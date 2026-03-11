#!/usr/bin/env python3
"""
Transform CRM-style training data into canonical AI curator knowledge files.

Reads: faq_seed.jsonl (legacy), ml_cases.jsonl, intent_tags.json, core_policy.json.
Writes: data/ai/faq_seed.jsonl, data/ai/ml_cases.jsonl, data/ai/intents_catalog.json.

Canonical schemas (snake_case, append-only):
- faq_seed.jsonl: one JSON object per line with fields:
  faq_id, intent, question, answer, category, tag, keywords, role, is_active,
  priority, risk_level, when_to_escalate, source, version
- ml_cases.jsonl: one JSON object per line with fields:
  id, input, label, decision, explanation, intent, role, entities,
  severity, route_hint, source, version
- intents_catalog.json: root object
  {
    "version": "1.0",
    "intents": [
      {
        "intent", "category", "crm_tag", "complaint_type", "role",
        "entities", "phrases", "keywords", "must_match",
        "priority", "route_preference", "risk_level", "clarify_if_missing"
      },
      ...
    ]
  }

Naming: snake_case only, no duplicate intents, anonymized.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

# Default data root (project root relative)
DEFAULT_DATA_ROOT = Path(__file__).resolve().parent.parent / "data" / "ai"

# Map Russian labels from ml_cases to canonical snake_case intents
LABEL_TO_INTENT = {
    "Неаккуратная доставка": "careless_delivery",
    "Температурный режим": "temperature",
    "Не отдали часть заказа": "missing_items",
    "Коммуникация с покупателем": "communication",
    "Коммуникация + тяжёлое нарушение": "communication_severe",
    "Игнор комментариев": "ignore_comments",
    "Отказ доставлять до двери": "refuse_door_delivery",
    "Отмена / заказ вернулся в магазин": "return_cancelled",
    "Нарушение Кодекса": "code_violation",
    "Нарушение регламента": "procedure_violation",
}


def _snake(s: str) -> str:
    """Normalize to snake_case: lowercase, spaces/punctuation to underscore."""
    if not s or not isinstance(s, str):
        return ""
    s = re.sub(r"[^\w\s]", " ", s)
    s = re.sub(r"\s+", "_", s.strip().lower())
    return re.sub(r"_+", "_", s).strip("_")


def _load_jsonl(path: Path) -> list[dict]:
    out = []
    if not path.exists():
        return out
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return out


def _load_json(path: Path, default: dict | list) -> dict | list:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return default


def _intent_from_faq_id(faq_id: str) -> str:
    """Derive intent from legacy faq id (e.g. faq_damage_eggs -> damage)."""
    if not faq_id or not isinstance(faq_id, str):
        return "general"
    # faq_damage_eggs -> damage, faq_temp_melted -> temperature
    parts = faq_id.replace("faq_", "").split("_")
    return "_".join(parts[:2]) if len(parts) >= 2 else (parts[0] if parts else "general")


def _category_from_intent(intent: str) -> str:
    """Map intent to high-level category."""
    category_map = {
        "damage": "delivery_quality",
        "damage_eggs": "delivery_quality",
        "careless_delivery": "delivery_quality",
        "missing_items": "delivery_quality",
        "missing_item": "delivery_quality",
        "temperature": "temperature",
        "temp_melted": "temperature",
        "late_delivery": "delivery_timing",
        "late_risk": "delivery_timing",
        "contact_customer": "contact",
        "no_answer": "contact",
        "communication": "communication",
        "communication_severe": "communication",
        "ignore_comments": "compliance",
        "refuse_door_delivery": "compliance",
        "return_cancelled": "return",
        "return": "return",
        "return_flow": "return",
        "parking": "operational",
        "battery_fire": "safety",
        "battery_smoke": "safety",
        "equipment": "operational",
        "conflict": "safety",
        "conflict_customer": "safety",
        "code_violation": "compliance",
        "procedure_violation": "compliance",
    }
    return category_map.get(intent, "general")


def _risk_level(intent: str, high_risk_topics: list[str]) -> str:
    if intent in ("battery_fire", "communication_severe", "conflict"):
        return "high"
    return "medium" if intent in ("missing_items", "temperature", "return_cancelled") else "low"


def _when_to_escalate(intent: str, risk: str) -> str:
    if risk == "high":
        return "always"
    if intent in ("missing_items", "return_cancelled", "code_violation", "procedure_violation"):
        return "when_unclear_or_dispute"
    return "when_out_of_scope"


def build_faq_seed(
    data_root: Path,
    intent_tags: dict,
    core_policy: dict,
) -> list[dict]:
    """Build faq_seed records (regulation cards) from legacy faq_seed + must_match."""
    faq_path = data_root / "faq_seed.jsonl"
    legacy_faq = _load_jsonl(faq_path)
    must_match = core_policy.get("must_match_cases", [])
    high_risk = core_policy.get("high_risk_topics", [])

    out = []
    seen_intent_question = set()

    # From must_match: regulation-style answers
    for m in must_match:
        intents = m.get("intents") or []
        intent = (intents[0] if intents else "general").strip().lower().replace(" ", "_")
        question = (m.get("trigger") or "").strip()
        answer = (m.get("response") or "").strip()
        if not question or not answer:
            continue
        key = (intent, question)
        if key in seen_intent_question:
            continue
        seen_intent_question.add(key)
        keywords = list(m.get("keywords") or [])
        category = _category_from_intent(intent)
        risk = _risk_level(intent, high_risk)
        faq_id = str(m.get("id") or f"must_{intent}_{len(out)+1}")
        out.append(
            {
                "faq_id": faq_id,
                "intent": intent,
                "question": question,
                "answer": answer,
                "category": category,
                "tag": intent,
                "keywords": keywords,
                "role": "courier",
                "is_active": True,
                "priority": "high" if risk == "high" else "normal",
                "risk_level": risk,
                "when_to_escalate": _when_to_escalate(intent, risk),
                "source": "core_policy.must_match",
                "version": "1.0",
            }
        )

    # From legacy faq_seed (id, tags, q, a) or already canonical (intent, question, answer)
    for row in legacy_faq:
        q = (row.get("q") or row.get("question") or "").strip()
        a = (row.get("a") or row.get("answer") or "").strip()
        if not q or not a:
            continue
        # Preserve intent if already canonical; else derive from id/tags
        existing_intent = row.get("intent")
        if existing_intent and isinstance(existing_intent, str):
            intent = _snake(existing_intent) or "general"
        else:
            legacy_faq_id = str(row.get("id", "")).strip()
            tags = row.get("tags") or []
            intent = _intent_from_faq_id(legacy_faq_id) if legacy_faq_id else (tags[0] if tags else "general")
            intent = _snake(intent) or "general"
        keywords = (
            list(row.get("keywords") or [])
            if row.get("keywords")
            else list(intent_tags.get(intent, []))
            if isinstance(intent_tags.get(intent), list)
            else []
        )
        category = _category_from_intent(intent)
        risk = _risk_level(intent, high_risk)
        key = (intent, q)
        if key in seen_intent_question:
            continue
        seen_intent_question.add(key)
        faq_id = str(row.get("faq_id") or row.get("id") or f"faq_{intent}_{len(out)+1}")
        out.append(
            {
                "faq_id": faq_id,
                "intent": intent,
                "question": q,
                "answer": a,
                "category": category,
                "tag": intent,
                "keywords": keywords,
                "role": "courier",
                "is_active": bool(row.get("is_active", True)),
                "priority": str(row.get("priority") or "normal"),
                "risk_level": risk,
                "when_to_escalate": _when_to_escalate(intent, risk),
                "source": str(row.get("source") or "legacy_faq_seed"),
                "version": str(row.get("version") or "1.0"),
            }
        )

    return out


def build_ml_cases(data_root: Path) -> list[dict]:
    """Build ml_cases with canonical schema."""
    path = data_root / "ml_cases.jsonl"
    rows = _load_jsonl(path)
    out = []
    for row in rows:
        case_id = row.get("id")
        inp = (row.get("input") or "").strip()
        if case_id is None or not inp:
            continue
        label = (row.get("label") or "").strip()
        decision = (row.get("decision") or "").strip()
        explanation = (row.get("explanation") or "").strip()
        intent = (row.get("intent") or "").strip()
        severity = str(row.get("severity") or "medium")
        route_hint = str(row.get("route_hint") or "")
        source = str(row.get("source") or "ml_cases")
        version = str(row.get("version") or "1.0")
        entities = row.get("entities") or []
        out.append(
            {
                "id": case_id,
                "input": inp,
                "label": label,
                "decision": decision,
                "explanation": explanation,
                "intent": intent,
                "role": "courier",
                "entities": entities,
                "severity": severity,
                "route_hint": route_hint,
                "source": source,
                "version": version,
            }
        )
    return out


def build_intents_catalog(
    intent_tags: dict,
    ml_cases: list[dict],
    faq_seed: list[dict],
) -> list[dict]:
    """Build intents_catalog: unique intents with canonical metadata."""
    intents_seen: set[str] = set()
    catalog = []

    # From intent_tags (canonical source for tag names)
    for raw_intent, keywords in intent_tags.items():
        intent = _snake(str(raw_intent)) or "general"
        if not intent or intent in intents_seen:
            continue
        intents_seen.add(intent)
        risk = _risk_level(intent, [])
        catalog.append(
            {
                "intent": intent,
                "category": _category_from_intent(intent),
                "crm_tag": intent,
                "complaint_type": intent,
                "role": "courier",
                "entities": [],
                "phrases": [],
                "keywords": list(keywords or []),
                "must_match": False,
                "priority": "high" if risk == "high" else "normal",
                "route_preference": "strict" if risk == "high" else "auto",
                "risk_level": risk,
                "clarify_if_missing": risk != "high",
            }
        )

    # From ml_cases labels -> intents
    for case in ml_cases:
        label = (case.get("label") or "").strip()
        intent = LABEL_TO_INTENT.get(label) or _snake(label)
        if not intent:
            continue
        intent = intent.replace(" ", "_").lower()
        if intent in intents_seen:
            continue
        intents_seen.add(intent)
        risk = _risk_level(intent, [])
        catalog.append(
            {
                "intent": intent,
                "category": _category_from_intent(intent),
                "crm_tag": intent,
                "complaint_type": intent,
                "role": "courier",
                "entities": [],
                "phrases": [],
                "keywords": [],
                "must_match": False,
                "priority": "high" if risk == "high" else "normal",
                "route_preference": "strict" if risk == "high" else "auto",
                "risk_level": risk,
                "clarify_if_missing": risk != "high",
            }
        )

    # From faq_seed intents
    for row in faq_seed:
        intent = (row.get("intent") or "").strip()
        if not intent or intent in intents_seen:
            continue
        intents_seen.add(intent)
        category = row.get("category", _category_from_intent(intent))
        risk = str(row.get("risk_level") or _risk_level(intent, []))
        catalog.append(
            {
                "intent": intent,
                "category": category,
                "crm_tag": intent,
                "complaint_type": intent,
                "role": "courier",
                "entities": [],
                "phrases": [],
                "keywords": list(row.get("keywords") or []),
                "must_match": True if str(row.get("when_to_escalate") or "") == "always" else False,
                "priority": str(row.get("priority") or ("high" if risk == "high" else "normal")),
                "route_preference": "strict" if risk == "high" else "auto",
                "risk_level": risk,
                "clarify_if_missing": risk != "high",
            }
        )

    return sorted(catalog, key=lambda x: x["intent"])


def main() -> int:
    args = sys.argv[1:]
    if args and args[0] == "--verify":
        data_root = Path(args[1]) if len(args) > 1 else DEFAULT_DATA_ROOT
        return 0 if verify_structure(data_root) else 1
    data_root = Path(args[0]) if args else DEFAULT_DATA_ROOT
    if not data_root.is_dir():
        print(f"Data root is not a directory: {data_root}", file=sys.stderr)
        return 1

    intent_tags = _load_json(data_root / "intent_tags.json", {})
    core_policy = _load_json(data_root / "core_policy.json", {})

    faq_seed = build_faq_seed(data_root, intent_tags, core_policy)
    ml_cases = build_ml_cases(data_root)
    intents_catalog = build_intents_catalog(intent_tags, ml_cases, faq_seed)

    # Write faq_seed.jsonl
    faq_path = data_root / "faq_seed.jsonl"
    with open(faq_path, "w", encoding="utf-8") as f:
        for rec in faq_seed:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    print(f"Wrote {len(faq_seed)} records to {faq_path}")

    # Write ml_cases.jsonl
    ml_path = data_root / "ml_cases.jsonl"
    with open(ml_path, "w", encoding="utf-8") as f:
        for rec in ml_cases:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    print(f"Wrote {len(ml_cases)} records to {ml_path}")

    # Write intents_catalog.json (root object with version + intents[])
    catalog_path = data_root / "intents_catalog.json"
    with open(catalog_path, "w", encoding="utf-8") as f:
        json.dump({"version": "1.0", "intents": intents_catalog}, f, ensure_ascii=False, indent=2)
    print(f"Wrote {len(intents_catalog)} intents to {catalog_path}")

    return 0


def verify_structure(data_root: Path) -> bool:
    """Check that generated files have expected keys. Returns True if ok."""
    ok = True
    # faq_seed
    faq_path = data_root / "faq_seed.jsonl"
    required_faq = {
        "faq_id",
        "intent",
        "question",
        "answer",
        "category",
        "tag",
        "keywords",
        "role",
        "is_active",
        "priority",
        "risk_level",
        "when_to_escalate",
        "source",
        "version",
    }
    for i, line in enumerate(faq_path.read_text(encoding="utf-8").splitlines()):
        if not line.strip():
            continue
        row = json.loads(line)
        missing = required_faq - set(row.keys())
        if missing:
            print(f"faq_seed line {i+1}: missing keys {missing}", file=sys.stderr)
            ok = False
    # ml_cases
    ml_path = data_root / "ml_cases.jsonl"
    required_ml = {
        "id",
        "input",
        "label",
        "decision",
        "explanation",
        "intent",
        "role",
        "entities",
        "severity",
        "route_hint",
        "source",
        "version",
    }
    for i, line in enumerate(ml_path.read_text(encoding="utf-8").splitlines()):
        if not line.strip():
            continue
        row = json.loads(line)
        missing = required_ml - set(row.keys())
        if missing:
            print(f"ml_cases line {i+1}: missing keys {missing}", file=sys.stderr)
            ok = False
    # intents_catalog
    cat_path = data_root / "intents_catalog.json"
    catalog_obj = json.loads(cat_path.read_text(encoding="utf-8"))
    if not isinstance(catalog_obj, dict) or "version" not in catalog_obj or "intents" not in catalog_obj:
        print("intents_catalog.json: root must be object with 'version' and 'intents'", file=sys.stderr)
        ok = False
    else:
        required_cat = {
            "intent",
            "category",
            "crm_tag",
            "complaint_type",
            "role",
            "entities",
            "phrases",
            "keywords",
            "must_match",
            "priority",
            "route_preference",
            "risk_level",
            "clarify_if_missing",
        }
        for i, row in enumerate(catalog_obj.get("intents", [])):
            missing = required_cat - set(row.keys())
            if missing:
                print(f"intents_catalog.intents[{i}]: missing keys {missing}", file=sys.stderr)
                ok = False
    return ok


if __name__ == "__main__":
    sys.exit(main())
