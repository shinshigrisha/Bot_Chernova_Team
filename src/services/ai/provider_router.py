from __future__ import annotations

import asyncio
import logging
import os
from typing import Any

from groq import AsyncGroq
from openai import AsyncOpenAI

logger = logging.getLogger(__name__)


class ProviderRouter:
    def __init__(self) -> None:
        self._openai_key = os.getenv("OPENAI_API_KEY", "").strip()
        self._deepseek_key = os.getenv("DEEPSEEK_API_KEY", "").strip()
        self._groq_key = os.getenv("GROQ_API_KEY", "").strip()

        self._default_provider = os.getenv("AI_PROVIDER_DEFAULT", "groq").strip().lower()
        self._default_model = os.getenv("AI_MODEL_DEFAULT", "llama-3.1-8b-instant").strip()
        self._timeout_s = float(os.getenv("AI_PROVIDER_TIMEOUT_SEC", "20"))

        self._openai = AsyncOpenAI(api_key=self._openai_key) if self._openai_key else None
        self._deepseek = (
            AsyncOpenAI(
                api_key=self._deepseek_key,
                base_url=f"{os.getenv('DEEPSEEK_BASE_URL', 'https://api.deepseek.com').rstrip('/')}/v1",
            )
            if self._deepseek_key
            else None
        )
        self._groq = AsyncGroq(api_key=self._groq_key) if self._groq_key else None

    async def chat(
        self,
        messages: list[dict[str, Any]],
        model: str | None = None,
        temperature: float = 0.2,
        max_tokens: int = 500,
    ) -> str:
        model_name = model or self._default_model
        chain = self._provider_chain()
        last_exc: Exception | None = None

        for provider_name in chain:
            try:
                text = await self._call_provider(
                    provider_name=provider_name,
                    messages=messages,
                    model=model_name,
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
                logger.info("ai_provider_used=%s", provider_name)
                return text
            except Exception as exc:
                logger.warning("ai_provider_failed=%s error=%s", provider_name, exc)
                last_exc = exc

        raise RuntimeError("No available AI provider in fallback chain") from last_exc

    def _provider_chain(self) -> list[str]:
        # Base preference requested: groq -> openai -> deepseek
        base = ["groq", "openai", "deepseek"]
        if self._default_provider in base:
            base.remove(self._default_provider)
            base.insert(0, self._default_provider)
        return base

    async def _call_provider(
        self,
        provider_name: str,
        messages: list[dict[str, Any]],
        model: str,
        temperature: float,
        max_tokens: int,
    ) -> str:
        if provider_name == "groq":
            if self._groq is None:
                raise RuntimeError("Groq API key is not configured")
            coro = self._groq.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            resp = await asyncio.wait_for(coro, timeout=self._timeout_s)
            return (resp.choices[0].message.content or "").strip()

        if provider_name == "openai":
            if self._openai is None:
                raise RuntimeError("OpenAI API key is not configured")
            coro = self._openai.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            resp = await asyncio.wait_for(coro, timeout=self._timeout_s)
            return (resp.choices[0].message.content or "").strip()

        if provider_name == "deepseek":
            if self._deepseek is None:
                raise RuntimeError("DeepSeek API key is not configured")
            coro = self._deepseek.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            resp = await asyncio.wait_for(coro, timeout=self._timeout_s)
            return (resp.choices[0].message.content or "").strip()

        raise RuntimeError(f"Unknown provider: {provider_name}")
