"""Pytest fixtures for Delivery Assistant tests."""
import os
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine


def _normalize_db_url_sslmode(url: str) -> str:
    """Убирает sslmode/ssl_mode из URL: asyncpg принимает только disable|allow|prefer|require|verify-ca|verify-full, не false/true."""
    if not url or "postgres" not in (url.split(":")[0] or "").lower():
        return url
    parsed = urlparse(url)
    if not parsed.query:
        return url
    params = parse_qs(parsed.query, keep_blank_values=True)
    params.pop("sslmode", None)
    params.pop("ssl_mode", None)
    if not params:
        return urlunparse(parsed._replace(query=""))
    return urlunparse(parsed._replace(query=urlencode(params, doseq=True)))


# Use test DB URL; schema must exist (run: DATABASE_URL=<url> alembic upgrade head)
_TEST_DB_URL_RAW = os.environ.get(
    "TEST_DATABASE_URL",
    os.environ.get("DATABASE_URL", "postgresql+asyncpg://user:pass@localhost:5432/delivery_assistant"),
)
TEST_DATABASE_URL = _normalize_db_url_sslmode(_TEST_DB_URL_RAW)


# Локальные тесты без SSL; иначе asyncpg подхватывает PGSSLMODE=false из env и падает (ожидает disable, не false)
_TEST_CONNECT_ARGS = {"ssl": False}


@pytest_asyncio.fixture
async def async_engine():
    """Engine создаётся и уничтожается на каждый тест (тот же event loop, что и у теста)."""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        echo=False,
        pool_pre_ping=True,
        connect_args=_TEST_CONNECT_ARGS,
    )
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture
async def async_session(async_engine):
    """Сессия в рамках одной транзакции; после теста транзакция откатывается — без загрязнения БД между тестами.
    Тесты могут вызывать commit(); откат внешней транзакции в teardown отменяет все изменения (create_savepoint)."""
    connection = await async_engine.connect()
    transaction = await connection.begin()
    factory = async_sessionmaker(
        bind=connection,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
        join_transaction_mode="create_savepoint",
    )
    async with factory() as session:
        yield session
    await transaction.rollback()
    await connection.close()
