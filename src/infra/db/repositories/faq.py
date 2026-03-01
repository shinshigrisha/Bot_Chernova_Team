"""FAQ repository (SQLAlchemy async)."""
from __future__ import annotations

from typing import Any, Sequence

from sqlalchemy import func, select, case
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from src.infra.db.models import FAQItem


class FAQRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def count(self) -> int:
        result = await self._session.execute(select(func.count()).select_from(FAQItem))
        return result.scalar_one()

    async def upsert(
        self, faq_id: str, q: str, a: str, tags: Sequence[str] = ()
    ) -> None:
        stmt = (
            insert(FAQItem)
            .values(id=faq_id, q=q, a=a, tags=list(tags))
            .on_conflict_do_update(
                index_elements=["id"],
                set_={"q": q, "a": a, "tags": list(tags), "updated_at": func.now()},
            )
        )
        await self._session.execute(stmt)

    async def search(
        self,
        text: str,
        tags: Sequence[str] | None = None,
        top_k: int = 3,
    ) -> list[dict[str, Any]]:
        like = f"%{text}%"
        score_expr = case(
            (FAQItem.q.ilike(like), 1.0),
            (FAQItem.a.ilike(like), 0.8),
            else_=0.0,
        )
        stmt = (
            select(
                FAQItem.id,
                FAQItem.tags,
                FAQItem.q,
                FAQItem.a,
                score_expr.label("score"),
            )
            .where((FAQItem.q.ilike(like)) | (FAQItem.a.ilike(like)))
        )

        if tags:
            stmt = stmt.where(FAQItem.tags.contains([tags[0]]))

        stmt = stmt.order_by(score_expr.desc()).limit(top_k)

        result = await self._session.execute(stmt)
        return [
            {"id": r.id, "tags": r.tags, "q": r.q, "a": r.a, "score": float(r.score)}
            for r in result
        ]

    async def get_by_id(self, faq_id: str) -> FAQItem | None:
        return await self._session.get(FAQItem, faq_id)
