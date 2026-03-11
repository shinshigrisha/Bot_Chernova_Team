from __future__ import annotations

import asyncio
from collections import Counter
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.config import get_settings
from src.core.services.ai.ai_courier_service import AICourierService
from src.core.services.ai.provider_router import ProviderRouter
from src.core.services.ai.providers.deepseek_provider import DeepSeekProvider
from src.core.services.ai.providers.groq_provider import GroqProvider
from src.core.services.ai.providers.openai_provider import OpenAIProvider
from src.infra.db.repositories.faq_repo import FAQRepository
from src.infra.db.session import async_session_factory

GOLDEN_PATH = Path("data/ai/golden_cases.jsonl")


def _build_router_or_none() -> ProviderRouter | None:
    settings = get_settings()
    if not settings.ai_enabled:
        return None
    return ProviderRouter([GroqProvider(), DeepSeekProvider(), OpenAIProvider()])


async def main() -> None:
    if not GOLDEN_PATH.exists():
        raise RuntimeError(f"Golden file not found: {GOLDEN_PATH}")

    settings = get_settings()
    router = _build_router_or_none()
    enabled_providers = (
        sorted(router.providers.keys()) if router is not None else []
    )
    print(f"AI_ENABLED={str(settings.ai_enabled).lower()}")
    print(
        f"ENABLED_PROVIDERS={', '.join(enabled_providers) if enabled_providers else 'none'}"
    )

    ai = AICourierService(session_factory=async_session_factory, router=router)
    faq_repo = FAQRepository()
    try:
        async with async_session_factory() as session:
            faq_count = await faq_repo.count(session=session)
        print(f"FAQ_COUNT={faq_count}")
        if faq_count == 0:
            raise RuntimeError("Smoke failed: FAQ table is empty")

        answered = 0
        matched = 0
        total = 0
        failed = 0
        ml_case_matched_count = 0
        route_counts: Counter[str] = Counter()
        for line in GOLDEN_PATH.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            total += 1
            try:
                case = json.loads(line)
            except json.JSONDecodeError as e:
                print(f"[FAIL] Invalid JSON: {e}")
                failed += 1
                continue
            try:
                res = await ai.get_answer(user_id=1, text=case["input"])
            except Exception as e:
                print(f"[PROVIDER_FAIL] {case.get('input', '')[:60]!r}: {e}")
                failed += 1
                continue
            route_counts[res.route] += 1
            text = (res.text or "").lower()
            if text:
                answered += 1

            must_any = case.get("must_contain_any", [])
            must_not = case.get("must_not_contain_any", [])

            good_any = (not must_any) or any(x.lower() in text for x in must_any)
            good_not = all(x.lower() not in text for x in must_not)

            if good_any and good_not:
                matched += 1
            if res.debug.get("case_id"):
                ml_case_matched_count += 1

            status = "OK" if (good_any and good_not) else "CHECK"
            ml_case = res.debug.get("case_id") or "none"
            ml_sim = res.debug.get("case_similarity")
            print(f"[{status}] {case['input']}")
            print("ROUTE:", res.route, "INTENT:", res.intent, "CONF:", res.confidence)
            print("ML_CASE_MATCHED=" + str(ml_case) + (f" (sim={ml_sim})" if ml_sim is not None else ""))
            print("ANSWER:", res.text)
            print()

        print(f"ANSWERED={answered}/{total}")
        print(f"GOLDEN_MATCH={matched}/{total}")
        if failed:
            print(f"FAILED_CASES={failed}")
        print(
            "ROUTE_COUNTS="
            + ", ".join(
                f"{route}:{count}" for route, count in sorted(route_counts.items())
            )
        )
        must_match_count = route_counts.get("must_match", 0)
        case_engine_count = route_counts.get("case_engine", 0)
        faq_match_count = route_counts.get("faq", 0)
        semantic_match_count = route_counts.get("semantic_faq", 0)
        case_match_count = route_counts.get("semantic_case", 0)
        llm_reason_count = route_counts.get("llm_reason", 0)
        fallback_count = route_counts.get("fallback", 0)
        strict_routes = (
            must_match_count + case_engine_count + faq_match_count
            + semantic_match_count + case_match_count
        )

        print(f"MUST_MATCH_COUNT={must_match_count}/{total}")
        print(f"FAQ_MATCH_COUNT={faq_match_count}/{total}")
        print(f"SEMANTIC_MATCH_COUNT={semantic_match_count}/{total}")
        print(f"CASE_MATCH_COUNT={case_match_count}/{total}")
        print(f"FALLBACK_COUNT={fallback_count}/{total}")
        print(f"STRICT_ROUTE_SHARE={strict_routes}/{total}")
        print(f"CASE_ENGINE_COUNT={case_engine_count}/{total}")
        print(f"LLM_REASON_COUNT={llm_reason_count}/{total}")
        print(f"ML_CASE_MATCHED_COUNT={ml_case_matched_count}/{total}")

        if answered == 0 and total > 0:
            raise RuntimeError("Smoke failed: AI returned no answers")
    finally:
        if router is not None:
            await router.close()


if __name__ == "__main__":
    asyncio.run(main())
