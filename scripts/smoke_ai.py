from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path

from src.core.services.ai.ai_courier_service import AICourierService
from src.core.services.ai.provider_router import ProviderRouter
from src.core.services.ai.providers.deepseek_provider import DeepSeekProvider
from src.core.services.ai.providers.groq_provider import GroqProvider
from src.core.services.ai.providers.openai_provider import OpenAIProvider
from src.infra.db.session import async_session_factory

GOLDEN_PATH = Path("data/ai/golden_cases.jsonl")


def _build_router_or_none() -> ProviderRouter | None:
    providers = [GroqProvider(), DeepSeekProvider(), OpenAIProvider()]
    enabled = [p for p in providers if p.enabled]
    if not enabled:
        return None
    return ProviderRouter(enabled)


async def main() -> None:
    if not os.getenv("DATABASE_URL"):
        raise RuntimeError("DATABASE_URL is not set")

    if not GOLDEN_PATH.exists():
        raise RuntimeError(f"Golden file not found: {GOLDEN_PATH}")

    router = _build_router_or_none()
    ai = AICourierService(session_factory=async_session_factory, router=router)

    ok = 0
    total = 0
    for line in GOLDEN_PATH.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        total += 1
        case = json.loads(line)
        res = await ai.get_answer(user_id=1, text=case["input"])
        text = (res.text or "").lower()

        must_any = case.get("must_contain_any", [])
        must_not = case.get("must_not_contain_any", [])

        good_any = (not must_any) or any(x.lower() in text for x in must_any)
        good_not = all(x.lower() not in text for x in must_not)

        if good_any and good_not:
            ok += 1
        else:
            print("FAIL:", case["input"])
            print("ROUTE:", res.route, "INTENT:", res.intent, "CONF:", res.confidence)
            print("ANSWER:", res.text)
            print()

    print(f"SMOKE: {ok}/{total} passed")
    if router is not None:
        await router.close()


if __name__ == "__main__":
    asyncio.run(main())
