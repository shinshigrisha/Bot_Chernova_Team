"""Middleware: логирование входящих обновлений."""
import logging

from aiogram import BaseMiddleware
from aiogram.types import Update

logger = logging.getLogger(__name__)


class LogUpdatesMiddleware(BaseMiddleware):
    async def __call__(self, handler, event: Update, data: dict):
        update_id = event.update_id
        chat_id = None
        msg_text = None
        if event.message:
            chat_id = event.message.chat.id
            msg_text = event.message.text
        elif event.callback_query:
            chat_id = event.callback_query.message.chat.id if event.callback_query.message else None
        logger.info("update received update_id=%s chat_id=%s text=%r", update_id, chat_id, msg_text)
        return await handler(event, data)
