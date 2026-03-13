from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from src.bot.keyboards.navigation import help_button, main_menu_button
from src.bot.navigation import NAV_HELP, NAV_MAIN, ROOT_AI_CURATOR


def build_courier_main_keyboard() -> InlineKeyboardMarkup:
    """Базовое меню курьера: разделы + навигация (Главное меню, Помощь)."""
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
                    text="📦 Мои смены и заказы",
                    callback_data="courier:shifts",
                )
            ],
            [
                InlineKeyboardButton(
                    text="❓ FAQ и правила",
                    callback_data="courier:faq",
                )
            ],
            [main_menu_button(NAV_MAIN), help_button(NAV_HELP)],
        ]
    )

