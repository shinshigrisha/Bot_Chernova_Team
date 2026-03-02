"""Middleware: логирование входящих обновлений для отладки (видно, что бот получает апдейты)."""
import json
import logging
import time

from aiogram import BaseMiddleware
from aiogram.types import Update

logger = logging.getLogger(__name__)

_LOG_PATH = "/Users/senya.miroshnichenko/apps/Bot_Chernova_Team/.cursor/debug-085abc.log"


def _dlog(msg: str, data: dict, hypothesis: str) -> None:
    try:
        with open(_LOG_PATH, "a") as f:
            f.write(json.dumps({
                "sessionId": "085abc",
                "timestamp": int(time.time() * 1000),
                "location": "log_updates.py",
                "message": msg,
                "data": data,
                "hypothesisId": hypothesis,
            }) + "\n")
    except Exception:
        pass


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
        # #region agent log
        _dlog("update_received", {"update_id": update_id, "chat_id": chat_id, "text": msg_text}, "H-A")
        # #endregion
        logger.info("update received update_id=%s chat_id=%s text=%r", update_id, chat_id, msg_text)
        result = await handler(event, data)
        # #region agent log
        _dlog("update_handled", {"update_id": update_id, "result": str(result)}, "H-A")
        # #endregion
        return result
