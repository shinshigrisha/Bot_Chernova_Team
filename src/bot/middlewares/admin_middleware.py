from __future__ import annotations

from typing import Any, Awaitable, Callable, Dict

from aiogram import BaseMiddleware, Dispatcher
from aiogram.types import CallbackQuery, Message, Update

from src.bot.access_guards import MSG_ADMIN_DENIED
from src.config import get_settings

Handler = Callable[[Update, Dict[str, Any]], Awaitable[Any]]


class AdminOnlyMiddleware(BaseMiddleware):
    """Разрешает доступ к админ-маршрутам только пользователям с правами админа.

    Проверка: при наличии AccessService в диспетчере используется
    access_service.can_access_admin(tg_user_id); иначе fallback на ADMIN_IDS.
    Сообщение об отказе централизовано в access_guards.MSG_ADMIN_DENIED.

    Применяется к update-уровню:
    - сообщения с командой /admin;
    - callback_query, где data начинается с 'admin:'.
    """

    def __init__(self, dp: Dispatcher | None = None) -> None:
        self._settings = get_settings()
        self._dp = dp

    async def __call__(self, handler: Handler, event: Update, data: Dict[str, Any]) -> Any:
        message: Message | None = None
        callback: CallbackQuery | None = None

        if event.message:
            message = event.message
        elif event.callback_query:
            callback = event.callback_query

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

        allowed = False
        if self._dp:
            access_service = self._dp.get("access_service")
            if access_service is not None:
                allowed = await access_service.can_access_admin(tg_user_id)
        if not allowed:
            allowed = tg_user_id in self._settings.admin_ids

        if not allowed:
            if message:
                await message.answer(MSG_ADMIN_DENIED)
            elif callback and callback.message:
                await callback.message.answer(MSG_ADMIN_DENIED)
                await callback.answer()
            return None

        return await handler(event, data)

