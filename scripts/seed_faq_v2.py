from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path

import asyncpg

from repositories.faq_repo import FAQRepository

SEED_PATH = Path("data/ai/faq_seed.jsonl")


async def main() -> None:
    dsn = os.getenv("DATABASE_URL")
    if not dsn:
        raise RuntimeError("DATABASE_URL is not set")
    if not SEED_PATH.exists():
        raise RuntimeError(f"Seed file not found: {SEED_PATH}")

    # asyncpg expects postgresql:// form
    dsn = dsn.replace("postgresql+asyncpg://", "postgresql://")
    pool = await asyncpg.create_pool(dsn=dsn, min_size=1, max_size=5)
    repo = FAQRepository(pool)

    # 5-10 minimal records (from jsonl; keep first 10)
    inserted = 0
    for line in SEED_PATH.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        item = json.loads(line)
        await repo.add_faq(
            question=item.get("q", ""),
            answer=item.get("a", ""),
            category=None,
            tag=(item.get("tags") or [None])[0],
            keywords=item.get("tags", []),
        )
        inserted += 1
        if inserted >= 10:
            break

    await pool.close()
    print(f"Seeded {inserted} items")


if __name__ == "__main__":
    asyncio.run(main())
