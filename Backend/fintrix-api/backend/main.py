from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from apscheduler.schedulers.background import BackgroundScheduler
from pathlib import Path
import os
import logging
from backend.database import engine, Base, SessionLocal, ensure_ai_session_metadata_columns
from backend.models import News
from backend.news_fetcher import fetch_finance_news
from backend.auth.routes import router as auth_router
from backend.whatif.routes import router as session_router
from backend.ai_agent.routes import router as ai_router
from backend.blog.routes import router as blog_router
from backend.rules.routes import router as rules_router
from backend.chats.routes import router as chats_router
from backend.rules.models import ComplianceRule
from backend.config import (
    get_allowed_origins,
    should_auto_create_schema,
    should_enable_news_scheduler,
    should_seed_rules_on_startup,
    validate_runtime_config,
)

APP_ROOT = Path(__file__).resolve().parents[1]
DOCS_DIR = APP_ROOT / "docs"
logger = logging.getLogger(__name__)

app = FastAPI(docs_url="/api/docs", redoc_url="/api/redoc")
app.include_router(ai_router, prefix="/api/ai")
app.include_router(chats_router, prefix="/api/chats", tags=["Chats"])
app.include_router(rules_router, prefix="/api/rules", tags=["Rules Engine"])
app.include_router(blog_router, prefix="/api/blog", tags=["Blog"])
security = HTTPBearer()

allowed_origins = get_allowed_origins()
allow_all = "*" in allowed_origins

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=bool(allowed_origins) and not allow_all,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router, prefix="/api/auth", tags=["Auth"])
app.include_router(session_router, prefix="/api/session", tags=["Session"])
app.mount("/docs", StaticFiles(directory=str(DOCS_DIR)), name="docs")
scheduler = None


@app.on_event("startup")
def startup_event():
    global scheduler

    validate_runtime_config()

    if should_auto_create_schema():
        Base.metadata.create_all(bind=engine)
        ensure_ai_session_metadata_columns()

    from backend.rules.seed import seed_rules

    db = SessionLocal()
    try:
        active_rules = db.query(ComplianceRule).filter(ComplianceRule.is_active == True).count()  # noqa: E712
    finally:
        db.close()

    if should_seed_rules_on_startup() or active_rules == 0:
        seed_rules()

    if should_enable_news_scheduler():
        scheduler = BackgroundScheduler()
        scheduler.add_job(fetch_finance_news, "interval", minutes=30)
        scheduler.start()
        logger.info("Finance news scheduler started.")


@app.on_event("shutdown")
def shutdown_event():
    global scheduler

    if scheduler:
        scheduler.shutdown(wait=False)
        scheduler = None


def run_what_if_agent(question: str):
    from backend.whatif.whatif_engine import what_if_agent

    return what_if_agent(question)


@app.get("/api/health")
def health():
    return {"status": "ok"}

@app.get("/api/news")
def get_news():
    db = SessionLocal()
    news = db.query(News).order_by(News.published_at.desc()).limit(20).all()
    db.close()
    return news

@app.get("/api/news/{news_id}")
def get_article(news_id: int):
    db = SessionLocal()
    article = db.query(News).filter(News.id == news_id).first()
    db.close()
    return article

@app.get("/api/fetch-news")
def manual_fetch():
    fetch_finance_news()
    return {"message": "News fetched successfully"}

class Question(BaseModel):
    question: str

@app.post("/api/ask")
def ask(question: Question):
    try:
        from backend.ai_agent.rag_pipeline import ask_agent
        response = ask_agent(question.question)
    except Exception:
        from backend.ai_agent.fallback import ask_agent_fallback
        response = ask_agent_fallback(question.question)

    if isinstance(response, dict):
        response.setdefault("is_off_topic", False)
    return response

@app.post("/api/what-if")
def what_if(question: Question):
    return run_what_if_agent(question.question)

@app.get("/api/dashboard")
def dashboard():
    db = SessionLocal()
    try:
        from backend.rules.engine import get_rule_stats
        stats = get_rule_stats(db)
        return {
            "queries": stats.get("total_evaluations", 0),
            "risk": "Medium",
            "compliance": 89,
            "active_rules": stats.get("active_rules", 0),
            "total_rules": stats.get("total_rules", 0),
            "domains": stats.get("domains", {}),
            "regulators": stats.get("regulators", {}),
            "severities": stats.get("severities", {})
        }
    finally:
        db.close()

@app.get("/api/budget")
def get_budget():
    return {
        "labels": ["Infrastructure", "Healthcare", "Education", "Defense", "Others"],
        "allocation": [30, 25, 20, 15, 10],
        "monthly": [65, 59, 80, 81, 56, 55]
    }

@app.get("/api/tax")
def get_tax():
    return [
        {"range": "0-5L", "rate": 0},
        {"range": "5-10L", "rate": 20},
        {"range": "10-20L", "rate": 30},
        {"range": "20L+", "rate": 30}
    ]
