from __future__ import annotations

"""
Seed FAQ from canonical data/ai/faq_seed.jsonl into faq_ai v2.

- Supports: question, answer, category, tag, keywords, is_active.
- tag: taken from "tag" or fallback "intent" (canonical format).
- risk_level / when_to_escalate: present in JSONL are kept in source model only;
  not stored in DB (no columns yet); extension point for future schema.
- Idempotent: upsert by question (existing rows updated, new rows inserted).
"""

import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Load .env before get_settings()
try:
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env")
except ImportError:
    pass

# When running on host (not in Docker): use localhost instead of postgres
_db_url = os.environ.get("DATABASE_URL", "")
if os.environ.get("SEED_DATABASE_URL"):
    os.environ["DATABASE_URL"] = os.environ["SEED_DATABASE_URL"]
elif _db_url and "@postgres" in _db_url:
    os.environ["DATABASE_URL"] = _db_url.replace("@postgres:", "@localhost:").replace("@postgres/", "@localhost/")

from src.config import get_settings
from src.infra.db.repositories.faq_repo import FAQRepository
from src.infra.db.session import async_session_factory

SEED_PATH = ROOT / "data" / "ai" / "faq_seed.jsonl"


def _normalize_optional(value: Any) -> str | None:
    if value is None:
        return None
    normalized = str(value).strip()
    return normalized or None


def _normalize_keywords(raw_keywords: Any) -> list[str]:
    if not raw_keywords:
        return []
    if isinstance(raw_keywords, str):
        raw_keywords = [raw_keywords]
    return [str(keyword).strip() for keyword in raw_keywords if str(keyword).strip()]


def _normalize_seed_item(item: dict[str, Any]) -> dict[str, Any]:
    """Normalize one JSONL row to faq_ai v2 fields. Backward-safe for legacy q/a/tags.
    Source may include risk_level, when_to_escalate — not persisted (extension point)."""
    question = str(item.get("question") or item.get("q") or "").strip()
    answer = str(item.get("answer") or item.get("a") or "").strip()
    category = _normalize_optional(item.get("category"))
    tag = _normalize_optional(item.get("tag") or item.get("intent"))
    keywords = _normalize_keywords(item.get("keywords"))

    legacy_tags = _normalize_keywords(item.get("tags"))
    if not tag and legacy_tags:
        tag = legacy_tags[0]
    if not keywords and legacy_tags:
        keywords = legacy_tags

    return {
        "question": question,
        "answer": answer,
        "category": category,
        "tag": tag,
        "keywords": keywords,
        "is_active": bool(item.get("is_active", True)),
    }


async def main() -> None:
    settings = get_settings()
    if not settings.database_url:
        raise RuntimeError("DATABASE_URL is not set")

    if not SEED_PATH.exists():
        raise RuntimeError(f"Seed file not found: {SEED_PATH}")

    repo = FAQRepository()
    created = 0
    updated = 0
    async with async_session_factory() as session:
        for line in SEED_PATH.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            item = _normalize_seed_item(json.loads(line))
            if not item["question"] or not item["answer"]:
                continue
            _, was_created = await repo.upsert_faq(
                session=session,
                question=item["question"],
                answer=item["answer"],
                category=item["category"],
                tag=item["tag"],
                keywords=item["keywords"],
                is_active=item["is_active"],
            )
            if was_created:
                created += 1
            else:
                updated += 1
        await session.commit()

    print(f"Seeded FAQ items: created={created}, updated={updated}, total={created + updated}")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        err_msg = str(e).lower()
        if "connection" in err_msg or "closed" in err_msg or "does not exist" in err_msg:
            print("Database connection failed.", file=sys.stderr)
            print("Hint: ensure PostgreSQL is running and DATABASE_URL is correct (use localhost when not in Docker).", file=sys.stderr)
        raise
