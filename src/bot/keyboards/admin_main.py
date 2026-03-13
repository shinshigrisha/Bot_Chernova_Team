from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

# Единый стиль callback (см. docs/LEGACY_UX_AUDIT_AND_MIGRATION_MAP.md):
# admin:<section>_menu — вход в раздел; admin:back_to_main — возврат; admin:<section>:<action> — действие.
ADMIN_CB_PREFIX = "admin:"

# Разделы админ-панели V2
VERIFICATION_CB = f"{ADMIN_CB_PREFIX}verification_menu"
AI_CURATOR_CB = f"{ADMIN_CB_PREFIX}ai_menu"
FAQ_KB_CB = f"{ADMIN_CB_PREFIX}faq_menu"
CSV_ANALYSIS_CB = f"{ADMIN_CB_PREFIX}csv_menu"
MONITORING_CB = f"{ADMIN_CB_PREFIX}monitoring_menu"
ASSETS_CB = f"{ADMIN_CB_PREFIX}tmc_menu"
BROADCASTS_CB = f"{ADMIN_CB_PREFIX}broadcast_menu"
LEGACY_CB = f"{ADMIN_CB_PREFIX}legacy_root"

# Legacy sub-menu callbacks (совместимость с menu.py)
LEGACY_TMC_CB = f"{ADMIN_CB_PREFIX}tmc"
LEGACY_JOURNAL_CB = f"{ADMIN_CB_PREFIX}journal"
LEGACY_INGEST_CB = f"{ADMIN_CB_PREFIX}ingest"
LEGACY_SETTINGS_CB = f"{ADMIN_CB_PREFIX}settings"
LEGACY_MONITOR_CB = f"{ADMIN_CB_PREFIX}monitor"


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
            [
                InlineKeyboardButton(
                    text="🧩 Legacy / сервис",
                    callback_data=LEGACY_CB,
                ),
            ],
        ]
    )


def build_legacy_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура Legacy-разделов: ТМЦ, журнал смены, импорт CSV, настройки, мониторинг."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="⚙️ ТМЦ", callback_data=LEGACY_TMC_CB)],
            [InlineKeyboardButton(text="📋 Журнал смены", callback_data=LEGACY_JOURNAL_CB)],
            [InlineKeyboardButton(text="📥 Импорт CSV", callback_data=LEGACY_INGEST_CB)],
            [InlineKeyboardButton(text="⚙️ Настройки", callback_data=LEGACY_SETTINGS_CB)],
            [InlineKeyboardButton(text="📈 Мониторинг", callback_data=LEGACY_MONITOR_CB)],
        ]
    )
