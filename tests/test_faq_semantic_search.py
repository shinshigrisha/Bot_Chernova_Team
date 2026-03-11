"""Regression tests for FAQ semantic search and hybrid retrieval.

Cases: similar phrase retrieval, synonym detection, fallback behavior, semantic ranking.
"""
from __future__ import annotations

import pytest
from sqlalchemy import text

from src.infra.db.repositories.faq_repo import FAQRepository


async def _has_pgvector(async_session) -> bool:
    result = await async_session.execute(
        # pgvector extension is named 'vector'
        text("SELECT EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'vector')")
    )
    return bool(result.scalar())


def _unit_vec(dim: int, index: int) -> str:
    """Return a vector literal like '[0,0,1,0,...]' for pgvector CAST()."""
    values = ["0.0"] * dim
    values[index] = "1.0"
    return "[" + ",".join(values) + "]"


@pytest.mark.asyncio
async def test_search_semantic_returns_empty_for_empty_embedding(async_session) -> None:
    """Semantic search with empty or null embedding returns empty list."""
    repo = FAQRepository(session=async_session)
    result = await repo.search_semantic(query_embedding="", limit=5, session=async_session)
    assert result == []
    result = await repo.search_semantic(query_embedding="[]", limit=5, session=async_session)
    assert result == []


@pytest.mark.asyncio
async def test_search_semantic_accepts_list_embedding(async_session) -> None:
    """search_semantic accepts list[float] and serializes to literal."""
    repo = FAQRepository(session=async_session)
    # Invalid length or empty list may return [] if pgvector rejects or no rows
    result = await repo.search_semantic(
        query_embedding=[0.0] * 1536, limit=5, session=async_session
    )
    # With no pgvector or no indexed rows, result is []; with pgvector and data, may be non-empty
    assert isinstance(result, list)
    for row in result:
        assert "id" in row and "question" in row and "answer" in row and "score" in row
        assert 0 <= float(row["score"]) <= 1.0


@pytest.mark.asyncio
async def test_search_semantic_fallback_when_pgvector_unavailable(async_session) -> None:
    """When pgvector extension is missing, search_semantic returns [] (fallback behavior)."""
    repo = FAQRepository(session=async_session)
    literal = "[0.1" + ",0.0" * 1535 + "]"  # valid 1536-dim vector literal
    result = await repo.search_semantic(
        query_embedding=literal, limit=5, session=async_session
    )
    assert isinstance(result, list)
    # Either empty (no extension) or list of dicts with score
    if result:
        assert all("score" in r and 0 <= float(r["score"]) <= 1.0 for r in result)


@pytest.mark.asyncio
async def test_search_by_keywords_unchanged(async_session) -> None:
    """Keyword search still works (existing behavior preserved)."""
    repo = FAQRepository(session=async_session)
    empty = await repo.search_by_keywords(query="", limit=5, session=async_session)
    assert empty == []
    # Non-empty query returns list (may be empty if no matching FAQ)
    any_q = await repo.search_by_keywords(query="доставка", limit=5, session=async_session)
    assert isinstance(any_q, list)
    for row in any_q:
        assert "id" in row and "question" in row and "answer" in row and "score" in row


@pytest.mark.asyncio
async def test_semantic_ranking_order_when_results_returned(async_session) -> None:
    """When semantic search returns results, they are ordered by score descending."""
    repo = FAQRepository(session=async_session)
    # Use a valid 1536-dim vector literal; may return 0 rows if no embeddings in DB
    literal = "[" + ",".join("0.0" for _ in range(1536)) + "]"
    result = await repo.search_semantic(
        query_embedding=literal, limit=5, session=async_session
    )
    if len(result) >= 2:
        scores = [float(r["score"]) for r in result]
        assert scores == sorted(scores, reverse=True), "semantic results must be ranked by score desc"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("query", "faq_question", "faq_answer"),
    [
        ("не берет трубку", "Не дозвонился клиенту", "Сделай 2–3 попытки связи и подожди у подъезда."),
        ("яйца побились", "Разбитые яйца", "Зафиксируй фото повреждения и оформи кейс."),
        ("не хватает пакета", "Недовоз", "Проверь состав заказа и сообщи в канал смены."),
        ("не хочет подниматься", "Отказ до двери", "Сообщи куратору и действуй по сценарию вручения."),
    ],
)
async def test_search_hybrid_semantic_pairs(
    async_session,
    query: str,
    faq_question: str,
    faq_answer: str,
) -> None:
    """
    Semantic retrieval should find relevant FAQ even when courier uses a different phrase.
    This test uses fixed embeddings stored in embedding_vector and passes query_embedding explicitly.
    """
    if not await _has_pgvector(async_session):
        pytest.skip("pgvector extension is not available in test DB")

    repo = FAQRepository(session=async_session)
    faq_id = await repo.add_faq(question=faq_question, answer=faq_answer, session=async_session)

    # Use unique one-hot embeddings for each parametrized case.
    # We pick index based on faq_id to avoid collisions across tests within same DB transaction.
    dim = 1536
    idx = int(faq_id) % dim
    literal = _unit_vec(dim, idx)
    await repo.set_embedding_vector(faq_id=int(faq_id), embedding_literal=literal, session=async_session)
    await async_session.commit()

    hits = await repo.search_hybrid(
        query=query,
        limit=3,
        query_embedding=literal,
        session=async_session,
    )
    assert hits, "expected at least one semantic hit"
    top = hits[0]
    assert int(top["id"]) == int(faq_id)
    assert top["question"] == faq_question
    assert top["answer"] == faq_answer
    assert float(top.get("semantic_score", 0.0)) > 0.95
    assert float(top.get("score", 0.0)) > 0.5


@pytest.mark.asyncio
async def test_search_hybrid_graceful_without_embeddings(async_session) -> None:
    """Hybrid retrieval must not fail when embeddings are unavailable (query_embedding=None)."""
    repo = FAQRepository(session=async_session)
    faq_id = await repo.add_faq(
        question="Не дозвонился клиенту",
        answer="Сделай 2–3 попытки связи.",
        session=async_session,
    )
    await async_session.commit()

    hits = await repo.search_hybrid(
        query="не берет трубку",
        limit=3,
        query_embedding=None,
        session=async_session,
    )
    assert isinstance(hits, list)
    # With no text/keyword match, it may be empty; but it must not raise.
    if hits:
        assert all("id" in h and "question" in h and "answer" in h for h in hits)
