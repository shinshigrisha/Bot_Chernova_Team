"""Canonical embedding service for semantic FAQ and ML case search.

Single entry point for embedding generation. Provider is config-driven (OpenAI).
Used by: FAQ semantic search, rebuild_faq_embeddings, rebuild_case_embeddings,
CaseClassifier semantic path, AICourierService.
Graceful fallback: returns None when API key is missing or provider errors.
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
    """
    Generate embedding for a single text.
    Returns None if embeddings disabled (no API key), empty input, or provider error.
    """
    if not (text or "").strip():
        return None
    service = get_embedding_service()
    if not service.enabled:
        return None
    return await service.embed_text(text)


async def batch_generate_embeddings(texts: Sequence[str]) -> list[list[float] | None]:
    """
    Generate embeddings for multiple texts. Preserves order.
    Entries are None for failed/disabled or empty inputs.
    """
    if not texts:
        return []
    service = get_embedding_service()
    if not service.enabled:
        return [None for _ in texts]
    return await service.embed_texts(list(texts))
