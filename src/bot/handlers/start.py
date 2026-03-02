"""Start and user greeting."""
import json
import logging
import time

from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message

from src.config import get_settings
from src.infra.db.enums import UserRole, coerce_user_role
from src.infra.db.repositories.users import UserRepository
from src.infra.db.session import async_session_factory

router = Router(name="start")
logger = logging.getLogger(__name__)

_LOG_PATH = "/Users/senya.miroshnichenko/apps/Bot_Chernova_Team/.cursor/debug-085abc.log"


def _dlog(msg: str, data: dict, hypothesis: str) -> None:
    try:
        with open(_LOG_PATH, "a") as f:
            f.write(json.dumps({
                "sessionId": "085abc",
                "timestamp": int(time.time() * 1000),
                "location": "start.py",
                "message": msg,
                "data": data,
                "hypothesisId": hypothesis,
            }) + "\n")
    except Exception:
        pass


@router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    settings = get_settings()
    tg_user_id = message.from_user.id if message.from_user else 0
    logger.info("cmd_start: tg_user_id=%s", tg_user_id)
    # #region agent log
    _dlog("cmd_start_enter", {"tg_user_id": tg_user_id}, "H-B")
    # #endregion
    display_name = message.from_user.full_name if message.from_user else None
    raw_role = UserRole.ADMIN if tg_user_id in settings.admin_ids else UserRole.VIEWER
    role = coerce_user_role(raw_role, default=UserRole.VIEWER)
    try:
        # #region agent log
        _dlog("cmd_start_before_db", {"tg_user_id": tg_user_id}, "H-B")
        # #endregion
        async with async_session_factory() as session:
            repo = UserRepository(session)
            user = await repo.get_or_create(tg_user_id, role=role, display_name=display_name)
            await session.commit()
            role_label = user.role.value
        # #region agent log
        _dlog("cmd_start_db_ok", {"tg_user_id": tg_user_id, "role": role_label}, "H-B")
        # #endregion
        await message.answer(
            f"Привет! Ты в боте Delivery Assistant.\nТвоя роль: **{role_label}**.",
            parse_mode="Markdown",
        )
        # #region agent log
        _dlog("cmd_start_answered", {"tg_user_id": tg_user_id}, "H-B")
        # #endregion
    except Exception as exc:
        # #region agent log
        _dlog("cmd_start_exception", {"tg_user_id": tg_user_id, "error": str(exc)}, "H-B")
        # #endregion
        logger.exception("cmd_start failed: tg_user_id=%s", tg_user_id)
        await message.answer(
            "Сервис временно недоступен. Проверьте, что миграции применены (alembic upgrade head), и попробуйте позже.",
        )
