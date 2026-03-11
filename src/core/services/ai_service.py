"""Legacy compatibility wrapper for AI assistant service."""
from __future__ import annotations

import logging
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import async_sessionmaker

from src.core.services.ai.provider_router import ProviderRouter
from src.infra.db.repositories.faq_repo import FAQRepository

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "Ты — AI-помощник курьерской службы доставки. "
    "Отвечай кратко, по делу, на русском языке. "
    "Используй предоставленный контекст из базы знаний, если он есть."
)

FAQ_SCORE_THRESHOLD = 0.8


@dataclass
class AIResponse:
    text: str
    source: str  # "faq" | "llm"
    provider: str = ""


class AICourierService:
    def __init__(
        self,
        session_factory: async_sessionmaker,
        router: ProviderRouter,
    ) -> None:
        self._session_factory = session_factory
        self._router = router

    async def get_answer(self, user_id: int, text: str) -> AIResponse:
        async with self._session_factory() as session:
            faq_repo = FAQRepository(session)
            faq_hits = await faq_repo.search_hybrid(query=text, limit=3)

        if faq_hits and faq_hits[0]["score"] >= FAQ_SCORE_THRESHOLD:
            best = faq_hits[0]
            return AIResponse(
                text=best["answer"],
                source="faq",
            )

        context_parts: list[str] = []
        for hit in faq_hits:
            context_parts.append(f"Q: {hit['question']}\nA: {hit['answer']}")

        context_block = ""
        if context_parts:
            context_block = (
                "\n\nКонтекст из базы знаний:\n" + "\n---\n".join(context_parts)
            )

        messages = [
            {"role": "system", "content": SYSTEM_PROMPT + context_block},
            {"role": "user", "content": text},
        ]

        try:
            llm_resp = await self._router.complete(messages)
            return AIResponse(
                text=llm_resp.text,
                source="llm",
                provider=llm_resp.provider,
            )
        except Exception:
            logger.exception("LLM call failed for user %s", user_id)
            if faq_hits:
                return AIResponse(
                    text=faq_hits[0]["answer"],
                    source="faq",
                )
            return AIResponse(
                text="Не удалось получить ответ. Попробуйте позже или обратитесь к координатору.",
                source="error",
            )
