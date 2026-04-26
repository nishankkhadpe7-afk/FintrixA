from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.database import SessionLocal
from backend.models import BlogComment, BlogPost

router = APIRouter()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


class PostCreateRequest(BaseModel):
    author: str
    title: str
    body: str


class CommentCreateRequest(BaseModel):
    author: str
    body: str


def serialize_post(post: BlogPost) -> dict:
    comments = sorted(post.comments, key=lambda item: item.created_at, reverse=True)
    return {
        "id": post.id,
        "author": post.author,
        "title": post.title,
        "body": post.body,
        "created_at": str(post.created_at),
        "comments": [
            {
                "id": comment.id,
                "author": comment.author,
                "body": comment.body,
                "created_at": str(comment.created_at),
            }
            for comment in comments
        ],
    }


@router.get("/posts")
def list_posts(db: Session = Depends(get_db)):
    posts = db.query(BlogPost).order_by(BlogPost.created_at.desc()).all()
    return [serialize_post(post) for post in posts]


@router.post("/posts")
def create_post(payload: PostCreateRequest, db: Session = Depends(get_db)):
    author = payload.author.strip()
    title = payload.title.strip()
    body = payload.body.strip()

    if not author or not title or not body:
        raise HTTPException(status_code=400, detail="Author, title, and body are required")

    post = BlogPost(author=author, title=title, body=body)
    db.add(post)
    db.commit()
    db.refresh(post)

    return serialize_post(post)


@router.post("/posts/{post_id}/comments")
def create_comment(post_id: int, payload: CommentCreateRequest, db: Session = Depends(get_db)):
    post = db.query(BlogPost).filter(BlogPost.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")

    author = payload.author.strip()
    body = payload.body.strip()

    if not author or not body:
        raise HTTPException(status_code=400, detail="Author and body are required")

    comment = BlogComment(post_id=post.id, author=author, body=body)
    db.add(comment)
    db.commit()
    db.refresh(comment)

    db.refresh(post)
    return serialize_post(post)


@router.delete("/posts/{post_id}")
def delete_post(post_id: int, db: Session = Depends(get_db)):
    post = db.query(BlogPost).filter(BlogPost.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")

    db.delete(post)
    db.commit()

    return {"message": "Post deleted"}
