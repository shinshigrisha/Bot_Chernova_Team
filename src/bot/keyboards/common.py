"""Общие текстовые константы и переиспользуемые клавиатуры."""

from aiogram.types import InlineKeyboardMarkup

from .navigation import (
    BACK_TEXT,
    CANCEL_TEXT,
    HELP_TEXT,
    MAIN_MENU_TEXT,
    build_nav_keyboard,
)

__all__ = [
    "BACK_TEXT",
    "MAIN_MENU_TEXT",
    "CANCEL_TEXT",
    "HELP_TEXT",
    "build_nav_keyboard",
    "build_common_nav",
]


def build_common_nav() -> InlineKeyboardMarkup:
    """Стандартная навигация: Назад / Главное меню / Отмена / Помощь.

    Конкретные callback_data заполняются на стороне хендлеров через NAV_* константы.
    """
    from src.bot.navigation import NAV_BACK, NAV_MAIN, NAV_CANCEL, NAV_HELP

    return build_nav_keyboard(
        back_cb=NAV_BACK,
        main_cb=NAV_MAIN,
        cancel_cb=NAV_CANCEL,
        help_cb=NAV_HELP,
    )

