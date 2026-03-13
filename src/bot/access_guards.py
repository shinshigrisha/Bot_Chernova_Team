"""Access / Role / Status Layer: стандартные сообщения и guard-функции.

Все проверки прав и статуса выполняются через AccessService.
Ответы «нет доступа» / «только для админов» централизованы здесь.
Использовать в хендлерах вместо ручных проверок и произвольных формулировок.
"""

from __future__ import annotations

from aiogram.types import CallbackQuery, Message

from src.core.services.access_service import AccessService

# Единые формулировки для ответов пользователю (Access / Role / Status Layer)
MSG_ADMIN_DENIED = "Доступ к админ-панели запрещён."
MSG_SERVICE_UNAVAILABLE = "Сервис временно недоступен. Попробуйте позже."
MSG_AI_ACCESS_DENIED = (
    "Для доступа к AI-куратору нужна одобренная регистрация. Нажмите /start."
)


async def require_admin_for_message(
    message: Message,
    access_service: AccessService,
) -> bool:
    """Проверить доступ к админ-панели для сообщения.

    При отсутствии доступа отправляет message.answer(MSG_ADMIN_DENIED).
    Returns:
        True — доступ есть, можно продолжать; False — доступ запрещён, обработку прекратить.
    """
    tg_user_id = message.from_user.id if message.from_user else 0
    if not await access_service.can_access_admin(tg_user_id):
        await message.answer(MSG_ADMIN_DENIED)
        return False
    return True


async def require_admin_for_callback(
    callback: CallbackQuery,
    access_service: AccessService,
    *,
    show_alert: bool = True,
) -> bool:
    """Проверить доступ к админ-панели для callback_query.

    При отсутствии доступа вызывает callback.answer(MSG_ADMIN_DENIED, show_alert=...).
    Returns:
        True — доступ есть; False — доступ запрещён, обработку прекратить.
    """
    tg_user_id = callback.from_user.id if callback.from_user else 0
    if not await access_service.can_access_admin(tg_user_id):
        await callback.answer(MSG_ADMIN_DENIED, show_alert=show_alert)
        return False
    return True
