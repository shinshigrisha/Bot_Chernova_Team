"""Print AI config (OpenAI-compatible endpoint + fast/reasoning/analytics/fallback) for smoke checklist.

Usage:
  python scripts/smoke_ai_config.py

Exit 0; output is parseable (KEY=value) for verification.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

try:
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env")
except ImportError:
    pass

from src.config import get_settings
from src.core.services.ai.model_config import get_model_config, AIModeCapability


def main() -> None:
    s = get_settings()
    # OpenAI-compatible
    base = (s.openai_base_url or "").strip()
    key_set = bool((s.openai_api_key or "").strip())
    print("OPENAI_BASE_URL=" + (base or "(empty)"))
    print("OPENAI_API_KEY_SET=" + str(key_set).lower())
    print("AI_DEFAULT_PROVIDER=" + (s.ai_default_provider or ""))
    print("AI_DEFAULT_MODEL=" + (s.ai_default_model or ""))

    for mode_name, mode_enum in [
        ("fast", AIModeCapability.FAST_CHAT),
        ("reasoning", AIModeCapability.REASONING),
        ("analytics", AIModeCapability.ANALYTICS),
        ("fallback", AIModeCapability.FALLBACK),
    ]:
        cfg = get_model_config(mode_enum)
        print(f"AI_{mode_name.upper()}_PROVIDER={cfg.provider}")
        print(f"AI_{mode_name.upper()}_MODEL={cfg.model}")

    print("EMBEDDING_PROVIDER=" + (s.embedding_provider or ""))
    print("EMBEDDING_MODEL=" + (s.embedding_model or ""))
    print("AI_ENABLED=" + str(s.ai_enabled).lower())
    print("AI_ENABLE_RAG=" + str(s.ai_enable_rag).lower())
    print("AI_ENABLE_SEMANTIC_SEARCH=" + str(s.ai_enable_semantic_search).lower())


if __name__ == "__main__":
    main()
    sys.exit(0)
