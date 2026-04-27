"""One-time migration script from local SQLite to Supabase/Postgres.

Usage:
    python scripts/migrate_sqlite_to_postgres.py

Required environment variables:
    TARGET_DATABASE_URL   Postgres/Supabase SQLAlchemy URL

Optional environment variables:
    SOURCE_SQLITE_PATH    Defaults to ../../Database/s92.db
    TRUNCATE_TARGET       Set to 1 to wipe target tables before import
"""

from __future__ import annotations

import os
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import Session, sessionmaker

from backend.ai_agent.models import AIMessage, AISession
from backend.auth.models import Message, User, WhatIfSession
from backend.models import BlogComment, BlogPost, News
from backend.rules.models import ComplianceRule, RuleEvaluation


ROOT = Path(__file__).resolve().parents[3]
DEFAULT_SOURCE = ROOT / "Database" / "s92.db"

TABLE_MODELS = [
    User,
    WhatIfSession,
    Message,
    AISession,
    AIMessage,
    BlogPost,
    BlogComment,
    News,
    ComplianceRule,
    RuleEvaluation,
]

TABLE_ORDER = [
    "users",
    "whatif_sessions",
    "messages",
    "ai_sessions",
    "ai_messages",
    "blog_posts",
    "blog_comments",
    "news",
    "compliance_rules",
    "rule_evaluations",
]


@dataclass
class TableSpec:
    name: str
    model: Any
    columns: list[str]


def get_source_sqlite_path() -> Path:
    raw_value = os.getenv("SOURCE_SQLITE_PATH", "").strip()
    return Path(raw_value) if raw_value else DEFAULT_SOURCE


def get_target_database_url() -> str:
    target_url = (os.getenv("TARGET_DATABASE_URL") or os.getenv("DATABASE_URL") or "").strip()
    if not target_url:
        raise RuntimeError("TARGET_DATABASE_URL or DATABASE_URL must be set.")
    if target_url.startswith("sqlite"):
        raise RuntimeError("Target database must be Postgres/Supabase, not SQLite.")
    return target_url


def should_truncate_target() -> bool:
    return os.getenv("TRUNCATE_TARGET", "0").strip().lower() in {"1", "true", "yes", "on"}


def sqlite_connect(path: Path) -> sqlite3.Connection:
    if not path.exists():
        raise FileNotFoundError(f"SQLite source database not found: {path}")
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    return connection


def fetch_sqlite_columns(connection: sqlite3.Connection, table_name: str) -> list[str]:
    rows = connection.execute(f"PRAGMA table_info({table_name})").fetchall()
    return [row["name"] for row in rows]


def fetch_sqlite_rows(connection: sqlite3.Connection, table_name: str, columns: list[str]) -> list[dict[str, Any]]:
    if not columns:
        return []
    query = f"SELECT {', '.join(columns)} FROM {table_name}"
    rows = connection.execute(query).fetchall()
    return [dict(row) for row in rows]


def build_table_specs(connection: sqlite3.Connection) -> list[TableSpec]:
    specs: list[TableSpec] = []
    for model in TABLE_MODELS:
        table_name = model.__tablename__
        available_columns = set(fetch_sqlite_columns(connection, table_name))
        model_columns = [column.name for column in model.__table__.columns if column.name in available_columns]
        specs.append(TableSpec(name=table_name, model=model, columns=model_columns))
    return specs


def assert_target_is_empty_or_allowed(session: Session, truncate_target: bool) -> None:
    if truncate_target:
        return
    for model in TABLE_MODELS:
        has_rows = session.execute(select(model.id).limit(1)).scalar_one_or_none()
        if has_rows is not None:
            raise RuntimeError(
                f"Target table '{model.__tablename__}' already has data. "
                "Set TRUNCATE_TARGET=1 to allow replacing target data."
            )


def truncate_target_tables(session: Session) -> None:
    session.execute(text("TRUNCATE TABLE messages, whatif_sessions, ai_messages, ai_sessions, blog_comments, blog_posts, news, rule_evaluations, compliance_rules, users RESTART IDENTITY CASCADE"))
    session.commit()


def normalize_row(table_name: str, row: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(row)

    if table_name == "ai_sessions":
        normalized.setdefault("title", "New chat")
        normalized.setdefault("updated_at", normalized.get("created_at"))

    return normalized


def import_table(session: Session, spec: TableSpec, rows: list[dict[str, Any]]) -> int:
    if not rows:
        return 0

    payload = [normalize_row(spec.name, row) for row in rows]
    session.bulk_insert_mappings(spec.model, payload)
    session.commit()
    return len(payload)


def reset_postgres_sequences(session: Session) -> None:
    for model in TABLE_MODELS:
        table = model.__tablename__
        session.execute(
            text(
                """
                SELECT setval(
                    pg_get_serial_sequence(:table_name, 'id'),
                    COALESCE((SELECT MAX(id) FROM """ + table + """), 1),
                    COALESCE((SELECT MAX(id) FROM """ + table + """), 0) > 0
                )
                """
            ),
            {"table_name": table},
        )
    session.commit()


def main() -> None:
    source_path = get_source_sqlite_path()
    target_url = get_target_database_url()
    truncate_target = should_truncate_target()

    sqlite_connection = sqlite_connect(source_path)
    specs = build_table_specs(sqlite_connection)

    target_engine = create_engine(target_url, pool_pre_ping=True)
    SessionLocal = sessionmaker(bind=target_engine)

    print(f"Source SQLite: {source_path}")
    print(f"Target DB: {target_url.split('@')[-1]}")
    print(f"Truncate target first: {'yes' if truncate_target else 'no'}")

    with SessionLocal() as session:
        assert_target_is_empty_or_allowed(session, truncate_target)

        if truncate_target:
            truncate_target_tables(session)

        imported_counts: dict[str, int] = {}

        for table_name in TABLE_ORDER:
            spec = next(item for item in specs if item.name == table_name)
            rows = fetch_sqlite_rows(sqlite_connection, spec.name, spec.columns)
            imported_counts[spec.name] = import_table(session, spec, rows)
            print(f"Imported {imported_counts[spec.name]} rows into {spec.name}")

        reset_postgres_sequences(session)

    sqlite_connection.close()
    print("SQLite to Postgres migration completed successfully.")


if __name__ == "__main__":
    main()
