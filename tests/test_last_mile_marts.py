"""Тесты витрин последней мили: raw_orders, mart_orders_enriched и производные view."""
import pytest
import pytest_asyncio
from sqlalchemy import text


@pytest_asyncio.fixture
async def ensure_marts(async_session):
    """Миграции с витринами уже применены через conftest._ensure_migrations."""
    yield async_session


@pytest.mark.asyncio
async def test_raw_orders_table_exists(ensure_marts):
    """Таблица raw_orders создана и доступна."""
    result = await ensure_marts.execute(
        text(
            """
            SELECT column_name FROM information_schema.columns
            WHERE table_name = 'raw_orders'
            ORDER BY ordinal_position
            """
        )
    )
    names = [row[0] for row in result.fetchall()]
    assert len(names) >= 1
    assert "id" in names
    assert len(names) >= 5


@pytest.mark.asyncio
async def test_mart_orders_enriched_view_exists_and_selectable(ensure_marts):
    """Представление mart_orders_enriched существует и по нему можно выполнить SELECT."""
    result = await ensure_marts.execute(text("SELECT 1 FROM mart_orders_enriched LIMIT 1"))
    result.fetchall()


@pytest.mark.asyncio
async def test_mart_service_rollout_views_selectable(ensure_marts):
    """Витрины раскатки и качества доступны для запроса."""
    for view_name in (
        "mart_service_rollout_cluster",
        "mart_service_rollout_tt",
        "mart_tt_quality",
        "mart_courier_violations",
    ):
        result = await ensure_marts.execute(text(f"SELECT 1 FROM {view_name} LIMIT 1"))
        result.fetchall()
