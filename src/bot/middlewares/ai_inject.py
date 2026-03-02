from __future__ import annotations

from aiogram import Dispatcher
from aiogram.dispatcher.middlewares.base import BaseMiddleware


class InjectAIMiddleware(BaseMiddleware):
    def __init__(self, dp: Dispatcher) -> None:
        self._dp = dp

    async def __call__(self, handler, event, data):
        data["ai_service"] = self._dp.get("ai_service")
        data["faq_repo"] = self._dp.get("faq_repo")
        data["provider_router"] = self._dp.get("provider_router") or self._dp.get("ai_router")
        return await handler(event, data)
