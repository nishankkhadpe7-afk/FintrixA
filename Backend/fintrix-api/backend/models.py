from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from backend.database import Base
from datetime import datetime

class News(Base):
    __tablename__ = "news"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    description = Column(Text)
    content = Column(Text)
    image_url = Column(String)
    source = Column(String)
    url = Column(String)
    published_at = Column(DateTime, default=datetime.utcnow)


class BlogPost(Base):
    __tablename__ = "blog_posts"

    id = Column(Integer, primary_key=True, index=True)
    author = Column(String, nullable=False)
    title = Column(String, nullable=False)
    body = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    comments = relationship("BlogComment", back_populates="post", cascade="all, delete-orphan")


class BlogComment(Base):
    __tablename__ = "blog_comments"

    id = Column(Integer, primary_key=True, index=True)
    post_id = Column(Integer, ForeignKey("blog_posts.id"), nullable=False, index=True)
    author = Column(String, nullable=False)
    body = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    post = relationship("BlogPost", back_populates="comments")
