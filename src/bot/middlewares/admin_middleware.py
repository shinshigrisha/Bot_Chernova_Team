from __future__ import annotations

from typing import Any, Awaitable, Callable, Dict

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, Update

from src.config import get_settings


Handler = Callable[[Update, Dict[str, Any]], Awaitable[Any]]


class AdminOnlyMiddleware(BaseMiddleware):
    """Разрешает доступ к админ-маршрутам только пользователям из ADMIN_IDS.

    Применяется к update-уровню и отфильтровывает:
    - сообщения с командой /admin;
    - callback_query, где data начинается с 'admin:'.
    """

    def __init__(self) -> None:
        self._settings = get_settings()

    async def __call__(self, handler: Handler, event: Update, data: Dict[str, Any]) -> Any:
        message: Message | None = None
        callback: CallbackQuery | None = None

        if event.message:
            message = event.message
        elif event.callback_query:
            callback = event.callback_query

        # Ничего админского — просто пропускаем.
        if message is None and callback is None:
            return await handler(event, data)

        tg_user_id = 0
        if message and message.from_user:
            tg_user_id = message.from_user.id
        if callback and callback.from_user:
            tg_user_id = callback.from_user.id

        is_admin_command = bool(
            message
            and message.text
            and message.text.strip().startswith("/admin")
        )
        is_admin_callback = bool(
            callback
            and callback.data
            and callback.data.startswith("admin:")
        )

        if not (is_admin_command or is_admin_callback):
            return await handler(event, data)

        if tg_user_id not in self._settings.admin_ids:
            # Уведомляем пользователя и блокируем дальнейшую обработку.
            if message:
                await message.answer("У вас нет доступа к админ-панели.")
            elif callback and callback.message:
                await callback.message.answer("У вас нет доступа к админ-панели.")
                await callback.answer()
            return None

        return await handler(event, data)

