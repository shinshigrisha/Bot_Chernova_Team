"""Admin menu and entry point."""
from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from src.config import get_settings
from src.infra.db.enums import UserRole
from src.infra.db.repositories.users import UserRepository
from src.infra.db.session import async_session_factory

router = Router(name="admin_menu")

ADMIN_CB_PREFIX = "admin:"


def _admin_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="ТМЦ", callback_data=f"{ADMIN_CB_PREFIX}tmc")],
        [InlineKeyboardButton(text="Журнал смены", callback_data=f"{ADMIN_CB_PREFIX}journal")],
        [InlineKeyboardButton(text="Импорт CSV", callback_data=f"{ADMIN_CB_PREFIX}ingest")],
        [InlineKeyboardButton(text="Настройки", callback_data=f"{ADMIN_CB_PREFIX}settings")],
        [InlineKeyboardButton(text="Мониторинг", callback_data=f"{ADMIN_CB_PREFIX}monitor")],
    ])


async def _can_admin(tg_user_id: int) -> bool:
    settings = get_settings()
    if tg_user_id in settings.admin_ids:
        return True
    async with async_session_factory() as session:
        repo = UserRepository(session)
        user = await repo.get_by_tg_id(tg_user_id)
        await session.commit()
        if user and user.role in (UserRole.ADMIN, UserRole.LEAD, UserRole.CURATOR):
            return True
    return False


@router.message(Command("admin"))
async def cmd_admin(message: Message) -> None:
    tg_user_id = message.from_user.id if message.from_user else 0
    if not await _can_admin(tg_user_id):
        await message.answer("Доступ запрещён.")
        return
    await message.answer("Админ-панель:", reply_markup=_admin_keyboard())


@router.callback_query(F.data == f"{ADMIN_CB_PREFIX}settings")
async def cb_settings(callback: CallbackQuery) -> None:
    await callback.answer("Раздел в разработке.")

@router.callback_query(F.data == f"{ADMIN_CB_PREFIX}monitor")
async def cb_monitor(callback: CallbackQuery) -> None:
    await callback.answer("Раздел в разработке.")
