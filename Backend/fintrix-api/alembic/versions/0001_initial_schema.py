"""Initial schema for FinTrix backend.

Revision ID: 0001_initial_schema
Revises:
Create Date: 2026-04-24 00:00:00
"""

from alembic import op
import sqlalchemy as sa


revision = "0001_initial_schema"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "blog_posts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("author", sa.String(), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_blog_posts_id"), "blog_posts", ["id"], unique=False)

    op.create_table(
        "compliance_rules",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("rule_id", sa.String(), nullable=True),
        sa.Column("version", sa.Integer(), nullable=True),
        sa.Column("domain", sa.String(), nullable=True),
        sa.Column("type", sa.String(), nullable=True),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("canonical_rule", sa.Text(), nullable=False),
        sa.Column("action", sa.String(), nullable=True),
        sa.Column("source_document", sa.String(), nullable=True),
        sa.Column("source_page", sa.Integer(), nullable=True),
        sa.Column("source_url", sa.String(), nullable=True),
        sa.Column("regulator", sa.String(), nullable=True),
        sa.Column("severity", sa.String(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_compliance_rules_domain"), "compliance_rules", ["domain"], unique=False)
    op.create_index(op.f("ix_compliance_rules_id"), "compliance_rules", ["id"], unique=False)
    op.create_index(op.f("ix_compliance_rules_rule_id"), "compliance_rules", ["rule_id"], unique=False)

    op.create_table(
        "news",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("content", sa.Text(), nullable=True),
        sa.Column("image_url", sa.String(), nullable=True),
        sa.Column("source", sa.String(), nullable=True),
        sa.Column("url", sa.String(), nullable=True),
        sa.Column("published_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_news_id"), "news", ["id"], unique=False)

    op.create_table(
        "rule_evaluations",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("rule_id", sa.String(), nullable=True),
        sa.Column("input_summary", sa.Text(), nullable=True),
        sa.Column("matched", sa.Boolean(), nullable=True),
        sa.Column("trace", sa.Text(), nullable=True),
        sa.Column("source", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_rule_evaluations_id"), "rule_evaluations", ["id"], unique=False)

    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("email", sa.String(), nullable=True),
        sa.Column("password", sa.String(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_users_email"), "users", ["email"], unique=True)
    op.create_index(op.f("ix_users_id"), "users", ["id"], unique=False)

    op.create_table(
        "ai_sessions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_ai_sessions_id"), "ai_sessions", ["id"], unique=False)

    op.create_table(
        "blog_comments",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("post_id", sa.Integer(), nullable=False),
        sa.Column("author", sa.String(), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["post_id"], ["blog_posts.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_blog_comments_id"), "blog_comments", ["id"], unique=False)
    op.create_index(op.f("ix_blog_comments_post_id"), "blog_comments", ["post_id"], unique=False)

    op.create_table(
        "whatif_sessions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_whatif_sessions_id"), "whatif_sessions", ["id"], unique=False)

    op.create_table(
        "ai_messages",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("session_id", sa.Integer(), nullable=True),
        sa.Column("role", sa.String(), nullable=True),
        sa.Column("content", sa.Text(), nullable=True),
        sa.Column("timestamp", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["session_id"], ["ai_sessions.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_ai_messages_id"), "ai_messages", ["id"], unique=False)

    op.create_table(
        "messages",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("session_id", sa.Integer(), nullable=True),
        sa.Column("role", sa.String(), nullable=True),
        sa.Column("content", sa.Text(), nullable=True),
        sa.Column("timestamp", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["session_id"], ["whatif_sessions.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_messages_id"), "messages", ["id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_messages_id"), table_name="messages")
    op.drop_table("messages")

    op.drop_index(op.f("ix_ai_messages_id"), table_name="ai_messages")
    op.drop_table("ai_messages")

    op.drop_index(op.f("ix_whatif_sessions_id"), table_name="whatif_sessions")
    op.drop_table("whatif_sessions")

    op.drop_index(op.f("ix_blog_comments_post_id"), table_name="blog_comments")
    op.drop_index(op.f("ix_blog_comments_id"), table_name="blog_comments")
    op.drop_table("blog_comments")

    op.drop_index(op.f("ix_ai_sessions_id"), table_name="ai_sessions")
    op.drop_table("ai_sessions")

    op.drop_index(op.f("ix_users_id"), table_name="users")
    op.drop_index(op.f("ix_users_email"), table_name="users")
    op.drop_table("users")

    op.drop_index(op.f("ix_rule_evaluations_id"), table_name="rule_evaluations")
    op.drop_table("rule_evaluations")

    op.drop_index(op.f("ix_news_id"), table_name="news")
    op.drop_table("news")

    op.drop_index(op.f("ix_compliance_rules_rule_id"), table_name="compliance_rules")
    op.drop_index(op.f("ix_compliance_rules_id"), table_name="compliance_rules")
    op.drop_index(op.f("ix_compliance_rules_domain"), table_name="compliance_rules")
    op.drop_table("compliance_rules")

    op.drop_index(op.f("ix_blog_posts_id"), table_name="blog_posts")
    op.drop_table("blog_posts")
