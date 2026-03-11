"""Add native vector(1536) column and index for semantic FAQ search.

Revision ID: 006_faq_embedding_vector
Revises: 005_add_faq_embeddings
Create Date: 2026-03-11

Safe migration: nullable column, index for similarity search (pgvector).
"""

from alembic import op

revision = "006_faq_embedding_vector"
down_revision = "005_add_faq_embeddings"
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
                    RAISE NOTICE 'pgvector extension unavailable; semantic index skipped';
            END;
        END
        $$;
        """
    )
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_schema = 'public'
                  AND table_name = 'faq_ai'
                  AND column_name = 'embedding_vector'
            ) THEN
                ALTER TABLE faq_ai
                ADD COLUMN embedding_vector vector(1536) NULL;
            END IF;
        END
        $$;
        """
    )
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'vector')
               AND NOT EXISTS (
                   SELECT 1 FROM pg_indexes
                   WHERE indexname = 'faq_ai_embedding_vector_hnsw_idx'
               )
            THEN
                CREATE INDEX faq_ai_embedding_vector_hnsw_idx
                ON faq_ai
                USING hnsw (embedding_vector vector_cosine_ops)
                WITH (m = 32, ef_construction = 128)
                WHERE embedding_vector IS NOT NULL;
            END IF;
        EXCEPTION
            WHEN OTHERS THEN
                RAISE NOTICE 'HNSW index creation failed, trying IVFFlat: %', SQLERRM;
                IF NOT EXISTS (
                    SELECT 1 FROM pg_indexes
                    WHERE indexname = 'faq_ai_embedding_vector_ivfflat_idx'
                ) THEN
                    CREATE INDEX faq_ai_embedding_vector_ivfflat_idx
                    ON faq_ai
                    USING ivfflat (embedding_vector vector_cosine_ops)
                    WITH (lists = 100)
                    WHERE embedding_vector IS NOT NULL;
                END IF;
        END
        $$;
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DROP INDEX IF EXISTS faq_ai_embedding_vector_hnsw_idx;
        """
    )
    op.execute(
        """
        DROP INDEX IF EXISTS faq_ai_embedding_vector_ivfflat_idx;
        """
    )
    op.execute(
        """
        ALTER TABLE faq_ai DROP COLUMN IF EXISTS embedding_vector;
        """
    )
