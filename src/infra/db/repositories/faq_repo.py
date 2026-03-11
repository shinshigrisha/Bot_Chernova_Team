from __future__ import annotations

import json
from typing import Any, Sequence

from sqlalchemy import func, select, text, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from src.infra.db.models import FAQItem


class FAQRepository:
    """Canonical FAQ repository for faq_ai v2 schema."""

    _SEARCH_RESULT_FIELDS = ("id", "question", "answer", "score")
    _SCORE_FIELDS = ("score", "text_score", "keyword_score", "semantic_score")

    def __init__(self, session: AsyncSession | None = None) -> None:
        self._session = session
        self._pgvector_available: bool | None = None

    def _get_session(self, session: AsyncSession | None = None) -> AsyncSession:
        current_session = session or self._session
        if current_session is None:
            raise RuntimeError("FAQRepository requires an AsyncSession")
        return current_session

    @staticmethod
    def _normalize_keywords(keywords: Sequence[str] = ()) -> list[str]:
        return [str(keyword).strip() for keyword in keywords if str(keyword).strip()]

    @classmethod
    def _normalize_rows(cls, rows: Sequence[Any]) -> list[dict[str, Any]]:
        normalized_rows: list[dict[str, Any]] = []
        for row in rows:
            item = dict(row)
            for field in cls._SCORE_FIELDS:
                if field in item and item[field] is not None:
                    item[field] = float(item[field])
            normalized_rows.append(item)
        return normalized_rows

    @staticmethod
    def serialize_embedding(embedding: Sequence[float] | None) -> str | None:
        if not embedding:
            return None
        return json.dumps([float(value) for value in embedding], separators=(",", ":"))

    @classmethod
    def _normalize_search_rows(cls, rows: Sequence[Any]) -> list[dict[str, Any]]:
        normalized_rows = cls._normalize_rows(rows)
        return [{field: row[field] for field in cls._SEARCH_RESULT_FIELDS} for row in normalized_rows]

    async def count(self, session: AsyncSession | None = None) -> int:
        current_session = self._get_session(session)
        result = await current_session.execute(select(func.count()).select_from(FAQItem))
        return int(result.scalar_one())

    async def list_embedding_sources(
        self,
        *,
        session: AsyncSession | None = None,
    ) -> list[dict[str, Any]]:
        current_session = self._get_session(session)
        result = await current_session.execute(
            select(FAQItem.id, FAQItem.question, FAQItem.answer).order_by(FAQItem.id.asc())
        )
        return [dict(row) for row in result.mappings().all()]

    async def set_embedding(
        self,
        faq_id: int,
        embedding: str | None,
        *,
        session: AsyncSession | None = None,
    ) -> None:
        current_session = self._get_session(session)
        await current_session.execute(
            update(FAQItem)
            .where(FAQItem.id == faq_id)
            .values(embedding=embedding, updated_at=func.now())
        )

    async def set_embedding_vector(
        self,
        faq_id: int,
        embedding_literal: str | None,
        *,
        session: AsyncSession | None = None,
    ) -> None:
        """Set native vector(1536) column for semantic search. embedding_literal format: '[0.1,0.2,...]'."""
        if not embedding_literal or not embedding_literal.strip():
            return
        current_session = self._get_session(session)
        await current_session.execute(
            text(
                """
                UPDATE faq_ai
                SET embedding_vector = CAST(:embedding_literal AS vector),
                    updated_at = NOW()
                WHERE id = :faq_id
                """
            ),
            {"embedding_literal": embedding_literal.strip(), "faq_id": faq_id},
        )

    async def search_semantic(
        self,
        query_embedding: list[float] | str,
        limit: int = 5,
        *,
        tag: str | None = None,
        category: str | None = None,
        session: AsyncSession | None = None,
    ) -> list[dict[str, Any]]:
        """Return FAQ rows ordered by vector similarity (cosine). Uses embedding_vector column."""
        current_session = self._get_session(session)
        if not await self._has_pgvector_extension(session=current_session):
            return []
        literal = (
            self.serialize_embedding(query_embedding)
            if isinstance(query_embedding, (list, tuple))
            else str(query_embedding).strip()
        )
        if not literal or literal == "null":
            return []
        sql = text(
            """
            SELECT
                id,
                question,
                answer,
                category,
                tag,
                keywords,
                is_active,
                0.0 AS text_score,
                0.0 AS keyword_score,
                GREATEST(0.0, 1.0 - (embedding_vector <=> CAST(:query_embedding AS vector))) AS semantic_score,
                GREATEST(0.0, 1.0 - (embedding_vector <=> CAST(:query_embedding AS vector))) AS score
            FROM faq_ai
            WHERE is_active = TRUE
              AND embedding_vector IS NOT NULL
              AND (CAST(:tag AS text) IS NULL OR lower(coalesce(tag, '')) = lower(CAST(:tag AS text)))
              AND (CAST(:category AS text) IS NULL OR lower(coalesce(category, '')) = lower(CAST(:category AS text)))
            ORDER BY embedding_vector <=> CAST(:query_embedding AS vector)
            LIMIT :limit
            """
        )
        try:
            result = await current_session.execute(
                sql,
                {
                    "query_embedding": literal,
                    "limit": limit,
                    "tag": tag,
                    "category": category,
                },
            )
        except Exception:
            self._pgvector_available = False
            return []
        return self._normalize_rows(result.mappings().all())

    async def _has_pgvector_extension(
        self,
        session: AsyncSession | None = None,
    ) -> bool:
        if self._pgvector_available is not None:
            return self._pgvector_available

        current_session = self._get_session(session)
        result = await current_session.execute(
            text("SELECT EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'vector')")
        )
        self._pgvector_available = bool(result.scalar())
        return self._pgvector_available

    async def add_faq(
        self,
        question: str,
        answer: str,
        category: str | None = None,
        tag: str | None = None,
        keywords: Sequence[str] = (),
        is_active: bool = True,
        session: AsyncSession | None = None,
    ) -> int:
        current_session = self._get_session(session)
        stmt = (
            insert(FAQItem)
            .values(
                question=question,
                answer=answer,
                category=category,
                tag=tag,
                keywords=self._normalize_keywords(keywords),
                is_active=is_active,
            )
            .returning(FAQItem.id)
        )
        result = await current_session.execute(stmt)
        return int(result.scalar_one())

    async def upsert_faq(
        self,
        *,
        question: str,
        answer: str,
        category: str | None = None,
        tag: str | None = None,
        keywords: Sequence[str] = (),
        is_active: bool = True,
        faq_id: int | None = None,
        session: AsyncSession | None = None,
    ) -> tuple[int, bool]:
        current_session = self._get_session(session)
        existing_id: int | None

        if faq_id is not None:
            result = await current_session.execute(select(FAQItem.id).where(FAQItem.id == faq_id))
            existing_id = result.scalar_one_or_none()
        else:
            result = await current_session.execute(
                select(FAQItem.id).where(FAQItem.question == question).order_by(FAQItem.id.asc()).limit(1)
            )
            existing_id = result.scalar_one_or_none()

        if existing_id is None:
            new_id = await self.add_faq(
                question=question,
                answer=answer,
                category=category,
                tag=tag,
                keywords=keywords,
                is_active=is_active,
                session=current_session,
            )
            return new_id, True

        stmt = (
            update(FAQItem)
            .where(FAQItem.id == existing_id)
            .values(
                question=question,
                answer=answer,
                category=category,
                tag=tag,
                keywords=self._normalize_keywords(keywords),
                is_active=is_active,
                updated_at=func.now(),
            )
            .returning(FAQItem.id)
        )
        result = await current_session.execute(stmt)
        return int(result.scalar_one()), False

    async def search_by_text(
        self,
        query: str,
        limit: int = 5,
        *,
        tag: str | None = None,
        category: str | None = None,
        session: AsyncSession | None = None,
    ) -> list[dict[str, Any]]:
        current_session = self._get_session(session)
        normalized_query = (query or "").strip()
        if not normalized_query:
            return []

        sql = text(
            """
            SELECT id, question, answer, category, tag, keywords, is_active,
                   ts_rank(
                       to_tsvector('russian', coalesce(question, '') || ' ' || coalesce(answer, '')),
                       plainto_tsquery('russian', :query)
                   ) AS score
            FROM faq_ai
            WHERE is_active = TRUE
              AND to_tsvector('russian', coalesce(question, '') || ' ' || coalesce(answer, ''))
                  @@ plainto_tsquery('russian', :query)
              AND (CAST(:tag AS text) IS NULL OR lower(coalesce(tag, '')) = lower(CAST(:tag AS text)))
              AND (CAST(:category AS text) IS NULL OR lower(coalesce(category, '')) = lower(CAST(:category AS text)))
            ORDER BY score DESC, updated_at DESC
            LIMIT :limit
            """
        )
        result = await current_session.execute(
            sql,
            {
                "query": normalized_query,
                "tag": tag,
                "category": category,
                "limit": limit,
            },
        )
        return self._normalize_rows(result.mappings().all())

    async def search_by_keywords(
        self,
        query: str,
        limit: int = 5,
        *,
        tag: str | None = None,
        category: str | None = None,
        session: AsyncSession | None = None,
    ) -> list[dict[str, Any]]:
        current_session = self._get_session(session)
        normalized_query = (query or "").strip().lower()
        if not normalized_query:
            return []

        sql = text(
            """
            SELECT id, question, answer, category, tag, keywords, is_active,
                   CASE
                     WHEN lower(question) LIKE :like_query OR lower(answer) LIKE :like_query THEN 0.8
                     WHEN lower(coalesce(tag, '')) = :exact_query THEN 0.7
                     ELSE 0.5
                   END AS score
            FROM faq_ai
            WHERE is_active = TRUE
              AND (
                   lower(question) LIKE :like_query
                OR lower(answer) LIKE :like_query
                OR lower(coalesce(tag, '')) = :exact_query
                OR EXISTS (
                    SELECT 1
                    FROM jsonb_array_elements_text(keywords) kw
                    WHERE lower(kw) LIKE :like_query
                )
              )
              AND (CAST(:tag AS text) IS NULL OR lower(coalesce(tag, '')) = lower(CAST(:tag AS text)))
              AND (CAST(:category AS text) IS NULL OR lower(coalesce(category, '')) = lower(CAST(:category AS text)))
            ORDER BY score DESC, updated_at DESC
            LIMIT :limit
            """
        )
        result = await current_session.execute(
            sql,
            {
                "like_query": f"%{normalized_query}%",
                "exact_query": normalized_query,
                "tag": tag,
                "category": category,
                "limit": limit,
            },
        )
        return self._normalize_rows(result.mappings().all())

    async def search_hybrid(
        self,
        query: str,
        limit: int = 5,
        *,
        tag: str | None = None,
        category: str | None = None,
        query_embedding: str | None = None,
        session: AsyncSession | None = None,
    ) -> list[dict[str, Any]]:
        current_session = self._get_session(session)
        normalized_query = (query or "").strip()
        if not normalized_query:
            return []

        pgvector_enabled = bool(query_embedding) and await self._has_pgvector_extension(current_session)

        # Use native embedding_vector column (vector(1536)) when available; fallback to 0.0
        semantic_score_sql = (
            """
                    CASE
                        WHEN f.embedding_vector IS NOT NULL THEN
                            GREATEST(0.0, 1.0 - (f.embedding_vector <=> CAST(:query_embedding AS vector)))
                        ELSE 0.0
                    END AS semantic_score
            """
            if pgvector_enabled
            else """
                    0.0 AS semantic_score
            """
        )

        sql = text(
            f"""
            WITH ranked AS (
                SELECT
                    f.id,
                    f.question,
                    f.answer,
                    f.category,
                    f.tag,
                    f.keywords,
                    f.is_active,
                    f.updated_at,
                    ts_rank(
                        to_tsvector('russian', coalesce(f.question, '') || ' ' || coalesce(f.answer, '')),
                        plainto_tsquery('russian', CAST(:query AS text))
                    ) AS text_score,
                    (
                        CASE
                            WHEN EXISTS (
                                SELECT 1
                                FROM jsonb_array_elements_text(coalesce(f.keywords, '[]'::jsonb)) AS kw
                                WHERE lower(kw) = lower(CAST(:exact_query AS text))
                            ) THEN 1.0
                            WHEN EXISTS (
                                SELECT 1
                                FROM jsonb_array_elements_text(coalesce(f.keywords, '[]'::jsonb)) AS kw
                                WHERE lower(kw) LIKE lower(CAST(:like_query AS text))
                            ) THEN 0.8
                            ELSE 0.0
                        END * 0.35
                        + CASE
                            WHEN lower(coalesce(f.tag, '')) = lower(CAST(:exact_query AS text)) THEN 1.0
                            WHEN lower(coalesce(f.tag, '')) LIKE lower(CAST(:like_query AS text)) THEN 0.7
                            ELSE 0.0
                        END * 0.2
                        + CASE
                            WHEN lower(coalesce(f.category, '')) = lower(CAST(:exact_query AS text)) THEN 1.0
                            WHEN lower(coalesce(f.category, '')) LIKE lower(CAST(:like_query AS text)) THEN 0.7
                            ELSE 0.0
                        END * 0.15
                        + CASE
                            WHEN lower(coalesce(f.question, '')) LIKE lower(CAST(:like_query AS text)) THEN 1.0
                            ELSE 0.0
                        END * 0.15
                        + CASE
                            WHEN lower(coalesce(f.answer, '')) LIKE lower(CAST(:like_query AS text)) THEN 1.0
                            ELSE 0.0
                        END * 0.15
                    ) AS keyword_score,
                    {semantic_score_sql}
                FROM faq_ai AS f
                WHERE f.is_active = TRUE
                  AND (CAST(:tag AS text) IS NULL OR lower(coalesce(f.tag, '')) = lower(CAST(:tag AS text)))
                  AND (CAST(:category AS text) IS NULL OR lower(coalesce(f.category, '')) = lower(CAST(:category AS text)))
            )
            SELECT
                id,
                question,
                answer,
                category,
                tag,
                keywords,
                is_active,
                text_score,
                keyword_score,
                semantic_score,
                (
                    CASE
                        WHEN semantic_score > 0
                        THEN (text_score * 0.3 + keyword_score * 0.1 + semantic_score * 0.6)
                        ELSE (text_score * 0.7 + keyword_score * 0.3)
                    END
                ) AS score
            FROM ranked
            WHERE text_score > 0
               OR keyword_score > 0
               OR semantic_score > 0
            ORDER BY score DESC, updated_at DESC
            LIMIT :limit
            """
        )
        params = {
            "query": normalized_query,
            "like_query": f"%{normalized_query.lower()}%",
            "exact_query": normalized_query.lower(),
            "tag": tag,
            "category": category,
            "query_embedding": query_embedding,
            "limit": limit,
        }
        try:
            result = await current_session.execute(sql, params)
        except Exception:
            if pgvector_enabled:
                self._pgvector_available = False
                return await self.search_hybrid(
                    query=query,
                    limit=limit,
                    tag=tag,
                    category=category,
                    query_embedding=None,
                    session=current_session,
                )
            raise
        return self._normalize_rows(result.mappings().all())

    async def search(
        self,
        query: str,
        limit: int = 5,
        *,
        tag: str | None = None,
        category: str | None = None,
        session: AsyncSession | None = None,
    ) -> list[dict[str, Any]]:
        hits = await self.search_hybrid(
            query=query,
            limit=limit,
            tag=tag,
            category=category,
            session=session,
        )
        return self._normalize_search_rows(hits)

    async def get_by_id(
        self,
        faq_id: int,
        *,
        session: AsyncSession | None = None,
    ) -> FAQItem | None:
        current_session = self._get_session(session)
        return await current_session.get(FAQItem, faq_id)
