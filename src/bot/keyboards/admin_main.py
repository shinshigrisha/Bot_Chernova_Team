from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


ADMIN_CB_PREFIX = "admin:"

# Разделы админ-панели V2
VERIFICATION_CB = f"{ADMIN_CB_PREFIX}verification_menu"
AI_CURATOR_CB = f"{ADMIN_CB_PREFIX}ai_menu"
FAQ_KB_CB = f"{ADMIN_CB_PREFIX}faq_menu"
CSV_ANALYSIS_CB = f"{ADMIN_CB_PREFIX}csv_menu"
MONITORING_CB = f"{ADMIN_CB_PREFIX}monitoring_menu"
ASSETS_CB = f"{ADMIN_CB_PREFIX}tmc_menu"
BROADCASTS_CB = f"{ADMIN_CB_PREFIX}broadcast_menu"


def build_admin_main_keyboard() -> InlineKeyboardMarkup:
    """Главное меню админ-панели (V2), меню-first UX."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🧾 Верификация",
                    callback_data=VERIFICATION_CB,
                ),
                InlineKeyboardButton(
                    text="🤖 AI-куратор",
                    callback_data=AI_CURATOR_CB,
                ),
            ],
            [
                InlineKeyboardButton(
                    text="📚 FAQ / база знаний",
                    callback_data=FAQ_KB_CB,
                ),
                InlineKeyboardButton(
                    text="📊 Анализ CSV",
                    callback_data=CSV_ANALYSIS_CB,
                ),
            ],
            [
                InlineKeyboardButton(
                    text="📈 Мониторинг",
                    callback_data=MONITORING_CB,
                ),
                InlineKeyboardButton(
                    text="📢 Рассылка",
                    callback_data=BROADCASTS_CB,
                ),
            ],
            [
                InlineKeyboardButton(
                    text="⚙️ ТМЦ",
                    callback_data=ASSETS_CB,
                ),
            ],
        ]
    )
