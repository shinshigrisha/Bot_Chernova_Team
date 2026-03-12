from __future__ import annotations

from aiogram import Dispatcher
from aiogram.dispatcher.middlewares.base import BaseMiddleware


class InjectAIMiddleware(BaseMiddleware):
    def __init__(self, dp: Dispatcher) -> None:
        self._dp = dp

    async def __call__(self, handler, event, data):
        ai_router = self._dp.get("ai_router")
        data["ai_service"] = self._dp.get("ai_service")
        data["ai_facade"] = self._dp.get("ai_facade")
        data["faq_repo"] = self._dp.get("faq_repo")
        data["ai_router"] = ai_router
        data["provider_router"] = self._dp.get("provider_router") or ai_router
        data["event_bus"] = self._dp.get("event_bus")
        data["access_service"] = self._dp.get("access_service")
        data["user_service"] = self._dp.get("user_service")
        return await handler(event, data)
