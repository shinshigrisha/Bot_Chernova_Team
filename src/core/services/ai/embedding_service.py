"""Embedding generation for semantic FAQ search.

Single module for generating embeddings using configured provider
(OpenAI or DeepSeek). Used by FAQ semantic search and rebuild script.
"""

from __future__ import annotations

import logging
from collections.abc import Sequence

from src.core.services.ai.embeddings_service import EmbeddingsService

logger = logging.getLogger(__name__)


def get_embedding_service() -> EmbeddingsService:
    """Return the canonical embeddings service (config-driven: OpenAI)."""
    return EmbeddingsService()


async def generate_embedding(text: str) -> list[float] | None:
    """Generate embedding for a single text. Returns None if disabled or error."""
    service = get_embedding_service()
    return await service.embed_text(text)


async def batch_generate_embeddings(texts: Sequence[str]) -> list[list[float] | None]:
    """Generate embeddings for multiple texts. Preserves order; None for failed/disabled."""
    if not texts:
        return []
    service = get_embedding_service()
    return await service.embed_texts(list(texts))
