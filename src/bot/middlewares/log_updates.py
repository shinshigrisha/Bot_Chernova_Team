"""Middleware: логирование входящих обновлений для отладки (видно, что бот получает апдейты)."""
import logging

from aiogram import BaseMiddleware
from aiogram.types import Update

logger = logging.getLogger(__name__)


class LogUpdatesMiddleware(BaseMiddleware):
    async def __call__(self, handler, event: Update, data: dict):
        update_id = event.update_id
        chat_id = None
        if event.message:
            chat_id = event.message.chat.id
        elif event.callback_query:
            chat_id = event.callback_query.message.chat.id if event.callback_query.message else None
        logger.info("update received update_id=%s chat_id=%s", update_id, chat_id)
        return await handler(event, data)
