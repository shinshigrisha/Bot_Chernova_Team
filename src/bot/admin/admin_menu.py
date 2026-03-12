from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from src.bot.keyboards.admin_main import (
    ADMIN_CB_PREFIX,
    AI_CURATOR_CB,
    ASSETS_CB,
    BROADCASTS_CB,
    CSV_ANALYSIS_CB,
    FAQ_KB_CB,
    MONITORING_CB,
    VERIFICATION_CB,
    build_admin_main_keyboard,
)
from src.bot.keyboards.navigation import build_nav_keyboard
from src.bot.navigation import NAV_CANCEL, NAV_MAIN


ADMIN_BACK_CB = f"{ADMIN_CB_PREFIX}back"
ADMIN_CANCEL_CB = f"{ADMIN_CB_PREFIX}cancel"


def build_admin_main_menu() -> InlineKeyboardMarkup:
    """Обёртка вокруг канонического admin main keyboard."""
    return build_admin_main_keyboard()


def build_section_nav_keyboard() -> InlineKeyboardMarkup:
    """Навигация для экранов разделов: Назад / Главное меню / Отмена."""
    return build_nav_keyboard(
        back_cb=ADMIN_BACK_CB,
        main_cb=NAV_MAIN,
        cancel_cb=ADMIN_CANCEL_CB,
        help_cb=None,
    )


def with_section_nav(
    rows: list[list[InlineKeyboardButton]] | None = None,
) -> InlineKeyboardMarkup:
    """Добавить к разделу навигационные кнопки."""
    nav = build_section_nav_keyboard()
    all_rows: list[list[InlineKeyboardButton]] = []
    if rows:
        all_rows.extend(rows)
    all_rows.extend(nav.inline_keyboard)
    return InlineKeyboardMarkup(inline_keyboard=all_rows)


__all__ = [
    "ADMIN_CB_PREFIX",
    "VERIFICATION_CB",
    "AI_CURATOR_CB",
    "FAQ_KB_CB",
    "CSV_ANALYSIS_CB",
    "MONITORING_CB",
    "ASSETS_CB",
    "BROADCASTS_CB",
    "ADMIN_BACK_CB",
    "ADMIN_CANCEL_CB",
    "build_admin_main_menu",
    "build_section_nav_keyboard",
    "with_section_nav",
]

