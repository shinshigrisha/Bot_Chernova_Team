"""Change FAQ embedding_vector to vector(384) for canonical local MiniLM backend.

Revision ID: 018_embedding_vector_384
Revises: 017_verif_resolution
Create Date: 2026-03-14

Canonical embeddings: sentence-transformers/all-MiniLM-L6-v2 (384 dims).
Drops existing vector(1536) column and indexes; recreates as vector(384).
Run rebuild_embeddings after upgrade to repopulate.
"""

from typing import Sequence, Union

from alembic import op

revision: str = "018_embedding_vector_384"
down_revision: Union[str, None] = "017_verif_resolution"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("DROP INDEX IF EXISTS faq_ai_embedding_vector_hnsw_idx;")
    op.execute("DROP INDEX IF EXISTS faq_ai_embedding_vector_ivfflat_idx;")
    op.execute("ALTER TABLE faq_ai DROP COLUMN IF EXISTS embedding_vector;")
    op.execute(
        """
        ALTER TABLE faq_ai
        ADD COLUMN embedding_vector vector(384) NULL;
        """
    )
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'vector') THEN
                CREATE INDEX faq_ai_embedding_vector_hnsw_idx
                ON faq_ai
                USING hnsw (embedding_vector vector_cosine_ops)
                WITH (m = 32, ef_construction = 128)
                WHERE embedding_vector IS NOT NULL;
            END IF;
        EXCEPTION
            WHEN OTHERS THEN
                IF NOT EXISTS (SELECT 1 FROM pg_indexes WHERE indexname = 'faq_ai_embedding_vector_ivfflat_idx') THEN
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
    op.execute("DROP INDEX IF EXISTS faq_ai_embedding_vector_hnsw_idx;")
    op.execute("DROP INDEX IF EXISTS faq_ai_embedding_vector_ivfflat_idx;")
    op.execute("ALTER TABLE faq_ai DROP COLUMN IF EXISTS embedding_vector;")
    op.execute(
        """
        ALTER TABLE faq_ai
        ADD COLUMN embedding_vector vector(1536) NULL;
        """
    )
