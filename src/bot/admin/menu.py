"""Admin menu and entry point."""
from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from src.bot.keyboards.admin_main import (
    ADMIN_CB_PREFIX,
    ASSETS_CB,
    BROADCASTS_CB,
    CSV_ANALYSIS_CB,
    MONITORING_CB,
    POLL_GROUPS_CB,
    AI_CURATOR_CB,
    build_admin_main_keyboard,
)
from src.core.services.access_service import AccessService

router = Router(name="admin_menu")


def _legacy_admin_keyboard() -> InlineKeyboardMarkup:
    """Старое админ-меню (legacy), сохранено для совместимости."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="ТМЦ", callback_data=f"{ADMIN_CB_PREFIX}tmc")],
            [InlineKeyboardButton(text="Журнал смены", callback_data=f"{ADMIN_CB_PREFIX}journal")],
            [InlineKeyboardButton(text="Импорт CSV", callback_data=f"{ADMIN_CB_PREFIX}ingest")],
            [InlineKeyboardButton(text="Настройки", callback_data=f"{ADMIN_CB_PREFIX}settings")],
            [InlineKeyboardButton(text="Мониторинг", callback_data=f"{ADMIN_CB_PREFIX}monitor")],
        ]
    )


def _root_admin_keyboard() -> InlineKeyboardMarkup:
    """Комбинированное админ-меню: новые разделы + ссылка на legacy."""
    rows = build_admin_main_keyboard().inline_keyboard
    rows.append(
        [
            InlineKeyboardButton(
                text="🧩 Legacy разделы",
                callback_data=f"{ADMIN_CB_PREFIX}legacy_root",
            )
        ]
    )
    return InlineKeyboardMarkup(inline_keyboard=rows)


async def _can_admin(tg_user_id: int, access_service: AccessService) -> bool:
    return await access_service.can_access_admin(tg_user_id)


@router.message(Command("admin"))
async def cmd_admin(message: Message, access_service: AccessService) -> None:
    tg_user_id = message.from_user.id if message.from_user else 0
    if not await _can_admin(tg_user_id, access_service):
        await message.answer("Доступ запрещён.")
        return
    await message.answer("Админ-панель:", reply_markup=_root_admin_keyboard())


@router.callback_query(F.data == f"{ADMIN_CB_PREFIX}legacy_root")
async def cb_legacy_root(callback: CallbackQuery) -> None:
    await callback.message.edit_text(
        "Legacy разделы админ-панели:",
        reply_markup=_legacy_admin_keyboard(),
    )
    await callback.answer()


@router.callback_query(F.data == MONITORING_CB)
async def cb_monitoring_new(callback: CallbackQuery) -> None:
    await callback.answer("Раздел '📈 Мониторинг' в новом меню пока в разработке.")


@router.callback_query(F.data == CSV_ANALYSIS_CB)
async def cb_csv_analysis_new(callback: CallbackQuery) -> None:
    await callback.answer("Раздел '📊 Анализ CSV' в новом меню пока в разработке.")


@router.callback_query(F.data == ASSETS_CB)
async def cb_assets_new(callback: CallbackQuery) -> None:
    await callback.answer("Раздел '⚙️ Учет ТМЦ' в новом меню пока в разработке.")


@router.callback_query(F.data == POLL_GROUPS_CB)
async def cb_polls_groups_new(callback: CallbackQuery) -> None:
    await callback.answer("Раздел '📋 Опросы и группы' в новом меню пока в разработке.")


@router.callback_query(F.data == AI_CURATOR_CB)
async def cb_ai_curator_new(callback: CallbackQuery) -> None:
    await callback.answer("Раздел '🤖 AI куратор' в новом меню пока в разработке.")


@router.callback_query(F.data == BROADCASTS_CB)
async def cb_broadcasts_new(callback: CallbackQuery) -> None:
    await callback.answer("Раздел '📢 Рассылка' в новом меню пока в разработке.")
