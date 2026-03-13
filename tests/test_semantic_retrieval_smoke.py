"""Smoke validation for canonical embeddings and retrieval flows.

- Canonical embeddings: embedding_service.get_embedding_service(), generate_embedding().
- Retrieval: RAG build_context returns valid RAGKnowledgeContext; retrieval_stage in (none|semantic|hybrid).
- Known cases: golden_cases.jsonl прогоняется через scripts/smoke_ai.py (ручной запуск).
"""

from __future__ import annotations

import pytest

from src.core.services.ai.embedding_service import (
    get_embedding_service,
    generate_embedding,
)
from src.core.services.ai.embeddings_service import EmbeddingsService
from src.core.services.ai.intent_engine import IntentDetectionResult
from src.core.services.ai.rag_service import RAGService, RAGKnowledgeContext


pytestmark = pytest.mark.smoke


def test_canonical_embedding_service_returns_embeddings_service() -> None:
    """Единая точка входа: get_embedding_service() возвращает EmbeddingsService."""
    service = get_embedding_service()
    assert isinstance(service, EmbeddingsService)


@pytest.mark.asyncio
async def test_generate_embedding_empty_input_returns_none() -> None:
    """Пустой текст -> None (canonical flow)."""
    result = await generate_embedding("")
    assert result is None
    result = await generate_embedding("   ")
    assert result is None


@pytest.mark.asyncio
async def test_generate_embedding_disabled_returns_none_or_list() -> None:
    """При отключённых эмбеддингах (нет ключа) возвращается None; иначе list[float]."""
    result = await generate_embedding("тест")
    assert result is None or (isinstance(result, list) and len(result) > 0)


def test_rag_knowledge_context_has_retrieval_stage() -> None:
    """RAGKnowledgeContext содержит поле retrieval_stage из допустимого набора."""
    ctx = RAGKnowledgeContext(
        question="?",
        intent=IntentDetectionResult(
            intent="unknown",
            confidence=0.0,
            matched_keywords=[],
            matched_catalog_intent=None,
        ),
        high_risk=False,
        retrieval_stage="none",
    )
    assert ctx.retrieval_stage in ("none", "keyword", "semantic", "hybrid")


@pytest.mark.asyncio
async def test_rag_build_context_returns_valid_structure(async_session) -> None:
    """RAGService.build_context возвращает RAGKnowledgeContext с полями question, intent, retrieval_stage."""
    from contextlib import asynccontextmanager

    @asynccontextmanager
    async def session_factory():
        yield async_session

    rag = RAGService(session_factory=session_factory, data_root="data/ai")
    ctx = await rag.build_context("Курьер опаздывает")
    assert isinstance(ctx, RAGKnowledgeContext)
    assert ctx.question == "Курьер опаздывает"
    assert hasattr(ctx.intent, "intent")
    assert ctx.retrieval_stage in ("none", "keyword", "semantic", "hybrid")
    assert isinstance(ctx.context_text, str)
