"""Пересборка эмбеддингов FAQ. Вызывается из скрипта и из проактивного слоя (событие faq_added)."""

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy.ext.asyncio import async_sessionmaker

from src.core.services.ai.embeddings_service import EmbeddingsService
from src.infra.db.repositories.faq_repo import FAQRepository

logger = logging.getLogger(__name__)


async def rebuild_faq_embeddings_async(
    session_factory: async_sessionmaker,
    embeddings_service: EmbeddingsService | None = None,
) -> dict[str, Any]:
    """Пересобрать эмбеддинги для всех активных FAQ. Возвращает счётчики.

    Если embeddings_service is None — создаётся новый EmbeddingsService() (канонический
    бэкенд: local MiniLM по умолчанию, без внешнего API при EMBEDDING_PROVIDER=local).
    При отключённых эмбеддингах возвращает {"skipped": 0, "updated": 0, "error": "embeddings_disabled"}.
    """
    emb = embeddings_service or EmbeddingsService()
    repo = FAQRepository()
    try:
        if not emb.enabled:
            logger.info("faq_embeddings_rebuild_skipped", reason="embeddings_disabled")
            return {"updated": 0, "skipped": 0, "total": 0, "error": "embeddings_disabled", "output": "DB (pgvector, faq_ai.embedding_vector)"}

        async with session_factory() as session:
            faq_rows = await repo.list_embedding_sources(session=session)
            if not faq_rows:
                return {"updated": 0, "skipped": 0, "total": 0, "output": "DB (pgvector, faq_ai.embedding_vector)"}

            payloads = [
                EmbeddingsService.build_faq_text(
                    question=str(row.get("question") or ""),
                    answer=str(row.get("answer") or ""),
                )
                for row in faq_rows
            ]
            embeddings = await emb.embed_texts(payloads)

            updated = 0
            skipped = 0
            for row, embedding in zip(faq_rows, embeddings, strict=False):
                if embedding is None:
                    skipped += 1
                    continue
                literal = EmbeddingsService.serialize_embedding(embedding)
                await repo.set_embedding(
                    faq_id=int(row["id"]),
                    embedding=literal,
                    session=session,
                )
                await repo.set_embedding_vector(
                    faq_id=int(row["id"]),
                    embedding_literal=literal,
                    session=session,
                )
                updated += 1

            await session.commit()
            logger.info(
                "faq_embeddings_rebuild_done",
                total=len(faq_rows),
                updated=updated,
                skipped=skipped,
            )
            return {
                "updated": updated,
                "skipped": skipped,
                "total": len(faq_rows),
                "output": "DB (pgvector, faq_ai.embedding_vector)",
            }
    except Exception as e:
        logger.error("faq_embeddings_rebuild_failed: %s", str(e))
        return {"updated": 0, "skipped": 0, "total": 0, "error": str(e)}
    finally:
        if embeddings_service is None and emb is not None:
            await emb.close()
