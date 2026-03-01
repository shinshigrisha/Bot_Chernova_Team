from __future__ import annotations

import logging
import os
from typing import Iterable

from src.core.services.ai.providers.base import BaseProvider, ProviderResponse

logger = logging.getLogger(__name__)


class ProviderRouter:
    def __init__(self, providers: Iterable[BaseProvider]):
        enabled = [p for p in providers if getattr(p, "enabled", False)]
        self.providers: dict[str, BaseProvider] = {p.name: p for p in enabled}

    @staticmethod
    def _ordered_names(mode: str) -> list[str]:
        if mode == "reason":
            raw = os.getenv("AI_PROVIDER_ORDER_REASON", "openai,deepseek,groq")
        else:
            raw = os.getenv("AI_PROVIDER_ORDER_CHAT", "groq,deepseek,openai")
        return [x.strip() for x in raw.split(",") if x.strip()]

    async def complete(
        self,
        messages: list[dict[str, str]],
        *,
        mode: str = "chat",
        temperature: float = 0.3,
        max_tokens: int = 1024,
    ) -> ProviderResponse:
        order = self._ordered_names(mode=mode)
        last_exc: Exception | None = None

        for name in order:
            provider = self.providers.get(name)
            if provider is None:
                continue
            try:
                return await provider.complete(
                    messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
            except Exception as exc:
                logger.warning("Provider %s failed in mode=%s: %s", name, mode, exc)
                last_exc = exc

        raise RuntimeError(f"No available provider for mode={mode}") from last_exc

    async def close(self) -> None:
        for provider in self.providers.values():
            await provider.close()
