from sqlalchemy import Column, Integer, String, ForeignKey, Text, DateTime
from datetime import datetime
from backend.database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    password = Column(String)

class WhatIfSession(Base):
    __tablename__ = "whatif_sessions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime, default=datetime.utcnow)

class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("whatif_sessions.id"))
    role = Column(String)  
    content = Column(Text)
    timestamp = Column(DateTime, default=datetime.utcnow)