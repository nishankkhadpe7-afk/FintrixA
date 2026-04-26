"""Add chat metadata columns to ai_sessions.

Revision ID: 0002_chat_session_metadata
Revises: 0001_initial_schema
Create Date: 2026-04-26 00:00:00
"""

from alembic import op
import sqlalchemy as sa


revision = "0002_chat_session_metadata"
down_revision = "0001_initial_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("ai_sessions", sa.Column("title", sa.String(), nullable=True))
    op.add_column("ai_sessions", sa.Column("updated_at", sa.DateTime(), nullable=True))

    op.execute("UPDATE ai_sessions SET title = 'New chat' WHERE title IS NULL")
    op.execute("UPDATE ai_sessions SET updated_at = created_at WHERE updated_at IS NULL")


def downgrade() -> None:
    op.drop_column("ai_sessions", "updated_at")
    op.drop_column("ai_sessions", "title")
