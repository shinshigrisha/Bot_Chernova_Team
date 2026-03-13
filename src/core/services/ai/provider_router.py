from __future__ import annotations

import logging
from typing import Iterable

from src.config import get_settings
from src.core.services.ai.model_config import ModelConfig, get_model_config
from src.core.services.ai.providers.base import BaseProvider, ProviderResponse

logger = logging.getLogger(__name__)


class NoProviderAvailable(RuntimeError):
    """Raised when no provider succeeded (all failed or none enabled)."""


class ProviderRouter:
    def __init__(self, providers: Iterable[BaseProvider]):
        enabled = [p for p in providers if getattr(p, "enabled", False)]
        self.providers: dict[str, BaseProvider] = {p.name: p for p in enabled}

    @staticmethod
    def _select_provider(config: ModelConfig, providers: dict[str, BaseProvider]) -> BaseProvider:
        provider = providers.get(config.provider)
        if provider is None:
            raise NoProviderAvailable(
                f"No provider configured for name={config.provider!r}"
            )
        if not getattr(provider, "enabled", False):
            raise NoProviderAvailable(
                f"Provider {config.provider!r} is disabled"
            )
        return provider

    async def complete(
        self,
        messages: list[dict[str, str]],
        *,
        mode: str = "chat",
        temperature: float = 0.3,
        max_tokens: int = 1024,
    ) -> ProviderResponse:
        """Route completion call to a provider based on canonical capability config.

        Mode is mapped to capability classes:
        - "chat"/"fast_chat" → fast_chat
        - "reason"/"reasoning" → reasoning
        - "analysis"/"analytics" → analytics
        - "fallback" → fallback
        - anything else → default
        """
        settings = get_settings()
        config = get_model_config(mode)
        try:
            provider = self._select_provider(config, self.providers)
        except NoProviderAvailable as exc:
            raise NoProviderAvailable(
                f"No available provider for mode={mode} (config provider={config.provider!r})"
            ) from exc

        # Enforce global token limit (budget protection)
        limit = max(0, settings.ai_max_output_tokens)
        effective_max_tokens = max_tokens
        if limit:
            effective_max_tokens = min(max_tokens, limit)

        return await provider.complete(
            messages,
            temperature=temperature,
            max_tokens=effective_max_tokens,
            model=config.model,
        )

    async def close(self) -> None:
        for provider in self.providers.values():
            await provider.close()
