from __future__ import annotations

import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.core.services.ai.embeddings_service import EmbeddingsService
from src.infra.db.repositories.faq_repo import FAQRepository
from src.infra.db.session import async_session_factory


async def main() -> None:
    repo = FAQRepository()
    embeddings_service = EmbeddingsService()
    try:
        if not embeddings_service.enabled:
            print("Embeddings disabled: OPENAI_API_KEY is not configured.")
            return

        async with async_session_factory() as session:
            faq_rows = await repo.list_embedding_sources(session=session)
            if not faq_rows:
                print("No FAQ rows found.")
                return

            payloads = [
                EmbeddingsService.build_faq_text(
                    question=str(row.get("question") or ""),
                    answer=str(row.get("answer") or ""),
                )
                for row in faq_rows
            ]
            embeddings = await embeddings_service.embed_texts(payloads)

            updated = 0
            skipped = 0
            for row, embedding in zip(faq_rows, embeddings, strict=False):
                if embedding is None:
                    skipped += 1
                    continue
                await repo.set_embedding(
                    faq_id=int(row["id"]),
                    embedding=EmbeddingsService.serialize_embedding(embedding),
                    session=session,
                )
                updated += 1

            await session.commit()
            print(f"FAQ_TOTAL={len(faq_rows)}")
            print(f"FAQ_EMBEDDINGS_UPDATED={updated}")
            print(f"FAQ_EMBEDDINGS_SKIPPED={skipped}")
    finally:
        await embeddings_service.close()


if __name__ == "__main__":
    asyncio.run(main())
