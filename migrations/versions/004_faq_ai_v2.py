"""Create faq_ai v2 schema with FTS indexes.

Revision ID: 004_faq_ai_v2
Revises: 003_faq_ai
Create Date: 2026-03-01
"""

from alembic import op

revision = "004_faq_ai_v2"
down_revision = "003_faq_ai"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE EXTENSION IF NOT EXISTS pg_trgm;
        """
    )

    # Preserve old faq_ai (q/a/tags) if present.
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1
                FROM information_schema.columns
                WHERE table_schema = 'public'
                  AND table_name = 'faq_ai'
                  AND column_name = 'q'
            ) THEN
                IF NOT EXISTS (
                    SELECT 1
                    FROM information_schema.tables
                    WHERE table_schema = 'public'
                      AND table_name = 'faq_ai_legacy'
                ) THEN
                    ALTER TABLE faq_ai RENAME TO faq_ai_legacy;
                END IF;
            END IF;
        END
        $$;
        """
    )

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS faq_ai (
            id BIGSERIAL PRIMARY KEY,
            question TEXT NOT NULL,
            answer TEXT NOT NULL,
            category TEXT NULL,
            tag TEXT NULL,
            keywords JSONB NOT NULL DEFAULT '[]'::jsonb,
            is_active BOOLEAN NOT NULL DEFAULT TRUE,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        );
        """
    )

    # Backfill from legacy, if we renamed old table.
    op.execute(
        """
        INSERT INTO faq_ai (question, answer, tag, keywords, is_active, created_at, updated_at)
        SELECT l.q, l.a, NULLIF(l.tags->>0, ''), COALESCE(l.tags, '[]'::jsonb), TRUE, l.created_at, l.updated_at
        FROM faq_ai_legacy l
        WHERE EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema='public' AND table_name='faq_ai_legacy');
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
        CREATE INDEX IF NOT EXISTS ix_faq_ai_tag
        ON faq_ai (tag);
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_faq_ai_category
        ON faq_ai (category);
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_faq_ai_is_active
        ON faq_ai (is_active);
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_faq_ai_tsv_ru
        ON faq_ai
        USING GIN (to_tsvector('russian', coalesce(question, '') || ' ' || coalesce(answer, '')));
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_faq_ai_question_trgm
        ON faq_ai
        USING GIN (question gin_trgm_ops);
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_faq_ai_question_trgm;")
    op.execute("DROP INDEX IF EXISTS ix_faq_ai_tsv_ru;")
    op.execute("DROP INDEX IF EXISTS ix_faq_ai_is_active;")
    op.execute("DROP INDEX IF EXISTS ix_faq_ai_category;")
    op.execute("DROP INDEX IF EXISTS ix_faq_ai_tag;")
    op.execute("DROP INDEX IF EXISTS ix_faq_ai_updated_at;")
    op.execute("DROP TABLE IF EXISTS faq_ai;")
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM information_schema.tables
                WHERE table_schema='public' AND table_name='faq_ai_legacy'
            ) THEN
                ALTER TABLE faq_ai_legacy RENAME TO faq_ai;
            END IF;
        END
        $$;
        """
    )
