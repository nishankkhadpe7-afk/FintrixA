from sqlalchemy import create_engine
from sqlalchemy import text
from sqlalchemy.orm import sessionmaker, declarative_base
from dotenv import load_dotenv
import os
from pathlib import Path

env_path = Path(__file__).resolve().parent / ".env"
load_dotenv(dotenv_path=env_path)

DATABASE_URL = os.getenv("DATABASE_URL")

# Local fallback keeps dev and tests runnable when env vars are not configured.
if not DATABASE_URL:
    workspace_root = Path(__file__).resolve().parents[3]
    fallback_db = workspace_root / "Database" / "s92.db"
    DATABASE_URL = f"sqlite:///{fallback_db.as_posix()}"

engine = create_engine(DATABASE_URL, pool_pre_ping=True)


def ensure_ai_session_metadata_columns():
    """Backfill ai_sessions metadata columns for existing SQLite databases.

    New deployments should use Alembic migration 0002_chat_session_metadata.
    This guard keeps local/dev DBs working when alembic_version is missing.
    """

    if engine.url.get_backend_name() != "sqlite":
        return

    with engine.begin() as connection:
        rows = connection.execute(text("PRAGMA table_info(ai_sessions)")).fetchall()
        columns = {row[1] for row in rows}

        if "title" not in columns:
            connection.execute(text("ALTER TABLE ai_sessions ADD COLUMN title VARCHAR"))

        if "updated_at" not in columns:
            connection.execute(text("ALTER TABLE ai_sessions ADD COLUMN updated_at DATETIME"))

        connection.execute(text("UPDATE ai_sessions SET title = 'New chat' WHERE title IS NULL"))
        connection.execute(text("UPDATE ai_sessions SET updated_at = created_at WHERE updated_at IS NULL"))

SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()
