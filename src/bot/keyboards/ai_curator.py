"""Клавиатуры для раздела AI-куратор: быстрые кейсы и навигация назад."""

from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from src.bot.navigation import NAV_MAIN

# Префикс callback для быстрых кейсов (текст передаётся в AI как есть)
AI_CURATOR_CB_PREFIX = "ai_curator:case:"

# Порядок кнопок по ТЗ; ключ кейса -> текст для запроса к AI
QUICK_CASE_ORDER: list[tuple[str, str]] = [
    ("client_no_answer", "Клиент не отвечает"),
    ("missing_items", "Недовоз"),
    ("damaged_goods", "Разбил товар"),
    ("payment_fail", "Не проходит оплата"),
    ("late", "Опаздываю"),
    ("address_issue", "Проблема с адресом"),
]
QUICK_CASE_LABELS: dict[str, str] = dict(QUICK_CASE_ORDER)

# Кнопка «Другое» — пользователь вводит текст сам
AI_CURATOR_OTHER = f"{AI_CURATOR_CB_PREFIX}other"


def build_ai_curator_intro_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура приветствия: быстрые кейсы (порядок по ТЗ) + Другое."""
    rows: list[list[InlineKeyboardButton]] = []
    for key, label in QUICK_CASE_ORDER:
        rows.append(
            [
                InlineKeyboardButton(
                    text=label,
                    callback_data=f"{AI_CURATOR_CB_PREFIX}{key}",
                )
            ]
        )
    rows.append(
        [
            InlineKeyboardButton(
                text="Другое",
                callback_data=AI_CURATOR_OTHER,
            )
        ]
    )
    return InlineKeyboardMarkup(inline_keyboard=rows)


def build_ai_curator_back_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура «Назад в главное меню» после ответа AI."""
    from .navigation import main_menu_button

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [main_menu_button(NAV_MAIN)],
        ]
    )
