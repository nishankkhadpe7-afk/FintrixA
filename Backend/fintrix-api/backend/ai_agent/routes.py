from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from sqlalchemy.exc import OperationalError
from backend.database import SessionLocal
from backend.auth.utils import decode_token
from backend.auth.models import User
from backend.ai_agent.models import AISession, AIMessage
from backend.ai_agent.topic_guard import (
    build_off_topic_response,
    build_welcome_response,
    classify_question_scope,
)
from pydantic import BaseModel
import json
import time
from datetime import datetime, timezone
import logging

router = APIRouter()
security = HTTPBearer()


def serialize_datetime(value: datetime | None):
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).isoformat()


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


class MessageRequest(BaseModel):
    session_id: int
    message: str
    persist: bool = True


def commit_with_retry(db: Session, attempts: int = 3, delay: float = 0.2):
    for attempt in range(attempts):
        try:
            db.commit()
            return
        except OperationalError:
            if attempt == attempts - 1:
                raise
            time.sleep(delay)


def load_ai_runtime():
    from backend.ai_agent.rag_pipeline import ask_agent, client

    return ask_agent, client


def detect_context_switch(history, new_message):
    try:
        _, client = load_ai_runtime()
    except Exception:
        return "NEW"
    if len(history.strip()) < 20:
        return "NEW"

    prompt = f"""
Conversation:
{history}

New message:
{new_message}

Is this a NEW topic or CONTINUATION?

Reply ONLY:
NEW
or
CONTINUE
"""

    try:
        res = client.chat.complete(
            model="mistral-small-latest",
            messages=[{"role": "user", "content": prompt}]
        )
        text = res.choices[0].message.content.upper()
    except Exception:
        # If the model is unavailable, avoid blocking the request.
        return "CONTINUE"

    if "NEW" in text:
        return "NEW"
    return "CONTINUE"


@router.post("/session/create")
def create_session(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    session = AISession(user_id=user.id)
    db.add(session)
    commit_with_retry(db)
    db.refresh(session)

    return {
        "session_id": session.id,
        "message": "Session created"
    }


@router.post("/session/message")
def send_message(
    data: MessageRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    scope = classify_question_scope(data.message)

    session = db.query(AISession).filter(
        AISession.id == data.session_id,
        AISession.user_id == user.id
    ).first()

    if not session:
        # Defensive fallback: try to use the most recently-updated session for the user,
        # or create a new one if none exist. This avoids surfacing a hard 404 to the UI
        # when the frontend creates sessions via the /api/chats path but race/consistency
        # issues cause a lookup miss here.
        logger = logging.getLogger(__name__)
        logger.warning("AI session id %s not found for user %s; attempting fallback", data.session_id, user.id)

        fallback = db.query(AISession).filter(AISession.user_id == user.id).order_by(AISession.updated_at.desc()).first()
        if fallback:
            session = fallback
            logger.info("Using fallback AI session id %s for user %s", session.id, user.id)
        else:
            # Create a new session for the user
            new_session = AISession(user_id=user.id)
            db.add(new_session)
            db.commit()
            db.refresh(new_session)
            session = new_session
            logger.info("Created new AI session id %s for user %s", session.id, user.id)

    if data.persist:
        user_msg = AIMessage(
            session_id=session.id,
            role="user",
            content=data.message
        )
        db.add(user_msg)

        if not session.title or session.title.strip() == "":
            session.title = data.message.strip()[:40] or "New chat"
        session.updated_at = datetime.now(timezone.utc)
        db.add(session)

        commit_with_retry(db)

    with db.no_autoflush:
        messages = db.query(AIMessage).filter(
            AIMessage.session_id == session.id
        ).order_by(AIMessage.timestamp).all()

    context = ""

    for m in messages:
        if m.role == "assistant":
            try:
                parsed = json.loads(m.content)
                text = parsed.get("answer", "")
            except:
                text = m.content
        else:
            text = m.content

        context += f"{m.role.upper()}: {text}\n"

    context = "\n".join(context.split("\n")[-6:])
    if not data.persist:
        context = f"{context}\nUSER: {data.message}"

    if scope == "greeting":
        ai_response = build_welcome_response()
    elif scope == "off_topic":
        ai_response = build_off_topic_response()
    else:
        decision = detect_context_switch(context, data.message)

        if decision == "NEW":
            final_context = ""
        else:
            final_context = context

        try:
            ask_agent, _ = load_ai_runtime()
            ai_response = ask_agent(data.message, final_context)
        except Exception:
            from backend.ai_agent.fallback import ask_agent_fallback
            ai_response = ask_agent_fallback(data.message, final_context)

        if isinstance(ai_response, dict):
            ai_response.setdefault("is_off_topic", False)

    if data.persist:
        ai_msg = AIMessage(
            session_id=session.id,
            role="assistant",
            content=json.dumps(ai_response)
        )
        db.add(ai_msg)

        session.updated_at = datetime.now(timezone.utc)
        db.add(session)

        commit_with_retry(db)

    return ai_response


@router.get("/session/history/{session_id}")
def get_history(
    session_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    session = db.query(AISession).filter(
        AISession.id == session_id,
        AISession.user_id == user.id
    ).first()

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    messages = db.query(AIMessage).filter(
        AIMessage.session_id == session_id
    ).order_by(AIMessage.timestamp).all()

    return [
        {
            "role": m.role,
            "content": m.content,
            "timestamp": serialize_datetime(m.timestamp)
        }
        for m in messages
    ]

@router.get("/session/list")
def list_sessions(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    sessions = db.query(AISession).filter(
        AISession.user_id == user.id
    ).order_by(AISession.id.desc()).all()

    return [{"id": s.id} for s in sessions]


@router.delete("/session/delete/{session_id}")
def delete_session(
    session_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    session = db.query(AISession).filter(
        AISession.id == session_id,
        AISession.user_id == user.id
    ).first()

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    db.query(AIMessage).filter(
        AIMessage.session_id == session_id
    ).delete()

    db.delete(session)
    commit_with_retry(db)

    return {"message": "Session deleted"}
