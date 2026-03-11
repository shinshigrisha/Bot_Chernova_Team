"""Smoke test for canonical ProviderRouter (core/services/ai)."""
from __future__ import annotations

import asyncio
import os

from src.core.services.ai.provider_router import ProviderRouter
from src.core.services.ai.providers.deepseek_provider import DeepSeekProvider
from src.core.services.ai.providers.groq_provider import GroqProvider
from src.core.services.ai.providers.openai_provider import OpenAIProvider


async def main() -> None:
    if not any(
        [
            os.getenv("GROQ_API_KEY"),
            os.getenv("OPENAI_API_KEY"),
            os.getenv("DEEPSEEK_API_KEY"),
        ]
    ):
        print("SMOKE: skipped (no provider keys configured)")
        return

    router = ProviderRouter(
        [
            GroqProvider(),
            DeepSeekProvider(),
            OpenAIProvider(),
        ]
    )
    try:
        response = await router.complete(
            [
                {"role": "system", "content": "Answer in one short sentence."},
                {"role": "user", "content": "Say hello in Russian."},
            ],
            mode="chat",
            max_tokens=60,
        )
        if response and response.text:
            print("SMOKE: provider_router OK")
        else:
            print("SMOKE: provider_router returned empty response")
    finally:
        await router.close()


if __name__ == "__main__":
    asyncio.run(main())
