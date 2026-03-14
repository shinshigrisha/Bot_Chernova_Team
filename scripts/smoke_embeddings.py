"""Minimal smoke script: local MiniLM embeddings load and produce 384-dim vector.

Verifies:
- model loads successfully (canonical get_embedding_service)
- embedding vector is produced and has expected length (384 for MiniLM-L6-v2)

Usage:
  python scripts/smoke_embeddings.py

Exit 0 on success; non-zero on failure.
"""
from __future__ import annotations

import asyncio
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

from src.core.services.ai.embedding_service import get_embedding_service


EXPECTED_DIM = 384
SAMPLE_TEXT = "курьер не дозвонился покупателю"


async def main() -> int:
    svc = get_embedding_service()
    print(f"EMBEDDING_PROVIDER={svc.provider}")
    print(f"EMBEDDING_MODEL={svc.model}")
    print(f"ENABLED={svc.enabled}")

    if not svc.enabled:
        print("SKIP: embedding service disabled (e.g. openai without key)", file=sys.stderr)
        return 0

    try:
        vec = await svc.embed_text(SAMPLE_TEXT)
    except Exception as e:
        print(f"FAIL: local embedding error: {e}", file=sys.stderr)
        return 1

    if vec is None:
        print("FAIL: embed_text returned None", file=sys.stderr)
        return 1

    dim = len(vec)
    print(f"VECTOR_DIM={dim}")
    if dim != EXPECTED_DIM:
        print(f"FAIL: expected vector length {EXPECTED_DIM}, got {dim}", file=sys.stderr)
        return 1

    print("OK: model loaded, vector produced, length check passed")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
