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
from src.infra.db.repositories.verification_applications import (
    VerificationApplicationRepository,
)


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


@pytest.mark.asyncio
async def test_apply_admin_decision_updates_status(session_factory) -> None:
    service = VerificationService(session_factory)

    # Сначала создаём пользователя со статусом PENDING.
    payload = VerificationApplicationPayload(
        tg_user_id=99_000_002,
        role=UserRole.COURIER,
        first_name="Test",
        last_name="User",
        tt_number="123",
        ds_code="DS-TEST",
        phone="+70000000000",
    )
    await service.create_application_and_mark_pending(payload)

    # Применяем решение "approve".
    new_status = await service.apply_admin_decision(
        tg_user_id=payload.tg_user_id,
        decision="approve",
    )

    async with session_factory() as session:
        repo = UserRepository(session)
        user = await repo.get_by_tg_id(payload.tg_user_id)

    assert new_status == UserStatus.APPROVED
    assert user is not None
    assert user.status == UserStatus.APPROVED


@pytest.mark.asyncio
async def test_apply_admin_decision_reject(session_factory) -> None:
    """При reject пользователь переходит в REJECTED."""
    service = VerificationService(session_factory)
    payload = VerificationApplicationPayload(
        tg_user_id=99_000_003,
        role=UserRole.CURATOR,
        first_name="Reject",
        last_name="User",
        tt_number="456",
        ds_code="DS-TEST",
        phone="+70000000001",
    )
    await service.create_application_and_mark_pending(payload)
    new_status = await service.apply_admin_decision(
        tg_user_id=payload.tg_user_id,
        decision="reject",
    )
    async with session_factory() as session:
        repo = UserRepository(session)
        user = await repo.get_by_tg_id(payload.tg_user_id)
    assert new_status == UserStatus.REJECTED
    assert user is not None
    assert user.status == UserStatus.REJECTED


@pytest.mark.asyncio
async def test_apply_admin_decision_block(session_factory) -> None:
    """При block пользователь переходит в BLOCKED."""
    service = VerificationService(session_factory)
    payload = VerificationApplicationPayload(
        tg_user_id=99_000_004,
        role=UserRole.COURIER,
        first_name="Block",
        last_name="User",
        tt_number="789",
        ds_code="DS-TEST",
        phone="+70000000002",
    )
    await service.create_application_and_mark_pending(payload)
    new_status = await service.apply_admin_decision(
        tg_user_id=payload.tg_user_id,
        decision="block",
    )
    async with session_factory() as session:
        repo = UserRepository(session)
        user = await repo.get_by_tg_id(payload.tg_user_id)
    assert new_status == UserStatus.BLOCKED
    assert user is not None
    assert user.status == UserStatus.BLOCKED


@pytest.mark.asyncio
async def test_apply_admin_decision_updates_application_resolution(session_factory) -> None:
    """После apply_admin_decision у последней заявки пользователя проставляются decision и resolved_at."""
    service = VerificationService(session_factory)
    payload = VerificationApplicationPayload(
        tg_user_id=99_000_005,
        role=UserRole.COURIER,
        first_name="Res",
        last_name="User",
        tt_number="111",
        ds_code="DS-TEST",
        phone="+70000000003",
    )
    await service.create_application_and_mark_pending(payload)
    await service.apply_admin_decision(
        tg_user_id=payload.tg_user_id,
        decision="approve",
    )
    async with session_factory() as session:
        app_repo = VerificationApplicationRepository(session)
        apps = await app_repo.list_for_user(payload.tg_user_id)
    assert len(apps) >= 1
    latest = apps[0]
    assert latest.decision == "approve"
    assert latest.resolved_at is not None


@pytest.mark.asyncio
async def test_apply_admin_decision_raises_when_user_not_found(session_factory) -> None:
    """apply_admin_decision не создаёт пользователя; при отсутствии в БД — ValueError."""
    service = VerificationService(session_factory)
    with pytest.raises(ValueError, match="User not found"):
        await service.apply_admin_decision(
            tg_user_id=99_000_999,
            decision="approve",
        )
