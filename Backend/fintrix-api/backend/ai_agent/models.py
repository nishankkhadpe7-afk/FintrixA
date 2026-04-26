from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, ForeignKey, Text, DateTime
from backend.database import Base

class AISession(Base):
    __tablename__ = "ai_sessions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    title = Column(String, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class AIMessage(Base):
    __tablename__ = "ai_messages"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("ai_sessions.id"))
    role = Column(String)
    content = Column(Text)
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc))