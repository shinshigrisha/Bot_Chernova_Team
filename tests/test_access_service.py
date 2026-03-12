"""Тесты AccessService: get_principal для guest и по статусу/роли."""

import pytest
from unittest.mock import MagicMock

from src.core.services.access_service import AccessService, Principal
from src.infra.db.repositories.users import UserRepository


def _session_factory(session):
    """Фабрика: при вызове возвращает async context manager с заданной сессией."""
    class _Ctx:
        async def __aenter__(self):
            return session
        async def __aexit__(self, *args):
            pass
    def factory():
        return _Ctx()
    return factory


@pytest.mark.asyncio
async def test_get_principal_returns_guest_when_no_user(async_session) -> None:
    """Когда пользователя нет в БД, get_principal возвращает principal без role/status (guest)."""
    repo = UserRepository(async_session)
    user = await repo.get_by_tg_id(77_000_999)
    assert user is None

    settings = MagicMock()
    settings.admin_ids = []
    settings.enable_new_auth_flow = True
    service = AccessService(
        session_factory=_session_factory(async_session),
        settings=settings,
    )

    principal = await service.get_principal(77_000_999)
    assert principal.tg_user_id == 77_000_999
    assert principal.role is None
    assert principal.status is None
