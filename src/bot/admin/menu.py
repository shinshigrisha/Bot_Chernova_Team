"""Legacy admin menu helpers (keyboard builders).

Каноническая точка входа в админку и обработка разделов — в admin_handlers.py.
Здесь только вспомогательные клавиатуры для обратной совместимости.
"""

from aiogram.types import InlineKeyboardMarkup

from src.bot.keyboards.admin_main import (
    build_admin_main_keyboard,
    build_legacy_keyboard,
)


def get_legacy_admin_keyboard() -> InlineKeyboardMarkup:
    """Legacy-подменю (ТМЦ, журнал, импорт CSV, настройки, мониторинг)."""
    return build_legacy_keyboard()


def get_root_admin_keyboard_with_legacy() -> InlineKeyboardMarkup:
    """Главное меню админки с рядом Legacy (совпадает с build_admin_main_keyboard)."""
    return build_admin_main_keyboard()
