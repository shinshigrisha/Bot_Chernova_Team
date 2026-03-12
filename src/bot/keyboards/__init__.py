"""Keyboard helpers and canonical menu layouts."""

from .common import (
    BACK_TEXT,
    CANCEL_TEXT,
    HELP_TEXT,
    MAIN_MENU_TEXT,
    build_common_nav,
    build_nav_keyboard,
)
from .root_menu import build_root_menu_keyboard
from .verification import (
    VERIFICATION_CB_PREFIX,
    build_confirmation_keyboard,
    build_registration_entry_keyboard,
    build_role_choice_keyboard,
)

__all__ = [
    # Навигация
    "BACK_TEXT",
    "MAIN_MENU_TEXT",
    "CANCEL_TEXT",
    "HELP_TEXT",
    "build_nav_keyboard",
    "build_common_nav",
    # Корневое меню
    "build_root_menu_keyboard",
    # Верификация
    "VERIFICATION_CB_PREFIX",
    "build_registration_entry_keyboard",
    "build_role_choice_keyboard",
    "build_confirmation_keyboard",
]

