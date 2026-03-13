"""Тесты канонического статус-/роль-based стартового меню."""

import pytest

from src.bot.menu_renderer import show_entrypoint_menu
from src.core.services.access_service import Principal
from src.infra.db.enums import UserRole, UserStatus


class DummyMessage:
    def __init__(self) -> None:
        self.sent: list[tuple[str, object | None]] = []

    async def answer(self, text: str, reply_markup=None) -> None:  # type: ignore[override]
        self.sent.append((text, reply_markup))


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "principal,status,role,expected_prefix",
    [
        # guest: нет пользователя / статус None / GUEST
        (None, None, None, "Для работы с ботом нужна регистрация."),
        (Principal(tg_user_id=1, role=None, status=None), None, None, "Для работы с ботом нужна регистрация."),
        (Principal(tg_user_id=1, role=None, status=UserStatus.GUEST), UserStatus.GUEST, None, "Для работы с ботом нужна регистрация."),
        # pending
        (Principal(tg_user_id=1, role=UserRole.COURIER, status=UserStatus.PENDING), UserStatus.PENDING, UserRole.COURIER, "Ваша заявка на регистрацию уже на рассмотрении."),
        # rejected
        (Principal(tg_user_id=1, role=UserRole.COURIER, status=UserStatus.REJECTED), UserStatus.REJECTED, UserRole.COURIER, "Ваша предыдущая заявка на регистрацию была отклонена."),
        # blocked
        (Principal(tg_user_id=1, role=UserRole.COURIER, status=UserStatus.BLOCKED), UserStatus.BLOCKED, UserRole.COURIER, "Ваш аккаунт заблокирован."),
    ],
)
async def test_show_entrypoint_menu_status_screens(principal, status, role, expected_prefix) -> None:
    msg = DummyMessage()

    await show_entrypoint_menu(msg, principal)

    assert msg.sent, "Сообщение должно быть отправлено"
    text, _ = msg.sent[0]
    assert text.startswith(expected_prefix)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "role,expected_prefix",
    [
        (UserRole.ADMIN, "Админ-меню:"),
        (UserRole.LEAD, "Админ-меню:"),
        (UserRole.COURIER, "Меню курьера:"),
        (UserRole.CURATOR, "Меню куратора:"),
        (UserRole.VIEWER, "Меню куратора:"),
    ],
)
async def test_show_entrypoint_menu_approved_roles(role: UserRole, expected_prefix: str) -> None:
    principal = Principal(tg_user_id=1, role=role, status=UserStatus.APPROVED)
    msg = DummyMessage()

    await show_entrypoint_menu(msg, principal)

    assert msg.sent, "Сообщение должно быть отправлено"
    text, _ = msg.sent[0]
    assert text.startswith(expected_prefix)


def test_admin_main_keyboard_has_required_sections() -> None:
    """Админ-меню содержит все ожидаемые разделы (callback_data), навигация не сломана."""
    from src.bot.keyboards.admin_main import (
        build_admin_main_keyboard,
        VERIFICATION_CB,
        AI_CURATOR_CB,
        FAQ_KB_CB,
        CSV_ANALYSIS_CB,
        MONITORING_CB,
        ASSETS_CB,
        BROADCASTS_CB,
        LEGACY_CB,
    )
    kb = build_admin_main_keyboard()
    flat = [btn.callback_data for row in kb.inline_keyboard for btn in row]
    assert VERIFICATION_CB in flat
    assert AI_CURATOR_CB in flat
    assert FAQ_KB_CB in flat
    assert CSV_ANALYSIS_CB in flat
    assert MONITORING_CB in flat
    assert ASSETS_CB in flat
    assert BROADCASTS_CB in flat
    assert LEGACY_CB in flat

