from __future__ import annotations

import asyncio
import os

from src.services.ai.provider_router import ProviderRouter


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

    router = ProviderRouter()
    text = await router.chat(
        messages=[
            {"role": "system", "content": "Answer in one short sentence."},
            {"role": "user", "content": "Say hello in Russian."},
        ],
        max_tokens=60,
    )
    if text:
        print("SMOKE: provider_router OK")
    else:
        print("SMOKE: provider_router returned empty response")


if __name__ == "__main__":
    asyncio.run(main())
