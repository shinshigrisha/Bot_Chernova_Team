from __future__ import annotations

from openai import AsyncOpenAI

from src.config import get_settings
from src.core.services.ai.providers.base import BaseProvider, ProviderResponse


class OpenAICompatibleProvider(BaseProvider):
    """OpenAI-compatible endpoint with canonical multi-model config.

    Uses OPENAI_API_KEY / OPENAI_BASE_URL and accepts a model override per call.
    """

    name = "openai_compatible"

    def __init__(self) -> None:
        settings = get_settings()
        api_key = settings.openai_api_key.strip()
        base_url = settings.openai_base_url.strip() or None

        self.enabled = bool(api_key)
        # Default model is the "default" capability; per-call overrides come from router.
        self._default_model = settings.ai_default_model
        self._client = (
            AsyncOpenAI(api_key=api_key, base_url=base_url) if self.enabled else None
        )

    async def complete(
        self,
        messages: list[dict[str, str]],
        *,
        temperature: float = 0.3,
        max_tokens: int = 1024,
        model: str | None = None,
    ) -> ProviderResponse:
        if not self.enabled or self._client is None:
            raise RuntimeError("OpenAI-compatible provider is disabled")

        model_name = model or self._default_model
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

