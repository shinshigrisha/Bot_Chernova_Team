"""FAQ AI repository with AsyncSession-based methods."""
from __future__ import annotations

from typing import Any, Sequence

from sqlalchemy import case, func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from src.infra.db.models import FAQAI


class FAQAIRepository:
    async def count(self, session: AsyncSession) -> int:
        result = await session.execute(select(func.count()).select_from(FAQAI))
        return result.scalar_one()

    async def upsert(
        self,
        session: AsyncSession,
        faq_id: str,
        q: str,
        a: str,
        tags: Sequence[str] = (),
    ) -> None:
        stmt = (
            insert(FAQAI)
            .values(id=faq_id, q=q, a=a, tags=list(tags))
            .on_conflict_do_update(
                index_elements=["id"],
                set_={"q": q, "a": a, "tags": list(tags), "updated_at": func.now()},
            )
        )
        await session.execute(stmt)

    async def search(
        self,
        session: AsyncSession,
        text: str,
        tags: Sequence[str] | None = None,
        top_k: int = 3,
    ) -> list[dict[str, Any]]:
        like = f"%{text}%"
        score_expr = case(
            (FAQAI.q.ilike(like), 1.0),
            (FAQAI.a.ilike(like), 0.8),
            else_=0.0,
        )
        stmt = (
            select(
                FAQAI.id,
                FAQAI.tags,
                FAQAI.q,
                FAQAI.a,
                score_expr.label("score"),
            )
            .where((FAQAI.q.ilike(like)) | (FAQAI.a.ilike(like)))
        )

        if tags:
            stmt = stmt.where(FAQAI.tags.contains([tags[0]]))

        stmt = stmt.order_by(score_expr.desc()).limit(top_k)
        result = await session.execute(stmt)

        return [
            {"id": row.id, "tags": row.tags, "q": row.q, "a": row.a, "score": float(row.score)}
            for row in result
        ]
