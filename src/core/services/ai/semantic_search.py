"""DEPRECATED: Not used in runtime. Canonical retrieval: RAGService + FAQRepository + get_embedding_service() (rag_service, faq_repo, embedding_service). Do not import; kept for reference only."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from src.core.services.ai.embedding_service import generate_embedding
from src.infra.db.repositories.faq_repo import FAQRepository


async def embed_text(text: str) -> list[float] | None:
    """Сгенерировать эмбеддинг для текста через канонический embedding_service.

    Возвращает None, если эмбеддинги отключены или текст пустой.
    """
    return await generate_embedding(text)


async def search_similar_faq(
    query: str,
    *,
    faq_repo: FAQRepository,
    session: AsyncSession,
    limit: int = 5,
    tag: str | None = None,
    category: str | None = None,
) -> list[dict[str, Any]]:
    """Найти top‑K FAQ по семантической близости с fallback на текстовый поиск.

    Workflow:
      user message -> embedding -> cosine similarity (pgvector) -> top‑K FAQ
      fallback: гибридный/text‑поиск, если семантика недоступна или не дала результатов.
    """
    normalized_query = (query or "").strip()
    if not normalized_query:
        return []

    # 1) Семантический путь (через канонический EmbeddingsService)
    embedding = await embed_text(normalized_query)
    if embedding:
        semantic_hits = await faq_repo.search_semantic(
            query_embedding=embedding,
            limit=limit,
            tag=tag,
            category=category,
            session=session,
        )
        if semantic_hits:
            return semantic_hits

    # 2) Fallback: существующий гибридный поиск (text + keyword [+ semantic, если доступен])
    hybrid_hits = await faq_repo.search_hybrid(
        query=normalized_query,
        limit=limit,
        tag=tag,
        category=category,
        query_embedding=None,
        session=session,
    )
    return hybrid_hits

