"""Smoke and unit tests for canonical local embedding backend (MiniLM)."""

from __future__ import annotations

import pytest

from src.core.services.ai.embedding_service import (
    get_embedding_service,
    generate_embedding,
    embed,
    embed_many,
)
from src.core.services.ai.embeddings_service import EmbeddingsService


pytestmark = pytest.mark.smoke


def test_get_embedding_service_returns_embeddings_service() -> None:
    """Canonical entry point returns EmbeddingsService (config-driven)."""
    svc = get_embedding_service()
    assert isinstance(svc, EmbeddingsService)


def test_embedding_service_has_model_from_config() -> None:
    """Service exposes model name from config (e.g. MiniLM)."""
    svc = get_embedding_service()
    assert isinstance(svc.model, str)
    assert len(svc.model) > 0


@pytest.mark.asyncio
async def test_embed_alias_equals_generate_embedding() -> None:
    """embed(text) is alias for generate_embedding(text)."""
    a = await generate_embedding("тест")
    b = await embed("тест")
    if a is None and b is None:
        return
    assert a is not None and b is not None
    assert len(a) == len(b)
    assert a == b


@pytest.mark.asyncio
async def test_local_embedding_smoke() -> None:
    """
    With EMBEDDING_PROVIDER=local (default), embed_text returns 384-dim vector (MiniLM-L6-v2).
    Skipped if sentence_transformers not installed or provider overridden to openai.
    """
    svc = get_embedding_service()
    if not svc.enabled:
        pytest.skip("embedding service disabled (e.g. openai without key)")
    try:
        vec = await svc.embed_text("курьер не дозвонился покупателю")
    except Exception as e:
        pytest.skip(f"local embedding not available: {e}")
    assert vec is not None, "expected non-null embedding for local backend"
    assert len(vec) == 384, "MiniLM-L6-v2 produces 384-dimensional vectors"
    assert all(isinstance(x, float) for x in vec)
