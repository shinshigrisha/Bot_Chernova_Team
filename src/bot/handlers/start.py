"""Start and user greeting."""
from __future__ import annotations

import logging

from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message

from src.config import get_settings
from src.core.services.users import UserService
from src.infra.db.enums import UserRole

router = Router(name="start")
logger = logging.getLogger(__name__)


@router.message(CommandStart())
async def cmd_start(message: Message, user_service: UserService) -> None:
    settings = get_settings()
    tg_user_id = message.from_user.id if message.from_user else 0
    display_name = message.from_user.full_name if message.from_user else None
    role = UserRole.ADMIN if tg_user_id in settings.admin_ids else UserRole.COURIER

    logger.info("cmd_start_enter", extra={"tg_user_id": tg_user_id})

    try:
        profile = await user_service.get_or_create(
            tg_user_id, role=role, display_name=display_name
        )
    except Exception:
        logger.info("cmd_start_fail", extra={"tg_user_id": tg_user_id})
        logger.exception("cmd_start_fail", extra={"tg_user_id": tg_user_id})
        await message.answer("Сервис временно недоступен. Попробуйте позже.")
        return

    logger.info(
        "cmd_start_ok",
        extra={"tg_user_id": tg_user_id, "role": profile.role.value},
    )
    await message.answer(
        f"Привет! Ты в боте Delivery Assistant.\nТвоя роль: **{profile.role.value}**.",
        parse_mode="Markdown",
    )
