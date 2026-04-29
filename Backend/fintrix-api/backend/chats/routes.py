from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.ai_agent.models import AIMessage, AISession
from backend.auth.models import User
from backend.auth.utils import decode_token
from backend.database import SessionLocal


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
    db: Session = Depends(get_db),
):
    user_id = decode_token(credentials.credentials)
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    return user


class ChatCreateRequest(BaseModel):
    title: str | None = None


class ChatMessageCreateRequest(BaseModel):
    role: str
    content: str


@router.post("")
def create_chat(
    payload: ChatCreateRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    now = datetime.now(timezone.utc)
    title = (payload.title or "").strip()[:120] or "New chat"

    session = AISession(
        user_id=user.id,
        title=title,
        created_at=now,
        updated_at=now,
    )
    db.add(session)
    db.commit()
    db.refresh(session)

    return {
        "id": session.id,
        "title": session.title,
        "createdAt": serialize_datetime(session.created_at),
    }


@router.get("")
def list_chats(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    sessions = (
        db.query(AISession)
        .filter(AISession.user_id == user.id)
        .order_by(AISession.updated_at.desc(), AISession.id.desc())
        .all()
    )

    return [
        {
            "id": session.id,
            "title": session.title or "New chat",
            "createdAt": serialize_datetime(session.created_at),
            "updatedAt": serialize_datetime(session.updated_at),
        }
        for session in sessions
    ]


@router.get("/{chat_id}/messages")
def get_chat_messages(
    chat_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    session = (
        db.query(AISession)
        .filter(AISession.id == chat_id, AISession.user_id == user.id)
        .first()
    )
    if not session:
        raise HTTPException(status_code=404, detail="Chat session not found")

    messages = (
        db.query(AIMessage)
        .filter(AIMessage.session_id == chat_id)
        .order_by(AIMessage.timestamp.asc(), AIMessage.id.asc())
        .all()
    )

    return [
        {
            "role": message.role,
            "content": message.content,
            "timestamp": serialize_datetime(message.timestamp),
        }
        for message in messages
    ]


@router.post("/{chat_id}/messages")
def append_chat_message(
    chat_id: int,
    payload: ChatMessageCreateRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    session = (
        db.query(AISession)
        .filter(AISession.id == chat_id, AISession.user_id == user.id)
        .first()
    )
    if not session:
        raise HTTPException(status_code=404, detail="Chat session not found")

    role = payload.role.strip().lower()
    if role not in {"user", "assistant"}:
        raise HTTPException(status_code=400, detail="role must be user or assistant")

    if not payload.content or not payload.content.strip():
        raise HTTPException(status_code=400, detail="content cannot be empty")

    now = datetime.now(timezone.utc)
    message = AIMessage(
        session_id=chat_id,
        role=role,
        content=payload.content,
        timestamp=now,
    )
    db.add(message)

    session.updated_at = now
    db.add(session)

    db.commit()
    db.refresh(message)

    return {
        "role": message.role,
        "content": message.content,
        "timestamp": serialize_datetime(message.timestamp),
    }


@router.delete("/{chat_id}")
def delete_chat(
    chat_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    session = (
        db.query(AISession)
        .filter(AISession.id == chat_id, AISession.user_id == user.id)
        .first()
    )
    if not session:
        raise HTTPException(status_code=404, detail="Chat session not found")

    db.query(AIMessage).filter(AIMessage.session_id == chat_id).delete()
    db.delete(session)
    db.commit()

    return {"message": "Chat deleted"}
