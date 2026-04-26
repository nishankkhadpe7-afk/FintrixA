from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from sqlalchemy.exc import OperationalError
from pydantic import BaseModel
import time
import json

from backend.database import SessionLocal
from backend.auth.utils import decode_token
from backend.auth.models import User, WhatIfSession, Message
from backend.mistral_client import get_mistral_client

router = APIRouter()
security = HTTPBearer()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
):
    token = credentials.credentials

    user_id = decode_token(token)

    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token")

    user = db.query(User).filter(User.id == user_id).first()

    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    return user


def run_what_if_agent(question: str):
    from backend.whatif.whatif_engine import what_if_agent

    return what_if_agent(question)

def run_mistral_prompt(prompt: str):
    try:
        client = get_mistral_client()
        response = client.chat.complete(
            model="mistral-small",
            messages=[{"role": "user", "content": prompt}],
        )
        return response.choices[0].message.content.strip()
    except Exception:
        return None


def detect_scenario_type(history: str, new_message: str):
    prompt = f"""
You are a financial scenario classifier.

Conversation so far:
{history}

New message:
{new_message}

Is this a NEW scenario or continuation of SAME scenario?

Reply ONLY with:
NEW
or
CONTINUE
"""
    result = run_mistral_prompt(prompt)
    if not result:
        return "CONTINUE"
    text = str(result).upper()

    if "NEW" in text:
        return "NEW"
    return "CONTINUE"


class MessageRequest(BaseModel):
    session_id: int
    message: str


def commit_with_retry(db: Session, attempts: int = 3, delay: float = 0.2):
    for attempt in range(attempts):
        try:
            db.commit()
            return
        except OperationalError:
            if attempt == attempts - 1:
                raise
            time.sleep(delay)


@router.post("/create")
def create_session(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    session = WhatIfSession(user_id=user.id)
    db.add(session)
    commit_with_retry(db)
    db.refresh(session)

    return {
        "session_id": session.id,
        "message": "Session created"
    }


@router.post("/message")
def send_message(
    data: MessageRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    session = db.query(WhatIfSession).filter(
        WhatIfSession.id == data.session_id,
        WhatIfSession.user_id == user.id
    ).first()

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    user_msg = Message(
        session_id=session.id,
        role="user",
        content=data.message
    )
    db.add(user_msg)
    commit_with_retry(db)

    with db.no_autoflush:
        messages = db.query(Message).filter(
            Message.session_id == session.id
        ).order_by(Message.timestamp).all()

    context = ""
    for message in messages:
        context += f"{message.role.upper()}: {message.content}\n"

    decision = detect_scenario_type(context, data.message)

    if decision == "NEW":
        full_input = f"USER: {data.message}"
    else:
        full_input = context + f"\nUSER: {data.message}"

    ai_response = run_what_if_agent(full_input)

    ai_msg = Message(
        session_id=session.id,
        role="assistant",
        content=json.dumps(ai_response)
    )
    db.add(ai_msg)

    commit_with_retry(db)

    return ai_response


@router.get("/history/{session_id}")
def get_history(
    session_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    session = db.query(WhatIfSession).filter(
        WhatIfSession.id == session_id,
        WhatIfSession.user_id == user.id
    ).first()

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    messages = db.query(Message).filter(
        Message.session_id == session_id
    ).order_by(Message.timestamp).all()

    return [
        {
            "role": message.role,
            "content": message.content,
            "timestamp": message.timestamp
        }
        for message in messages
    ]


@router.get("/list")
def list_sessions(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    sessions = db.query(WhatIfSession).filter(
        WhatIfSession.user_id == user.id
    ).order_by(WhatIfSession.id.desc()).all()

    return [{"id": session.id} for session in sessions]


@router.delete("/delete/{session_id}")
def delete_session(
    session_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    session = db.query(WhatIfSession).filter(
        WhatIfSession.id == session_id,
        WhatIfSession.user_id == user.id
    ).first()

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    db.query(Message).filter(Message.session_id == session_id).delete()
    db.delete(session)
    commit_with_retry(db)

    return {"message": "Deleted"}


@router.post("/title")
def generate_title(
    data: MessageRequest,
    user: User = Depends(get_current_user)
):
    prompt = f"""
Generate a short 3-5 word title for this financial scenario:

{data.message}

Rules:
- Keep it concise
- No punctuation
- No full sentence
- Only title

Example:
"₹10 lakh abroad transfer FEMA compliance"
→ "Foreign Transfer Compliance"
"""

    result = run_mistral_prompt(prompt)
    if result:
        return {"title": str(result).strip()}

    fallback = " ".join(data.message.strip().split()[:5]).strip() or "Scenario"
    return {"title": fallback}
