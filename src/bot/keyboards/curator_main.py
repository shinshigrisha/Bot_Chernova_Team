from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from src.bot.keyboards.navigation import help_button, main_menu_button
from src.bot.navigation import NAV_HELP, NAV_MAIN, ROOT_AI_CURATOR


def build_curator_main_keyboard() -> InlineKeyboardMarkup:
    """Базовое меню куратора: разделы + навигация (Главное меню, Помощь)."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🤖 AI-куратор",
                    callback_data=ROOT_AI_CURATOR,
                )
            ],
            [
                InlineKeyboardButton(
                    text="📊 Аналитика доставок",
                    callback_data="curator:analytics",
                )
            ],
            [
                InlineKeyboardButton(
                    text="📚 FAQ и регламенты",
                    callback_data="curator:faq",
                )
            ],
            [main_menu_button(NAV_MAIN), help_button(NAV_HELP)],
        ]
    )

