from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path

from src.infra.db.repositories.faq_ai import FAQAIRepository
from src.infra.db.session import async_session_factory

SEED_PATH = Path("data/ai/faq_seed.jsonl")


async def main() -> None:
    if not os.getenv("DATABASE_URL"):
        raise RuntimeError("DATABASE_URL is not set")

    if not SEED_PATH.exists():
        raise RuntimeError(f"Seed file not found: {SEED_PATH}")

    inserted = 0
    async with async_session_factory() as session:
        repo = FAQAIRepository()
        for line in SEED_PATH.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            item = json.loads(line)
            await repo.upsert(
                session=session,
                faq_id=item["id"],
                q=item["q"],
                a=item["a"],
                tags=item.get("tags", []),
            )
            inserted += 1
        await session.commit()

    print(f"Seeded {inserted} items")


if __name__ == "__main__":
    asyncio.run(main())
