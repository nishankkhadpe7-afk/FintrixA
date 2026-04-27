from sqlalchemy import create_engine
from sqlalchemy import text
from sqlalchemy.orm import sessionmaker, declarative_base
from backend.config import get_database_url

DATABASE_URL = get_database_url()

engine_kwargs = {
    "pool_pre_ping": True,
}

if DATABASE_URL.startswith("sqlite"):
    engine_kwargs["connect_args"] = {"check_same_thread": False}

engine = create_engine(DATABASE_URL, **engine_kwargs)


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
