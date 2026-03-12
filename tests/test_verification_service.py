"""Тесты для VerificationService: создание заявки и смена статуса пользователя."""

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.core.services.verification_service import (
    VerificationApplicationPayload,
    VerificationService,
)
from src.infra.db.enums import UserRole, UserStatus
from src.infra.db.repositories.users import UserRepository


@pytest_asyncio.fixture
async def session_factory(async_engine) -> async_sessionmaker[AsyncSession]:
    """Локальная фабрика сессий поверх тестового движка.

    Используем отдельную фабрику, чтобы не мешать общей фикстуре async_session,
    но при этом каждая сессия живёт в рамках одного тестового движка.
    """
    return async_sessionmaker(
        bind=async_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
        autocommit=False,
    )


@pytest.mark.asyncio
async def test_create_application_sets_pending_status(session_factory) -> None:
    service = VerificationService(session_factory)

    payload = VerificationApplicationPayload(
        tg_user_id=99_000_001,
        role=UserRole.COURIER,
        first_name="Test",
        last_name="User",
        tt_number="123",
        ds_code="DS-TEST",
        phone="+70000000000",
    )

    await service.create_application_and_mark_pending(payload)

    async with session_factory() as session:
        repo = UserRepository(session)
        user = await repo.get_by_tg_id(payload.tg_user_id)

    assert user is not None
    assert user.role == UserRole.COURIER
    assert user.status == UserStatus.PENDING


