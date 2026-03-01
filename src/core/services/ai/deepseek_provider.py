from __future__ import annotations

import httpx

from src.core.services.ai.base import BaseProvider, LLMResponse


class DeepSeekProvider(BaseProvider):
    name = "deepseek"
    default_model = "deepseek-chat"

    def __init__(self, api_key: str, *, model: str | None = None):
        self._api_key = api_key
        self._model = model or self.default_model
        self._client = httpx.AsyncClient(
            base_url="https://api.deepseek.com/v1",
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=30.0,
        )

    async def complete(
        self,
        messages: list[dict[str, str]],
        *,
        temperature: float = 0.3,
        max_tokens: int = 1024,
    ) -> LLMResponse:
        resp = await self._client.post(
            "/chat/completions",
            json={
                "model": self._model,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
            },
        )
        resp.raise_for_status()
        data = resp.json()
        usage = data.get("usage", {})
        return LLMResponse(
            text=data["choices"][0]["message"]["content"],
            provider=self.name,
            model=self._model,
            usage_tokens=usage.get("total_tokens", 0),
        )

    async def close(self) -> None:
        await self._client.aclose()
