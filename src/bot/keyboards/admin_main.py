from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


ADMIN_CB_PREFIX = "admin:"

POLL_GROUPS_CB = f"{ADMIN_CB_PREFIX}polls_groups"
ASSETS_CB = f"{ADMIN_CB_PREFIX}assets"
CSV_ANALYSIS_CB = f"{ADMIN_CB_PREFIX}csv_analysis"
AI_CURATOR_CB = f"{ADMIN_CB_PREFIX}ai_curator"
BROADCASTS_CB = f"{ADMIN_CB_PREFIX}broadcasts"
MONITORING_CB = f"{ADMIN_CB_PREFIX}monitoring"


def build_admin_main_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="📋 Опросы и группы",
                    callback_data=POLL_GROUPS_CB,
                )
            ],
            [
                InlineKeyboardButton(
                    text="⚙️ Учет ТМЦ",
                    callback_data=ASSETS_CB,
                )
            ],
            [
                InlineKeyboardButton(
                    text="📊 Анализ CSV",
                    callback_data=CSV_ANALYSIS_CB,
                )
            ],
            [
                InlineKeyboardButton(
                    text="🤖 AI куратор",
                    callback_data=AI_CURATOR_CB,
                )
            ],
            [
                InlineKeyboardButton(
                    text="📢 Рассылка",
                    callback_data=BROADCASTS_CB,
                )
            ],
            [
                InlineKeyboardButton(
                    text="📈 Мониторинг",
                    callback_data=MONITORING_CB,
                )
            ],
        ]
    )

