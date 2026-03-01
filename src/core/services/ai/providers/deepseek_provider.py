from __future__ import annotations

import os

from openai import AsyncOpenAI

from src.core.services.ai.providers.base import BaseProvider, ProviderResponse


class DeepSeekProvider(BaseProvider):
    name = "deepseek"

    def __init__(self) -> None:
        api_key = os.getenv("DEEPSEEK_API_KEY", "").strip()
        self.enabled = bool(api_key)
        self._model = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
        base_url = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com").rstrip("/")
        self._client = (
            AsyncOpenAI(api_key=api_key, base_url=f"{base_url}/v1")
            if self.enabled
            else None
        )

    async def complete(
        self,
        messages: list[dict[str, str]],
        *,
        temperature: float = 0.3,
        max_tokens: int = 1024,
    ) -> ProviderResponse:
        if not self.enabled or self._client is None:
            raise RuntimeError("DeepSeek provider is disabled")

        resp = await self._client.chat.completions.create(
            model=self._model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        text = resp.choices[0].message.content or ""
        usage_tokens = resp.usage.total_tokens if resp.usage else 0
        return ProviderResponse(
            text=text,
            provider=self.name,
            model=self._model,
            usage_tokens=usage_tokens,
        )

    async def close(self) -> None:
        if self._client is not None:
            await self._client.close()
