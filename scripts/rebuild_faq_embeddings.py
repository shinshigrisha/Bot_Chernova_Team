from __future__ import annotations

import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.core.services.ai.faq_embeddings_rebuild import rebuild_faq_embeddings_async
from src.infra.db.session import async_session_factory


async def main() -> None:
    result = await rebuild_faq_embeddings_async(
        session_factory=async_session_factory,
        embeddings_service=None,
    )
    if result.get("error"):
        print(f"Error: {result['error']}")
        return
    print(f"FAQ_TOTAL={result.get('total', 0)}")
    print(f"FAQ_EMBEDDINGS_UPDATED={result.get('updated', 0)}")
    print(f"FAQ_EMBEDDINGS_SKIPPED={result.get('skipped', 0)}")


if __name__ == "__main__":
    asyncio.run(main())
