#!/usr/bin/env python3
from __future__ import annotations

"""
Normalize delivery dataset assets into canonical AI curator knowledge contracts.

Source assets (data/ai/):
- delivery_entities.json      -> canonical entity dictionary (used by intents)
- delivery_intents_90.json    -> raw intents with questions/answers, entities
- delivery_dataset_meta.json  -> dataset-level metadata
- datasets/train.jsonl        -> ML train split (generated elsewhere, validated only)
- datasets/valid.jsonl        -> ML valid split (validated only)
- datasets/test.jsonl         -> ML test split  (validated only)

Canonical targets (runtime / ML ready, snake_case keys):
- data/ai/intents_catalog.json (root object: {"version": "1.0", "intents": [...]})
- data/ai/faq_seed.jsonl       (one JSON object per line with fields:
    faq_id, intent, question, answer, category, tag, keywords, role, is_active,
    priority, risk_level, when_to_escalate, source, version
  )
- data/ai/ml_cases.jsonl       (one JSON object per line with fields:
    id, input, label, decision, explanation, intent, role, entities,
    severity, route_hint, source, version
  )

Notes:
- Script НЕ меняет рантайм бота; только готовит/перегенерирует знания.
- JSON/JSONL остаются основным источником правды для AI, CSV используются только для аналитики.
"""

import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DATA_AI = ROOT / "data" / "ai"
DATASETS_DIR = DATA_AI / "datasets"


@dataclass(frozen=True)
class DeliveryIntent:
    intent: str
    category: str
    crm_tag: str
    complaint_type: str
    role: str
    entities: list[str]
    answer: str
    questions: list[str]


def _load_python_data_file(path: Path, var_name: str) -> Any:
    """
    Execute a Python-typed "data" file (delivery_*.json) and return variable by name.
    These files contain Python code, not pure JSON; we avoid inventing new schemas.
    """
    if not path.exists():
        raise FileNotFoundError(f"Source file not found: {path}")
    code = path.read_text(encoding="utf-8")
    namespace: dict[str, Any] = {}
    exec(compile(code, str(path), "exec"), namespace)  # trusted local data scripts
    if var_name not in namespace:
        raise RuntimeError(f"{path} did not define expected variable {var_name!r}")
    return namespace[var_name]


def _risk_level_from_category(category: str) -> str:
    cat = (category or "").lower()
    if "безопас" in cat:
        return "high"
    if "недовоз" in cat or "качество" in cat or "оплата" in cat:
        return "medium"
    return "low"


def _when_to_escalate_from_risk(risk: str) -> str:
    if risk == "high":
        return "always"
    if risk == "medium":
        return "when_unclear_or_dispute"
    return "when_out_of_scope"


def _normalize_intents(raw_intents: list[dict[str, Any]]) -> list[DeliveryIntent]:
    intents: list[DeliveryIntent] = []
    for item in raw_intents:
        intent = str(item.get("intent") or "").strip()
        if not intent:
            continue
        category = str(item.get("category") or "").strip()
        crm_tag = str(item.get("crm_tag") or "").strip()
        complaint_type = str(item.get("complaint_type") or "").strip()
        role = str(item.get("role") or "").strip()
        entities = [str(e).strip() for e in item.get("entities") or [] if str(e).strip()]
        answer = str(item.get("answer") or "").strip()
        questions_raw = item.get("questions") or []
        if isinstance(questions_raw, str):
            questions_raw = [questions_raw]
        questions = [str(q).strip() for q in questions_raw if str(q).strip()]
        if not questions:
            continue
        intents.append(
            DeliveryIntent(
                intent=intent,
                category=category,
                crm_tag=crm_tag,
                complaint_type=complaint_type,
                role=role,
                entities=entities,
                answer=answer,
                questions=questions,
            )
        )
    if not intents:
        raise RuntimeError("No valid intents found in delivery_intents_90.json")
    return intents


def build_intents_catalog(intents: list[DeliveryIntent]) -> dict[str, Any]:
    """Build canonical intents_catalog.json root object."""
    catalog_intents: list[dict[str, Any]] = []
    for item in intents:
        risk = _risk_level_from_category(item.category)
        catalog_intents.append(
            {
                "intent": item.intent,
                "category": item.category,
                "crm_tag": item.crm_tag,
                "complaint_type": item.complaint_type,
                "role": item.role,
                "entities": item.entities,
                "phrases": item.questions,
                "keywords": [],
                "must_match": False,
                "priority": "high" if risk == "high" else "normal",
                "route_preference": "strict" if risk == "high" else "auto",
                "risk_level": risk,
                "clarify_if_missing": risk != "high",
            }
        )
    return {"version": "1.0", "intents": catalog_intents}


def build_faq_seed(intents: list[DeliveryIntent]) -> list[dict[str, Any]]:
    """Build canonical faq_seed.jsonl rows from intent questions/answers."""
    rows: list[dict[str, Any]] = []
    for item in intents:
        risk = _risk_level_from_category(item.category)
        when_to_escalate = _when_to_escalate_from_risk(risk)
        for idx, question in enumerate(item.questions, start=1):
            faq_id = f"{item.intent}__q{idx:02d}"
            rows.append(
                {
                    "faq_id": faq_id,
                    "intent": item.intent,
                    "question": question,
                    "answer": item.answer,
                    "category": item.category,
                    "tag": item.intent,
                    "keywords": [],
                    "role": item.role,
                    "is_active": True,
                    "priority": "high" if risk == "high" else "normal",
                    "risk_level": risk,
                    "when_to_escalate": when_to_escalate,
                    "source": "delivery_intents_90",
                    "version": "1.0",
                }
            )
    return rows


def build_ml_cases(intents: list[DeliveryIntent]) -> list[dict[str, Any]]:
    """Build canonical ml_cases.jsonl rows as case memory seeds."""
    cases: list[dict[str, Any]] = []
    for item in intents:
        if not item.questions:
            continue
        input_text = item.questions[0]
        label = item.crm_tag or item.category or item.intent
        decision = item.answer
        explanation = item.complaint_type or item.category
        risk = _risk_level_from_category(item.category)
        severity = "high" if risk == "high" else ("medium" if risk == "medium" else "low")
        route_hint = item.category or ""
        cases.append(
            {
                "id": item.intent,
                "input": input_text,
                "label": label,
                "decision": decision,
                "explanation": explanation,
                "intent": item.intent,
                "role": item.role,
                "entities": item.entities,
                "severity": severity,
                "route_hint": route_hint,
                "source": "delivery_intents_90",
                "version": "1.0",
            }
        )
    if not cases:
        raise RuntimeError("No ML cases could be built from intents")
    return cases


def validate_splits() -> None:
    """Validate that train/valid/test splits exist; do not modify them."""
    missing: list[str] = []
    for name in ("train.jsonl", "valid.jsonl", "test.jsonl"):
        path = DATASETS_DIR / name
        if not path.exists():
            missing.append(str(path))
    if missing:
        raise FileNotFoundError(
            "Some dataset splits are missing; expected JSONL generators or data at:\n"
            + "\n".join(missing)
        )


def main() -> int:
    # 1) Validate & load source assets
    entities_path = DATA_AI / "delivery_entities.json"
    intents_path = DATA_AI / "delivery_intents_90.json"
    meta_path = DATA_AI / "delivery_dataset_meta.json"

    if not entities_path.exists():
        print(f"[ERROR] Missing entities file: {entities_path}", file=sys.stderr)
        return 1
    if not intents_path.exists():
        print(f"[ERROR] Missing intents file: {intents_path}", file=sys.stderr)
        return 1
    if not meta_path.exists():
        print(f"[ERROR] Missing dataset meta file: {meta_path}", file=sys.stderr)
        return 1

    # delivery_entities.json: currently not transformed, but validated as importable
    _ = _load_python_data_file(entities_path, "entities")

    raw_intents = _load_python_data_file(intents_path, "intents")
    if not isinstance(raw_intents, list):
        print("[ERROR] delivery_intents_90.json did not yield a list of intents", file=sys.stderr)
        return 1
    intents = _normalize_intents(raw_intents)

    # Validate that dataset splits exist (train/valid/test.jsonl)
    validate_splits()

    # 2) Build canonical targets
    intents_catalog = build_intents_catalog(intents)
    faq_rows = build_faq_seed(intents)
    ml_cases = build_ml_cases(intents)

    # 3) Write outputs under data/ai/
    faq_out = DATA_AI / "faq_seed.jsonl"
    ml_out = DATA_AI / "ml_cases.jsonl"
    catalog_out = DATA_AI / "intents_catalog.json"

    with faq_out.open("w", encoding="utf-8") as f:
        for row in faq_rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    with ml_out.open("w", encoding="utf-8") as f:
        for row in ml_cases:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    catalog_out.write_text(
        json.dumps(intents_catalog, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(f"[OK] Wrote {len(faq_rows)} FAQ cards to {faq_out}")
    print(f"[OK] Wrote {len(ml_cases)} ML cases to {ml_out}")
    print(f"[OK] Wrote {len(intents_catalog['intents'])} intents to {catalog_out}")
    print(f"[OK] Splits validated in {DATASETS_DIR}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

