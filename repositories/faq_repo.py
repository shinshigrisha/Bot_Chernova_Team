from __future__ import annotations

from typing import Any, Optional, Sequence

import asyncpg


class FAQRepository:
    def __init__(self, pool: asyncpg.Pool):
        self.pool = pool

    async def count(self) -> int:
        async with self.pool.acquire() as conn:
            return await conn.fetchval("SELECT COUNT(*) FROM faq_ai;")

    async def add_faq(
        self,
        question: str,
        answer: str,
        category: str | None = None,
        tag: str | None = None,
        keywords: Sequence[str] = (),
    ) -> int:
        async with self.pool.acquire() as conn:
            return await conn.fetchval(
                """
                INSERT INTO faq_ai (question, answer, category, tag, keywords)
                VALUES ($1, $2, $3, $4, $5::jsonb)
                RETURNING id;
                """,
                question,
                answer,
                category,
                tag,
                list(keywords),
            )

    async def search_by_text(self, query: str, limit: int = 5) -> list[dict[str, Any]]:
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT id, question, answer, category, tag, keywords, is_active,
                       ts_rank(
                           to_tsvector('russian', coalesce(question, '') || ' ' || coalesce(answer, '')),
                           plainto_tsquery('russian', $1)
                       ) AS score
                FROM faq_ai
                WHERE is_active = TRUE
                  AND to_tsvector('russian', coalesce(question, '') || ' ' || coalesce(answer, ''))
                      @@ plainto_tsquery('russian', $1)
                ORDER BY score DESC, updated_at DESC
                LIMIT $2;
                """,
                query,
                limit,
            )
        return [dict(r) | {"score": float(r["score"])} for r in rows]

    async def search_by_keywords(self, query: str, limit: int = 5) -> list[dict[str, Any]]:
        q = query.lower()
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT id, question, answer, category, tag, keywords, is_active,
                       CASE
                         WHEN lower(question) LIKE $1 OR lower(answer) LIKE $1 THEN 0.8
                         WHEN lower(tag) = $2 THEN 0.7
                         ELSE 0.5
                       END AS score
                FROM faq_ai
                WHERE is_active = TRUE
                  AND (
                       lower(question) LIKE $1
                    OR lower(answer) LIKE $1
                    OR lower(tag) = $2
                    OR EXISTS (
                        SELECT 1
                        FROM jsonb_array_elements_text(keywords) kw
                        WHERE lower(kw) LIKE $1
                    )
                  )
                ORDER BY score DESC, updated_at DESC
                LIMIT $3;
                """,
                f"%{q}%",
                q,
                limit,
            )
        return [dict(r) | {"score": float(r["score"])} for r in rows]

    async def search_hybrid(self, query: str, limit: int = 5) -> list[dict[str, Any]]:
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                """
                WITH text_ranked AS (
                    SELECT id,
                           ts_rank(
                               to_tsvector('russian', coalesce(question,'') || ' ' || coalesce(answer,'')),
                               plainto_tsquery('russian', $1)
                           ) AS text_score
                    FROM faq_ai
                    WHERE is_active = TRUE
                      AND to_tsvector('russian', coalesce(question,'') || ' ' || coalesce(answer,''))
                          @@ plainto_tsquery('russian', $1)
                ),
                keyword_ranked AS (
                    SELECT id,
                           CASE
                             WHEN lower(question) LIKE $2 OR lower(answer) LIKE $2 THEN 0.8
                             WHEN lower(tag) = $3 THEN 0.7
                             ELSE 0.5
                           END AS keyword_score
                    FROM faq_ai
                    WHERE is_active = TRUE
                      AND (
                           lower(question) LIKE $2
                        OR lower(answer) LIKE $2
                        OR lower(tag) = $3
                        OR EXISTS (
                            SELECT 1
                            FROM jsonb_array_elements_text(keywords) kw
                            WHERE lower(kw) LIKE $2
                        )
                      )
                )
                SELECT f.id, f.question, f.answer, f.category, f.tag, f.keywords, f.is_active,
                       COALESCE(t.text_score, 0) * 0.7 + COALESCE(k.keyword_score, 0) * 0.3 AS score
                FROM faq_ai f
                LEFT JOIN text_ranked t ON t.id = f.id
                LEFT JOIN keyword_ranked k ON k.id = f.id
                WHERE f.is_active = TRUE
                  AND (t.id IS NOT NULL OR k.id IS NOT NULL)
                ORDER BY score DESC, f.updated_at DESC
                LIMIT $4;
                """,
                query,
                f"%{query.lower()}%",
                query.lower(),
                limit,
            )
        return [dict(r) | {"score": float(r["score"])} for r in rows]

    # Backward-compat wrappers used by old handlers/scripts.
    async def upsert(self, faq_id: str, q: str, a: str, tags: Sequence[str] = ()) -> None:
        tag = tags[0] if tags else None
        try:
            faq_id_int = int(faq_id)
        except ValueError:
            faq_id_int = None

        async with self.pool.acquire() as conn:
            if faq_id_int is None:
                await conn.execute(
                    """
                    INSERT INTO faq_ai (question, answer, tag, keywords)
                    VALUES ($1, $2, $3, $4::jsonb);
                    """,
                    q,
                    a,
                    tag,
                    list(tags),
                )
                return
            await conn.execute(
                """
                INSERT INTO faq_ai (id, question, answer, tag, keywords)
                VALUES ($1, $2, $3, $4, $5::jsonb)
                ON CONFLICT (id) DO UPDATE SET
                  question = EXCLUDED.question,
                  answer = EXCLUDED.answer,
                  tag = EXCLUDED.tag,
                  keywords = EXCLUDED.keywords,
                  updated_at = now();
                """,
                faq_id_int,
                q,
                a,
                tag,
                list(tags),
            )

    async def search(
        self, text: str, tags: Optional[Sequence[str]] = None, top_k: int = 3
    ) -> list[dict[str, Any]]:
        rows = await self.search_hybrid(query=text, limit=top_k)
        if tags:
            allowed = {t.lower() for t in tags if t}
            rows = [r for r in rows if (r.get("tag") or "").lower() in allowed][:top_k]
        return [
            {
                "id": str(r["id"]),
                "tags": [r.get("tag")] if r.get("tag") else [],
                "q": r.get("question", ""),
                "a": r.get("answer", ""),
                "score": float(r["score"]),
            }
            for r in rows
        ]
