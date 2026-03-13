from __future__ import annotations

from groq import AsyncGroq

from src.config import get_settings
from src.core.services.ai.providers.base import BaseProvider, ProviderResponse


class GroqProvider(BaseProvider):
    name = "groq"

    def __init__(self) -> None:
        settings = get_settings()
        api_key = settings.groq_api_key.strip()
        self.enabled = bool(api_key)
        self._model = settings.groq_model
        self._client = AsyncGroq(api_key=api_key) if self.enabled else None

    async def complete(
        self,
        messages: list[dict[str, str]],
        *,
        temperature: float = 0.3,
        max_tokens: int = 1024,
        model: str | None = None,
    ) -> ProviderResponse:
        if not self.enabled or self._client is None:
            raise RuntimeError("Groq provider is disabled")

        model_name = model or self._model
        resp = await self._client.chat.completions.create(
            model=model_name,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        text = resp.choices[0].message.content or ""
        usage_tokens = resp.usage.total_tokens if resp.usage else 0
        return ProviderResponse(
            text=text,
            provider=self.name,
            model=model_name,
            usage_tokens=usage_tokens,
        )

    async def close(self) -> None:
        if self._client is not None:
            await self._client.close()
