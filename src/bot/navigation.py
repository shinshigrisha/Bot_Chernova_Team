"""Canonical navigation and root menu callbacks and handlers."""

from __future__ import annotations

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from src.bot.keyboards.verification import build_registration_entry_keyboard
from src.core.services.access_service import AccessService

router = Router(name="navigation")

# Корневой префикс для главного меню
ROOT_CB_PREFIX = "root:"

ROOT_MAIN = f"{ROOT_CB_PREFIX}main"
ROOT_VERIFICATION = f"{ROOT_CB_PREFIX}verification"
ROOT_ADMIN = f"{ROOT_CB_PREFIX}admin"
ROOT_HELP = f"{ROOT_CB_PREFIX}help"
ROOT_AI_CURATOR = f"{ROOT_CB_PREFIX}ai_curator"

# Паттерны для переиспользуемой навигации
NAV_CB_PREFIX = "nav:"

NAV_BACK = f"{NAV_CB_PREFIX}back"
NAV_MAIN = f"{NAV_CB_PREFIX}main"
NAV_CANCEL = f"{NAV_CB_PREFIX}cancel"
NAV_HELP = f"{NAV_CB_PREFIX}help"


@router.callback_query(F.data == ROOT_MAIN)
async def root_main(
    callback: CallbackQuery,
    access_service: AccessService | None = None,
) -> None:
    """Показать главное меню. При ENABLE_MENU_V2 — роль/статус-based меню."""
    from src.config import get_settings
    settings = get_settings()
    if getattr(settings, "enable_menu_v2", False) and access_service:
        from src.bot.menu_renderer import show_entrypoint_menu
        tg_user_id = callback.from_user.id if callback.from_user else 0
        try:
            principal = await access_service.get_principal(tg_user_id)
            await show_entrypoint_menu(callback.message, principal)
        except Exception:
            from src.bot.keyboards.root_menu import build_root_menu_keyboard
            await callback.message.answer(
                "Главное меню:",
                reply_markup=build_root_menu_keyboard(role=None),
            )
        await callback.answer()
        return
    from src.bot.keyboards.root_menu import build_root_menu_keyboard
    await callback.message.answer(
        "Главное меню:",
        reply_markup=build_root_menu_keyboard(role=None),
    )
    await callback.answer()


@router.callback_query(F.data == ROOT_VERIFICATION)
async def root_verification(callback: CallbackQuery) -> None:
    """Вход в верификационный флоу через единый корневой пункт."""
    await callback.message.answer(
        "Регистрация и верификация:",
        reply_markup=build_registration_entry_keyboard(),
    )
    await callback.answer()


@router.callback_query(F.data == ROOT_ADMIN)
async def root_admin(
    callback: CallbackQuery,
    access_service: AccessService | None = None,
) -> None:
    """Вход в админ-панель из главного меню."""
    from src.bot.keyboards.admin_main import build_admin_main_keyboard
    from src.bot.menu_renderer import get_admin_root_message

    if access_service is None:
        await callback.message.answer("Админ-панель временно недоступна. Нажмите /start.")
        await callback.answer()
        return

    tg_user_id = callback.from_user.id if callback.from_user else 0
    if not await access_service.can_access_admin(tg_user_id):
        await callback.answer("Доступ к админ-панели запрещён.", show_alert=True)
        return

    await callback.message.answer(
        get_admin_root_message(),
        reply_markup=build_admin_main_keyboard(),
    )
    await callback.answer()


@router.callback_query(F.data == ROOT_HELP)
async def root_help(callback: CallbackQuery) -> None:
    """Базовый раздел помощи (menu-first, без упора на slash-команды)."""
    await callback.message.answer(
        "Это бот Delivery Assistant.\n\n"
        "Используйте кнопки меню для навигации. "
        "В разделах доступны: «Назад», «Главное меню», «Отмена», «Помощь».",
    )
    await callback.answer()


@router.callback_query(F.data.in_({NAV_MAIN, NAV_BACK}))
async def nav_main(
    callback: CallbackQuery,
    state: FSMContext,
    access_service: AccessService | None = None,
) -> None:
    """«Главное меню» / «Назад» — возврат в корневое меню с учётом роли; сброс FSM."""
    from src.bot.menu_renderer import show_entrypoint_menu

    await state.clear()
    if access_service is None:
        await callback.message.answer("Меню временно недоступно. Нажмите /start.")
        await callback.answer()
        return
    try:
        tg_user_id = callback.from_user.id if callback.from_user else 0
        principal = await access_service.get_principal(tg_user_id)
        await show_entrypoint_menu(callback.message, principal)
    except Exception:
        await callback.message.answer("Ошибка загрузки меню. Нажмите /start.")
    await callback.answer()


@router.callback_query(F.data == NAV_CANCEL)
async def nav_cancel(
    callback: CallbackQuery,
    state: FSMContext,
    access_service: AccessService | None = None,
) -> None:
    """Отмена текущего действия и возврат в главное меню по роли; сброс FSM."""
    from src.bot.menu_renderer import show_entrypoint_menu

    await state.clear()
    if access_service is None:
        await callback.message.answer("Действие отменено. Нажмите /start.")
        await callback.answer()
        return
    try:
        tg_user_id = callback.from_user.id if callback.from_user else 0
        principal = await access_service.get_principal(tg_user_id)
        await callback.message.answer("Действие отменено.")
        await show_entrypoint_menu(callback.message, principal)
    except Exception:
        await callback.message.answer("Действие отменено. Нажмите /start.")
    await callback.answer()


@router.callback_query(F.data == NAV_HELP)
async def nav_help(
    callback: CallbackQuery,
    access_service: AccessService | None = None,
) -> None:
    """Помощь с кнопкой возврата в главное меню."""
    from src.bot.keyboards.navigation import build_nav_keyboard
    help_text = (
        "Помощь: используйте кнопки меню для навигации. "
        "В разделах: «Назад», «Главное меню», «Отмена», «Помощь»."
    )
    kb = build_nav_keyboard(main_cb=NAV_MAIN)
    await callback.message.answer(help_text, reply_markup=kb)
    await callback.answer()

