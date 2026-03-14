"""Единый скрипт пересборки индексов эмбеддингов: FAQ (pgvector) и ML-кейсы (ml_cases_embeddings.json).

Использование:
  python scripts/rebuild_embeddings.py [--all]       # по умолчанию: FAQ + cases
  python scripts/rebuild_embeddings.py --faq         # только FAQ (БД)
  python scripts/rebuild_embeddings.py --cases      # только ml_cases (файл)
  python scripts/rebuild_embeddings.py --all        # оба

Перед пересборкой FAQ убедитесь, что FAQ загружены (scripts/seed_faq.py из data/ai/faq_seed.jsonl).
Канонический embeddings flow: EmbeddingsService (embedding_service.get_embedding_service()).

Запуск с хоста (compose поднят, порт 5432 проброшен):
  DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/delivery_assistant python scripts/rebuild_embeddings.py --faq
Или из контейнера (DATABASE_URL из .env с хостом postgres):
  docker compose run --rm bot python scripts/rebuild_embeddings.py --faq
"""

from __future__ import annotations

import argparse
import asyncio
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


async def main() -> None:
    parser = argparse.ArgumentParser(
        description="Rebuild FAQ and/or ML case embeddings (canonical EmbeddingsService)."
    )
    parser.add_argument(
        "--faq",
        action="store_true",
        help="Rebuild only FAQ embeddings (DB, pgvector)",
    )
    parser.add_argument(
        "--cases",
        action="store_true",
        help="Rebuild only ML case embeddings (data/ai/ml_cases_embeddings.json)",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Rebuild both FAQ and ML cases (default if no --faq/--cases)",
    )
    args = parser.parse_args()

    do_faq = args.faq or args.all or (not args.faq and not args.cases)
    do_cases = args.cases or args.all or (not args.faq and not args.cases)

    exit_code = 0

    if do_faq:
        from src.core.services.ai.faq_embeddings_rebuild import rebuild_faq_embeddings_async
        from src.infra.db.session import async_session_factory

        print("Rebuilding FAQ embeddings...", flush=True)
        result = await rebuild_faq_embeddings_async(
            session_factory=async_session_factory,
            embeddings_service=None,
        )
        if result.get("error"):
            err = result["error"]
            print(f"FAQ rebuild error: {err}", file=sys.stderr)
            if "connection" in err.lower() or "closed" in err.lower():
                print("Hint: check DATABASE_URL and that PostgreSQL is running.", file=sys.stderr)
            exit_code = 1
        else:
            print(
                f"FAQ: total={result.get('total', 0)}, updated={result.get('updated', 0)}, "
                f"skipped={result.get('skipped', 0)}"
            )
            if result.get("output"):
                print(f"output: {result['output']}")

    if do_cases:
        print("Rebuilding ML case embeddings...", flush=True)
        proc = subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "rebuild_case_embeddings.py")],
            cwd=str(ROOT),
        )
        if proc.returncode != 0:
            exit_code = 1

    sys.exit(exit_code)


if __name__ == "__main__":
    asyncio.run(main())
