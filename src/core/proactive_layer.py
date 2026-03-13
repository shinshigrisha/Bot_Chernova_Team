"""Проактивный слой AI-куратора: подписки на события и авто-действия.

- faq_added → пересборка индекса эмбеддингов FAQ (в фоне)
- verification.pending → уведомление в Telegram получателям из Access Layer (get_verification_alert_recipient_ids)
- high_risk_detected / delivery_risk_eval — обрабатываются в API automation
- similar_case_shown — эмитируется в ai_chat при ответе по semantic_case
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from sqlalchemy.ext.asyncio import async_sessionmaker

from src.config import get_settings
from src.core.events import AutomationEvent
from src.core.services.access_service import AccessService
from src.core.services.ai.faq_embeddings_rebuild import rebuild_faq_embeddings_async

logger = logging.getLogger(__name__)

# Callback data для алерта верификации (совпадают с admin_handlers)
_ADMIN_VERIFICATION_APPROVE = "admin:verification:approve:"
_ADMIN_VERIFICATION_REJECT = "admin:verification:reject:"
_ADMIN_VERIFICATION_BLOCK = "admin:verification:block:"
_ADMIN_VERIFICATION_MENU = "admin:verification_menu"


def register_proactive_handlers(
    event_bus: Any,
    session_factory: async_sessionmaker,
    bot: Any = None,
    access_service: AccessService | None = None,
) -> None:
    """Подписать проактивные обработчики на event_bus.

    Вызывать после создания event_bus и до старта polling.
    bot: опционально, для отправки уведомлений о новой заявке.
    access_service: при наличии — список получателей верификационных алертов из слоя Access (get_verification_alert_recipient_ids).
    """

    async def _on_faq_added(event: str, payload: dict[str, Any]) -> None:
        if event != AutomationEvent.FAQ_ADDED:
            return
        logger.info("proactive_faq_rebuild_triggered", faq_id=payload.get("faq_id"))
        try:
            result = await rebuild_faq_embeddings_async(
                session_factory=session_factory,
                embeddings_service=None,
            )
            if result.get("error"):
                logger.warning(
                    "proactive_faq_rebuild_finished_with_error",
                    error=result.get("error"),
                )
            else:
                logger.info(
                    "proactive_faq_rebuild_finished",
                    updated=result.get("updated", 0),
                    total=result.get("total", 0),
                )
        except Exception as e:
            logger.exception("proactive_faq_rebuild_failed", error=str(e))

    async def _on_verification_pending(event: str, payload: dict[str, Any]) -> None:
        if event != AutomationEvent.VERIFICATION_PENDING or not bot:
            return
        if access_service is not None:
            recipient_ids = access_service.get_verification_alert_recipient_ids()
        else:
            recipient_ids = get_settings().admin_ids
        if not recipient_ids:
            return
        tg_user_id = payload.get("tg_user_id")
        first = payload.get("first_name", "")
        last = payload.get("last_name", "")
        role = payload.get("role", "")
        tt = payload.get("tt_number", "")
        phone = payload.get("phone", "")
        text = (
            "🆕 Новая заявка на регистрацию\n\n"
            f"tg_user_id: {tg_user_id}\n"
            f"Роль: {role}\n"
            f"Имя: {first}\n"
            f"Фамилия: {last}\n"
            f"ТТ: {tt}\n"
            f"Телефон: {phone}"
        )
        reply_markup = None
        if tg_user_id is not None:
            from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
            reply_markup = InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        InlineKeyboardButton(
                            text="✅ Одобрить",
                            callback_data=f"{_ADMIN_VERIFICATION_APPROVE}{tg_user_id}",
                        ),
                        InlineKeyboardButton(
                            text="❌ Отклонить",
                            callback_data=f"{_ADMIN_VERIFICATION_REJECT}{tg_user_id}",
                        ),
                    ],
                    [
                        InlineKeyboardButton(
                            text="⛔ Заблокировать",
                            callback_data=f"{_ADMIN_VERIFICATION_BLOCK}{tg_user_id}",
                        ),
                        InlineKeyboardButton(
                            text="📄 Открыть карточку",
                            callback_data=_ADMIN_VERIFICATION_MENU,
                        ),
                    ],
                ]
            )
        for admin_id in recipient_ids:
            try:
                await bot.send_message(
                    chat_id=admin_id,
                    text=text,
                    reply_markup=reply_markup,
                )
            except Exception as e:
                logger.warning(
                    "verification_notify_admin_failed",
                    admin_id=admin_id,
                    error=str(e),
                )

    def _handler(event: str, payload: dict[str, Any]) -> Any:
        if event == AutomationEvent.FAQ_ADDED:
            asyncio.create_task(_on_faq_added(event, payload))
        elif event == AutomationEvent.VERIFICATION_PENDING and bot:
            asyncio.create_task(_on_verification_pending(event, payload))

    event_bus.subscribe(_handler)
