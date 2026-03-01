"""Add faq_ai table for AI knowledge base.

Revision ID: 002_add_faq_ai
Revises: 001_initial_mvp
Create Date: 2026-03-01
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = "002_add_faq_ai"
down_revision = "001_initial_mvp"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "faq_ai",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column("tags", JSONB, nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("q", sa.Text, nullable=False),
        sa.Column("a", sa.Text, nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index("ix_faq_ai_tags", "faq_ai", [sa.text("tags")], postgresql_using="gin")
    op.create_index("ix_faq_ai_q", "faq_ai", ["q"])


def downgrade() -> None:
    op.drop_index("ix_faq_ai_q", table_name="faq_ai")
    op.drop_index("ix_faq_ai_tags", table_name="faq_ai")
    op.drop_table("faq_ai")
