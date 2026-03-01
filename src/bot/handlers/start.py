"""Start and user greeting."""
from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message

from src.config import get_settings
from src.infra.db.enums import UserRole
from src.infra.db.repositories.users import UserRepository
from src.infra.db.session import async_session_factory

router = Router(name="start")


@router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    settings = get_settings()
    tg_user_id = message.from_user.id if message.from_user else 0
    display_name = message.from_user.full_name if message.from_user else None
    role = UserRole.ADMIN if tg_user_id in settings.admin_ids else UserRole.VIEWER
    async with async_session_factory() as session:
        repo = UserRepository(session)
        user = await repo.get_or_create(tg_user_id, role=role, display_name=display_name)
        await session.commit()
        role_label = user.role.value
    await message.answer(
        f"Привет! Ты в боте Delivery Assistant.\nТвоя роль: **{role_label}**.",
        parse_mode="Markdown",
    )
