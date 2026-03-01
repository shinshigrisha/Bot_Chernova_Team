from __future__ import annotations

from aiogram.dispatcher.middlewares.base import BaseMiddleware


class InjectAIMiddleware(BaseMiddleware):
    async def __call__(self, handler, event, data):
        bot = data.get("bot") or getattr(event, "bot", None)
        if bot is not None:
            data["ai_service"] = bot.get("ai_service")
            data["faq_repo"] = bot.get("faq_repo")
            data["provider_router"] = bot.get("provider_router") or bot.get("ai_router")
        return await handler(event, data)
