from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from src.bot.navigation import ROOT_AI_CURATOR


def build_curator_main_keyboard() -> InlineKeyboardMarkup:
    """Базовое меню куратора (каркас, без бизнес-логики)."""
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
        ]
    )

