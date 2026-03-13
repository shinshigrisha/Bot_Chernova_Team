"""Helpers to render canonical, role/status-based menus from handlers.

Strict gating: guest -> registration; pending -> waiting; rejected -> reapply;
blocked -> blocked screen; approved -> menu by role (admin/courier/curator).
"""

from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message

from src.bot.keyboards.admin_main import build_admin_main_keyboard


def get_admin_root_message() -> str:
    """Единый текст главного экрана админ-панели с описанием разделов (legacy-style)."""
    return (
        "Админ-меню:\n\n"
        "Разделы: Верификация заявок • AI-куратор • FAQ и база знаний • "
        "Анализ CSV • Мониторинг • Рассылки • ТМЦ. "
        "В каждом разделе — кнопки «Назад» и «Главное меню»."
    )
from src.bot.keyboards.courier_main import build_courier_main_keyboard
from src.bot.keyboards.curator_main import build_curator_main_keyboard
from src.bot.keyboards.root_menu import build_root_menu_keyboard
from src.bot.keyboards.verification import build_registration_entry_keyboard
from src.bot.navigation import ROOT_VERIFICATION
from src.core.services.access_service import Principal
from src.infra.db.enums import UserRole, UserStatus


async def show_root_menu(message: Message, role: UserRole | str | None = None) -> None:
    """Показать простое корневое меню (без учёта статуса).

    Сохранено для обратной совместимости и вспомогательных сценариев.
    """
    await message.answer(
        "Выберите действие в меню ниже:",
        reply_markup=build_root_menu_keyboard(role=role),
    )


async def show_entrypoint_menu(message: Message, principal: Principal | None) -> None:
    """Показать экран/меню по канонической таблице: статус -> экран, approved -> роль."""
    # guest: нет записи в БД (None) или явный статус guest
    if principal is None or principal.status is None or principal.status == UserStatus.GUEST:
        await message.answer(
            "Для работы с ботом нужна регистрация. "
            "Нажмите кнопку ниже, чтобы подать заявку.",
            reply_markup=build_registration_entry_keyboard(),
        )
        return

    status = principal.status
    role = principal.role

    if status == UserStatus.PENDING:
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="🔄 Обновить статус",
                        callback_data="pending:refresh",
                    )
                ]
            ]
        )
        await message.answer(
            "Ваша заявка на регистрацию уже на рассмотрении.\n"
            "Ожидайте подтверждения от администратора.",
            reply_markup=keyboard,
        )
        return

    if status == UserStatus.REJECTED:
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="🔁 Подать новую заявку",
                        callback_data=ROOT_VERIFICATION,
                    )
                ]
            ]
        )
        await message.answer(
            "Ваша предыдущая заявка на регистрацию была отклонена.\n"
            "Вы можете подать новую заявку, если данные были скорректированы.",
            reply_markup=keyboard,
        )
        return

    if status == UserStatus.BLOCKED:
        await message.answer(
            "Ваш аккаунт заблокирован.\n"
            "Если вы считаете, что это ошибка, обратитесь к вашему куратору или администратору.",
        )
        return

    if status == UserStatus.APPROVED:
        if role in (UserRole.ADMIN, UserRole.LEAD):
            await message.answer(
                get_admin_root_message(),
                reply_markup=build_admin_main_keyboard(),
            )
            return
        if role == UserRole.COURIER:
            await message.answer(
                "Меню курьера:",
                reply_markup=build_courier_main_keyboard(),
            )
            return
        if role in (UserRole.CURATOR, UserRole.VIEWER):
            await message.answer(
                "Меню куратора:",
                reply_markup=build_curator_main_keyboard(),
            )
            return
        # approved but unknown role -> root menu (no default to courier)
        await show_root_menu(message, role=role)
        return

    # неизвестный статус -> базовое корневое меню
    await show_root_menu(message, role=role)

