from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from src.bot.navigation import ROOT_AI_CURATOR


def build_courier_main_keyboard() -> InlineKeyboardMarkup:
    """Базовое меню курьера (каркас, без бизнес-логики)."""
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
        ]
    )

