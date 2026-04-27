from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from sqlalchemy.exc import OperationalError
from backend.database import SessionLocal
from backend.auth.models import User
from backend.auth.utils import hash_password, verify_password, create_access_token, decode_token
from pydantic import BaseModel
import time

router = APIRouter()
security = HTTPBearer()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def commit_with_retry(db: Session, attempts: int = 3, delay: float = 0.2):
    for attempt in range(attempts):
        try:
            db.commit()
            return
        except OperationalError:
            if attempt == attempts - 1:
                raise
            time.sleep(delay)


class UserCreate(BaseModel):
    email: str
    password: str


class UserLogin(BaseModel):
    email: str
    password: str


@router.post("/signup")
def signup(data: UserCreate, db: Session = Depends(get_db)):
    normalized_email = data.email.strip().lower()
    existing_user = db.query(User).filter(User.email == normalized_email).first()

    if existing_user:
        raise HTTPException(status_code=400, detail="User already exists")

    user = User(
        email=normalized_email,
        password=hash_password(data.password)
    )

    db.add(user)
    commit_with_retry(db)
    db.refresh(user)

    token = create_access_token({"user_id": user.id})
    return {
        "message": "User created successfully",
        "token": token,
        "access_token": token,
        "token_type": "bearer",
        "user": {"id": user.id, "email": user.email}
    }


@router.post("/login")
def login(data: UserLogin, db: Session = Depends(get_db)):
    normalized_email = data.email.strip().lower()
    user = db.query(User).filter(User.email == normalized_email).first()

    if not user or not verify_password(data.password, user.password):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = create_access_token({"user_id": user.id})

    return {
        "token": token,
        "access_token": token,
        "token_type": "bearer",
        "user": {"id": user.id, "email": user.email}
    }


@router.get("/me")
def me(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
):
    user_id = decode_token(credentials.credentials)
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    return {"id": user.id, "email": user.email}
