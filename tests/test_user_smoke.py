"""Smoke-тесты: UserRole coerce + UserRepository.get_or_create.

Запуск:
    DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/delivery_assistant \
        pytest tests/test_user_smoke.py -v
"""
import pytest
import pytest_asyncio

from src.infra.db.enums import UserRole, UserStatus, coerce_user_role
from src.infra.db.repositories.users import UserRepository

# Используем async_session из conftest (единый lifecycle, изоляция через rollback транзакции).

pytestmark = pytest.mark.smoke


# ---------------------------------------------------------------------------
# Юнит-тесты coerce_user_role (без БД)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "raw, expected",
    [
        # Уже правильный enum-член
        (UserRole.ADMIN,   UserRole.ADMIN),
        (UserRole.VIEWER,  UserRole.VIEWER),
        (UserRole.COURIER, UserRole.COURIER),
        # Lowercase строка (значение в Postgres)
        ("admin",   UserRole.ADMIN),
        ("lead",    UserRole.LEAD),
        ("curator", UserRole.CURATOR),
        ("viewer",  UserRole.VIEWER),
        ("courier", UserRole.COURIER),
        # UPPERCASE (имя Python-члена — исторический источник ошибки)
        ("ADMIN",   UserRole.ADMIN),
        ("LEAD",    UserRole.LEAD),
        ("COURIER", UserRole.COURIER),
        # str(enum) в Python < 3.11 даёт "UserRole.ADMIN"
        ("UserRole.ADMIN",   UserRole.ADMIN),
        ("UserRole.courier", UserRole.COURIER),
        # Пробелы
        ("  admin  ", UserRole.ADMIN),
    ],
)
def test_coerce_valid(raw: str | UserRole, expected: UserRole) -> None:
    assert coerce_user_role(raw) == expected


@pytest.mark.parametrize("bad", ["god", "superadmin", "", "None", "null"])
def test_coerce_invalid_falls_back(bad: str) -> None:
    """Невалидное значение → fallback, без исключения."""
    result = coerce_user_role(bad, default=UserRole.VIEWER)
    assert result == UserRole.VIEWER


def test_coerce_invalid_custom_default() -> None:
    assert coerce_user_role("unknown_role", default=UserRole.COURIER) == UserRole.COURIER


# ---------------------------------------------------------------------------
# Интеграционные тесты UserRepository (требуют БД)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_or_create_admin(async_session) -> None:
    """INSERT users с ролью ADMIN не падает с 'invalid input value'. Default status=GUEST."""
    repo = UserRepository(async_session)
    user = await repo.get_or_create(
        tg_user_id=88_000_001,
        role=UserRole.ADMIN,
        display_name="SmokeAdmin",
    )
    assert user.tg_user_id == 88_000_001
    assert user.role == UserRole.ADMIN
    assert user.display_name == "SmokeAdmin"
    assert user.status == UserStatus.GUEST


@pytest.mark.asyncio
async def test_get_or_create_string_role(async_session) -> None:
    """Строка 'ADMIN' принимается без ошибки (coerce внутри репозитория)."""
    repo = UserRepository(async_session)
    user = await repo.get_or_create(
        tg_user_id=88_000_002,
        role="ADMIN",  # type: ignore[arg-type]  — намеренно строка
        display_name="StringRoleAdmin",
    )
    assert user.role == UserRole.ADMIN


@pytest.mark.asyncio
async def test_get_or_create_idempotent(async_session) -> None:
    """Повторный вызов возвращает тот же объект, display_name обновляется."""
    repo = UserRepository(async_session)
    u1 = await repo.get_or_create(88_000_003, role=UserRole.VIEWER, display_name="First")
    u2 = await repo.get_or_create(88_000_003, role=UserRole.VIEWER, display_name="Updated")
    assert u1.id == u2.id
    assert u2.display_name == "Updated"


@pytest.mark.asyncio
async def test_get_or_create_invalid_role_fallback(async_session) -> None:
    """Невалидная роль → fallback VIEWER (canonical coerce_user_role default), INSERT не падает."""
    repo = UserRepository(async_session)
    user = await repo.get_or_create(
        tg_user_id=88_000_004,
        role="SUPERADMIN",  # type: ignore[arg-type]
        display_name="FallbackUser",
    )
    assert user.role == UserRole.VIEWER


@pytest.mark.asyncio
async def test_get_or_create_with_status_approved(async_session) -> None:
    """При создании с status=APPROVED пользователь получает этот статус (bootstrap admin)."""
    repo = UserRepository(async_session)
    user = await repo.get_or_create(
        tg_user_id=88_000_005,
        role=UserRole.ADMIN,
        display_name="BootstrapAdmin",
        status=UserStatus.APPROVED,
    )
    assert user.tg_user_id == 88_000_005
    assert user.role == UserRole.ADMIN
    assert user.status == UserStatus.APPROVED
