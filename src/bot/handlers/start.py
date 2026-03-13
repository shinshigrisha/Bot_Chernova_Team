"""Start and user greeting — canonical status/role flow.

Strict status/role gating:
- guest (no record or status=guest) -> registration entry screen
- pending -> waiting screen
- rejected -> rejected + reapply
- blocked -> blocked screen
- approved + admin/lead -> admin root menu
- approved + courier -> courier root menu
- approved + curator/viewer -> curator root menu

Bootstrap: only for ADMIN_IDS when user does not exist; creates APPROVED+ADMIN.
Never auto-creates unknown users as courier (no bypass of status model).
"""
from __future__ import annotations

import logging

from aiogram import F, Router
from aiogram.filters import CommandStart
from aiogram.types import CallbackQuery, Message

from src.bot.menu_renderer import show_entrypoint_menu
from src.config import get_settings
from src.core.services.access_service import AccessService
from src.core.services.users import UserService
from src.infra.db.enums import UserRole, UserStatus

router = Router(name="start")
logger = logging.getLogger(__name__)


def _is_guest(principal) -> bool:
    """User has no record in DB (canonical guest)."""
    return principal.role is None and principal.status is None


@router.message(CommandStart())
async def cmd_start(
    message: Message,
    user_service: UserService,
    access_service: AccessService,
) -> None:
    settings = get_settings()
    tg_user_id = message.from_user.id if message.from_user else 0
    display_name = message.from_user.full_name if message.from_user else None

    logger.info("cmd_start_enter", extra={"tg_user_id": tg_user_id})

    try:
        principal = await access_service.get_principal(tg_user_id)
    except Exception:
        logger.exception("cmd_start_get_principal_fail", extra={"tg_user_id": tg_user_id})
        await message.answer("Сервис временно недоступен. Попробуйте позже.")
        return

    # Safe bootstrap: only ADMIN_IDS, only when user has no record; never creates courier/curator
    if _is_guest(principal) and tg_user_id in settings.admin_ids:
        try:
            await user_service.get_or_create(
                tg_user_id,
                role=UserRole.ADMIN,
                display_name=display_name,
                status=UserStatus.APPROVED,
            )
            principal = await access_service.get_principal(tg_user_id)
        except Exception:
            logger.exception(
                "cmd_start_bootstrap_admin_fail",
                extra={"tg_user_id": tg_user_id},
            )
            await message.answer("Сервис временно недоступен. Попробуйте позже.")
            return

    logger.info(
        "cmd_start_ok",
        extra={
            "tg_user_id": tg_user_id,
            "status": principal.status.value if principal.status else "guest",
            "role": principal.role.value if principal.role else None,
        },
    )
    await show_entrypoint_menu(message, principal)


@router.callback_query(F.data == "pending:refresh")
async def pending_refresh(
    callback: CallbackQuery,
    access_service: AccessService,
) -> None:
    """Обновить экран по статусу (для пользователя в PENDING — показать тот же или новый экран)."""
    tg_user_id = callback.from_user.id if callback.from_user else 0
    try:
        principal = await access_service.get_principal(tg_user_id)
    except Exception:
        await callback.answer("Сервис временно недоступен.")
        return
    await show_entrypoint_menu(callback.message, principal)
    await callback.answer()
