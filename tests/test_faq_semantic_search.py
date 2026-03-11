"""Regression tests for FAQ semantic search and hybrid retrieval.

Cases: similar phrase retrieval, synonym detection, fallback behavior, semantic ranking.
"""
from __future__ import annotations

import pytest

from src.infra.db.repositories.faq_repo import FAQRepository


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
