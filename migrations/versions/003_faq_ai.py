"""Ensure faq_ai table and indexes for AI FAQ.

Revision ID: 003_faq_ai
Revises: 002_add_faq_ai
Create Date: 2026-03-01
"""

from alembic import op

revision = "003_faq_ai"
down_revision = "002_add_faq_ai"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS faq_ai (
            id TEXT PRIMARY KEY,
            tags JSONB NOT NULL DEFAULT '[]'::jsonb,
            q TEXT NOT NULL,
            a TEXT NOT NULL,
            created_at TIMESTAMPTZ DEFAULT now(),
            updated_at TIMESTAMPTZ DEFAULT now()
        );
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_faq_ai_updated_at
        ON faq_ai (updated_at);
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_faq_ai_tags_gin
        ON faq_ai
        USING GIN (tags jsonb_path_ops);
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_faq_ai_tags_gin;")
    op.execute("DROP INDEX IF EXISTS ix_faq_ai_updated_at;")
