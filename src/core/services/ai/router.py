from __future__ import annotations

import logging
from typing import Sequence

from src.core.services.ai.base import BaseProvider, LLMResponse

logger = logging.getLogger(__name__)


class ProviderRouter:
    """Routes LLM calls across providers with ordered fallback."""

    def __init__(self, providers: Sequence[BaseProvider]):
        if not providers:
            raise ValueError("At least one provider is required")
        self.providers: dict[str, BaseProvider] = {p.name: p for p in providers}
        self._order = [p.name for p in providers]

    async def complete(
        self,
        messages: list[dict[str, str]],
        *,
        temperature: float = 0.3,
        max_tokens: int = 1024,
        provider_name: str | None = None,
    ) -> LLMResponse:
        """
        Try providers in order (or a specific one) until success.
        Raises the last exception if all fail.
        """
        names = [provider_name] if provider_name else self._order
        last_exc: Exception | None = None

        for name in names:
            prov = self.providers.get(name)
            if prov is None:
                continue
            try:
                return await prov.complete(
                    messages, temperature=temperature, max_tokens=max_tokens
                )
            except Exception as exc:
                logger.warning("Provider %s failed: %s", name, exc)
                last_exc = exc

        raise RuntimeError(
            f"All providers failed: {names}"
        ) from last_exc

    async def close(self) -> None:
        for prov in self.providers.values():
            await prov.close()
