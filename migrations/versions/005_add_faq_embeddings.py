"""Add embedding column for semantic FAQ search.

Revision ID: 005_add_faq_embeddings
Revises: 004_faq_ai_v2
Create Date: 2026-03-11
"""

from alembic import op

revision = "005_add_faq_embeddings"
down_revision = "004_faq_ai_v2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        DO $$
        BEGIN
            BEGIN
                CREATE EXTENSION IF NOT EXISTS vector;
            EXCEPTION
                WHEN OTHERS THEN
                    RAISE NOTICE 'pgvector extension is unavailable; semantic search will stay disabled';
            END;
        END
        $$;
        """
    )
    op.execute(
        """
        ALTER TABLE faq_ai
        ADD COLUMN IF NOT EXISTS embedding TEXT NULL;
        """
    )


def downgrade() -> None:
    op.execute(
        """
        ALTER TABLE faq_ai
        DROP COLUMN IF EXISTS embedding;
        """
    )
