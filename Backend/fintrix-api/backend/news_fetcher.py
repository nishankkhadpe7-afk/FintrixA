import requests
import os
from dotenv import load_dotenv
from backend.database import SessionLocal
from backend.models import News
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

env_path = Path(__file__).resolve().parent / ".env"
load_dotenv(dotenv_path=env_path)
API_KEY = os.getenv("NEWS_API_KEY")

def _parse_published_at(raw_value: str | None) -> datetime:
    if not raw_value:
        return datetime.utcnow()

    # NewsData usually returns ISO timestamps (for example 2026-04-24 10:22:00)
    # but fallback to utcnow if parsing fails.
    try:
        normalized = raw_value.replace("Z", "+00:00").replace(" ", "T")
        return datetime.fromisoformat(normalized)
    except Exception:
        return datetime.utcnow()


def _normalize_newsdata_article(article: Dict[str, Any]) -> Dict[str, Any] | None:
    title = (article.get("title") or "").strip()
    if not title:
        return None

    return {
        "title": title,
        "description": article.get("description"),
        "content": article.get("content"),
        "image_url": article.get("image_url"),
        "source": article.get("source_name") or article.get("source_id"),
        "url": article.get("link"),
        "published_at": _parse_published_at(article.get("pubDate")),
    }


def fetch_finance_news():
    if not API_KEY:
        return []
    session = requests.Session()
    session.trust_env = False

    # Pull finance-focused headlines directly from the business category.
    url = f"https://newsdata.io/api/1/news?apikey={API_KEY}&category=business&language=en"
    try:
        response = session.get(url, timeout=15)
    except Exception:
        return []

    if response.status_code != 200:
        return []

    payload = response.json()
    articles = payload.get("results", [])
    if not isinstance(articles, list):
        return []

    db = SessionLocal()

    try:
        for article in articles:
            normalized = _normalize_newsdata_article(article)
            if not normalized:
                continue
            title = normalized["title"]

            exists = db.query(News).filter(News.title == title).first()
            if exists:
                continue

            news = News(
                title=title,
                description=normalized["description"],
                content=normalized["content"],
                image_url=normalized["image_url"],
                source=normalized["source"],
                url=normalized["url"],
                published_at=normalized["published_at"],
            )

            db.add(news)

        db.commit()
    finally:
        db.close()

    return articles
