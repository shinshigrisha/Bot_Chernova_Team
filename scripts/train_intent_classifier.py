#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

import joblib  # type: ignore[import]
from sklearn.feature_extraction.text import TfidfVectorizer  # type: ignore[import]
from sklearn.linear_model import LogisticRegression  # type: ignore[import]
from sklearn.pipeline import Pipeline  # type: ignore[import]

from src.core.services.ai.intent_engine import IntentEngine


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_ROOT = PROJECT_ROOT / "data" / "ai"
ML_CASES_PATH = DATA_ROOT / "ml_cases.jsonl"
MODEL_PATH = DATA_ROOT / "intent_classifier.joblib"


def load_dataset() -> tuple[list[str], list[str]]:
    """Загрузить (text, intent) из ml_cases.jsonl и привести intent к coarse-форме."""
    X: list[str] = []
    y: list[str] = []

    if not ML_CASES_PATH.exists():
        raise FileNotFoundError(f"ml_cases.jsonl not found: {ML_CASES_PATH}")

    for line in ML_CASES_PATH.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        text = (row.get("input") or "").strip()
        intent_raw = (row.get("intent") or "").strip()
        if not text or not intent_raw:
            continue
        coarse = IntentEngine.coarse_intent_for_catalog_intent(intent_raw)
        if coarse == "unknown":
            continue
        X.append(text)
        y.append(coarse)
    return X, y


def main() -> int:
    X, y = load_dataset()
    if not X:
        print("No training data for intent classifier (ml_cases.jsonl empty or unusable).")
        return 1

    pipe: Pipeline = Pipeline(
        [
            ("tfidf", TfidfVectorizer(ngram_range=(1, 2), min_df=1)),
            (
                "clf",
                LogisticRegression(
                    max_iter=1000,
                    class_weight="balanced",
                    n_jobs=-1,
                    multi_class="auto",
                ),
            ),
        ]
    )
    pipe.fit(X, y)

    MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(pipe, MODEL_PATH)
    print(f"Trained intent classifier on {len(X)} samples, saved to {MODEL_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

