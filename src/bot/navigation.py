"""Canonical navigation and root menu callbacks and handlers."""

from __future__ import annotations

from aiogram import F, Router
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
async def root_main(callback: CallbackQuery) -> None:
    """Показать главное меню.

    На этом этапе задачи мы не делаем сложной логики выбора меню по ролям/статусам,
    а просто отображаем базовый каркас менюшки.
    """
    # Ленивый импорт, чтобы избежать циклической зависимости:
    # root_menu → navigation (константы ROOT_*) и navigation → root_menu (клавиатура).
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
async def root_admin(callback: CallbackQuery) -> None:
    """Заглушка для входа в админ-панель из меню.

    Полная миграция админки реализуется в отдельной задаче.
    """
    await callback.message.answer(
        "Админ-панель скоро будет доступна из главного меню.\n"
        "Пока используйте команду /admin.",
    )
    await callback.answer()


@router.callback_query(F.data == ROOT_HELP)
async def root_help(callback: CallbackQuery) -> None:
    """Базовый раздел помощи."""
    await callback.message.answer(
        "Это бот Delivery Assistant.\n"
        "Используйте кнопки меню ниже для навигации. "
        "Главная точка входа — команда /start.",
    )
    await callback.answer()


@router.callback_query(F.data == "nav:main")
async def nav_main(
    callback: CallbackQuery,
    access_service: AccessService | None = None,
) -> None:
    """Вернуться в главное меню с учётом роли (курьер/куратор/админ)."""
    from src.bot.menu_renderer import show_entrypoint_menu

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

