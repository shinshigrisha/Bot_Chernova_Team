"""Middleware: логирование входящих обновлений."""
import logging

from aiogram import BaseMiddleware
from aiogram.types import Update

logger = logging.getLogger(__name__)


class LogUpdatesMiddleware(BaseMiddleware):
    async def __call__(self, handler, event: Update, data: dict):
        update_id = event.update_id
        event_type = "unknown"
        from_user_id = None
        chat_id = None
        payload_len = 0

        if event.message:
            event_type = "message"
            from_user_id = event.message.from_user.id if event.message.from_user else None
            chat_id = event.message.chat.id
            payload_len = len((event.message.text or event.message.caption or ""))
        elif event.callback_query:
            event_type = "callback_query"
            from_user_id = (
                event.callback_query.from_user.id if event.callback_query.from_user else None
            )
            chat_id = event.callback_query.message.chat.id if event.callback_query.message else None
            payload_len = len(event.callback_query.data or "")

        logger.info(
            "update_received update_id=%s event_type=%s from_user_id=%s chat_id=%s payload_len=%s",
            update_id,
            event_type,
            from_user_id,
            chat_id,
            payload_len,
        )
        return await handler(event, data)
