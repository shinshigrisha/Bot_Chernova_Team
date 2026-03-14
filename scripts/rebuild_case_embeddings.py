"""Rebuild in-memory embeddings cache for ML cases (CaseClassifier semantic search).

Reads data/ai/ml_cases.jsonl, generates embeddings for each "input" via canonical
EmbeddingsService (local MiniLM by default: EMBEDDING_PROVIDER=local). Writes
data/ai/ml_cases_embeddings.json. No database dependency. No external embeddings API
required when EMBEDDING_PROVIDER=local.
Run after adding/editing ml_cases.jsonl so semantic_case routing can use the cache.
"""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.core.services.ai.embeddings_service import EmbeddingsService

ML_CASES_PATH = ROOT / "data" / "ai" / "ml_cases.jsonl"
ML_CASES_EMBEDDINGS_PATH = ROOT / "data" / "ai" / "ml_cases_embeddings.json"


async def main() -> None:
    if not ML_CASES_PATH.exists():
        print(f"ML cases file not found: {ML_CASES_PATH}")
        return

    service = EmbeddingsService()
    if not service.enabled:
        print(
            "Embeddings disabled (set EMBEDDING_PROVIDER=local for local MiniLM, "
            "or configure OpenAI API key for openai provider).",
            file=sys.stderr,
        )
        return

    cases = []
    for line in ML_CASES_PATH.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            raw = json.loads(line)
        except json.JSONDecodeError:
            continue
        case_id = str(raw.get("id", "")).strip()
        inp = str(raw.get("input", "")).strip()
        if case_id and inp:
            cases.append(
                {
                    "id": case_id,
                    "input": inp,
                    "label": str(raw.get("label", "")).strip(),
                    "decision": str(raw.get("decision", "")).strip(),
                    "explanation": str(raw.get("explanation", "")).strip(),
                }
            )

    if not cases:
        print("No valid cases in ml_cases.jsonl.")
        return

    texts = [c["input"] for c in cases]
    embeddings = await service.embed_texts(texts)
    await service.close()

    out_list = []
    skipped = 0
    for case, emb in zip(cases, embeddings, strict=False):
        if emb is None:
            skipped += 1
            continue
        out_list.append(
            {
                "id": case["id"],
                "input": case["input"],
                "label": case["label"],
                "decision": case["decision"],
                "explanation": case["explanation"],
                "embedding": emb,
            }
        )

    ML_CASES_EMBEDDINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
    ML_CASES_EMBEDDINGS_PATH.write_text(
        json.dumps(out_list, ensure_ascii=False, indent=0),
        encoding="utf-8",
    )

    total = len(cases)
    updated = len(out_list)
    output_path = str(ML_CASES_EMBEDDINGS_PATH.resolve())
    print(f"total: {total}, updated: {updated}, skipped: {skipped}")
    print(f"output: {output_path}")


if __name__ == "__main__":
    asyncio.run(main())
