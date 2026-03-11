"""
Case memory for AI courier assistant: lexical and optional semantic match over ml_cases.jsonl.
Source of truth: data/ai/ml_cases.jsonl with fields:
id, input, label, decision, explanation, intent, role, entities,
severity, route_hint, source, version.
Embeddings: optional in-memory cache from data/ai/ml_cases_embeddings.json (see rebuild_case_embeddings.py).
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import structlog

log = structlog.get_logger(__name__)

ML_CASES_FILENAME = "ml_cases.jsonl"
ML_CASES_EMBEDDINGS_FILENAME = "ml_cases_embeddings.json"
DEFAULT_MIN_SIMILARITY = 0.35
STRONG_MATCH_THRESHOLD = 0.50
DEFAULT_SEMANTIC_MIN_SIMILARITY = 0.65


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    """Cosine similarity; clipped to [0, 1] for consistent scoring."""
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b, strict=True))
    norm_a = sum(x * x for x in a) ** 0.5
    norm_b = sum(x * x for x in b) ** 0.5
    if norm_a <= 0 or norm_b <= 0:
        return 0.0
    sim = dot / (norm_a * norm_b)
    return max(0.0, min(1.0, float(sim)))


def _tokenize(text: str) -> set[str]:
    """Tokens: alphanumeric + Cyrillic, length >= 2."""
    return {
        token
        for token in re.findall(r"[0-9a-zA-Zа-яА-ЯёЁ]+", (text or "").lower())
        if len(token) >= 2
    }


@dataclass
class SimilarCaseResult:
    """Result of find_similar_case: one known case + score."""

    case_id: str
    input: str
    label: str
    decision: str
    explanation: str
    similarity_score: float


class CaseClassifier:
    """
    Loads ml_cases.jsonl, normalizes cases, exposes find_similar_case(text).
    Uses lexical similarity (token overlap) only; no embeddings.
    """

    def __init__(
        self,
        data_root: str | Path = "data/ai",
        min_similarity: float = DEFAULT_MIN_SIMILARITY,
        semantic_min_similarity: float = DEFAULT_SEMANTIC_MIN_SIMILARITY,
    ) -> None:
        self._data_root = Path(data_root)
        self._min_similarity = min_similarity
        self._semantic_min_similarity = semantic_min_similarity
        self._cases: list[dict[str, Any]] = []
        self._case_embeddings: dict[str, list[float]] = {}  # case_id -> vector (in-memory cache)
        self._load()

    def _load(self) -> None:
        path = self._data_root / ML_CASES_FILENAME
        self._cases = []
        self._case_embeddings = {}
        if not path.exists():
            log.debug("case_classifier_no_file", path=str(path))
            return
        try:
            for line in path.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line:
                    continue
                try:
                    raw = json.loads(line)
                except json.JSONDecodeError:
                    continue
                case = self._normalize_case(raw)
                if case:
                    self._cases.append(case)
            log.info("case_classifier_loaded", path=str(path), count=len(self._cases))
        except Exception as exc:
            log.warning("case_classifier_load_error", path=str(path), error=str(exc))

        # Optional: load precomputed embeddings for semantic search (no DB dependency)
        emb_path = self._data_root / ML_CASES_EMBEDDINGS_FILENAME
        if emb_path.exists():
            try:
                data = json.loads(emb_path.read_text(encoding="utf-8"))
                if isinstance(data, list):
                    for item in data:
                        cid = str(item.get("id", "")).strip()
                        emb = item.get("embedding")
                        if cid and isinstance(emb, list) and len(emb) > 0:
                            self._case_embeddings[cid] = [float(x) for x in emb]
                elif isinstance(data, dict):
                    for cid, emb in data.items():
                        if isinstance(emb, list) and len(emb) > 0:
                            self._case_embeddings[str(cid)] = [float(x) for x in emb]
                log.info(
                    "case_classifier_embeddings_loaded",
                    path=str(emb_path),
                    count=len(self._case_embeddings),
                )
            except Exception as exc:
                log.warning(
                    "case_classifier_embeddings_load_error",
                    path=str(emb_path),
                    error=str(exc),
                )

    @staticmethod
    def _normalize_case(raw: dict[str, Any]) -> dict[str, Any] | None:
        """Extract and normalize id, input, label, decision, explanation."""
        case_id = str(raw.get("id", "")).strip()
        inp = str(raw.get("input", "")).strip()
        if not case_id or not inp:
            return None
        return {
            "id": case_id,
            "input": inp,
            "label": str(raw.get("label", "")).strip(),
            "decision": str(raw.get("decision", "")).strip(),
            "explanation": str(raw.get("explanation", "")).strip(),
        }

    def find_similar_case(self, text: str) -> SimilarCaseResult | None:
        """
        Find the best matching known case by lexical overlap (tokens).
        Returns None if no case above min_similarity.
        """
        if not text or not self._cases:
            return None

        query_tokens = _tokenize(text)
        if not query_tokens:
            return None

        best: SimilarCaseResult | None = None
        best_score = self._min_similarity

        for case in self._cases:
            case_input = case.get("input", "")
            case_tokens = _tokenize(case_input)
            if not case_tokens:
                continue

            overlap = len(query_tokens.intersection(case_tokens))
            ref_len = max(len(case_tokens), 1)
            overlap_ratio = overlap / ref_len

            query_coverage = overlap / max(len(query_tokens), 1)
            score = 0.6 * overlap_ratio + 0.4 * min(1.0, query_coverage)

            if score >= best_score:
                best_score = score
                best = SimilarCaseResult(
                    case_id=case["id"],
                    input=case["input"],
                    label=case["label"],
                    decision=case["decision"],
                    explanation=case["explanation"],
                    similarity_score=round(score, 4),
                )

        return best

    def find_similar_case_semantic(
        self,
        query_embedding: list[float],
        min_similarity: float | None = None,
    ) -> SimilarCaseResult | None:
        """
        Find the best matching known case by semantic similarity (cosine).
        Uses in-memory cache from ml_cases_embeddings.json. Returns None if
        embeddings are not loaded or no case above threshold.
        """
        if not query_embedding or not self._case_embeddings or not self._cases:
            return None

        threshold = min_similarity if min_similarity is not None else self._semantic_min_similarity
        best: SimilarCaseResult | None = None
        best_score = threshold

        case_by_id = {c["id"]: c for c in self._cases}
        for case_id, case_emb in self._case_embeddings.items():
            if len(case_emb) != len(query_embedding):
                continue
            score = _cosine_similarity(query_embedding, case_emb)
            if score >= best_score:
                case = case_by_id.get(case_id)
                if not case:
                    continue
                best_score = score
                best = SimilarCaseResult(
                    case_id=case["id"],
                    input=case["input"],
                    label=case["label"],
                    decision=case["decision"],
                    explanation=case["explanation"],
                    similarity_score=round(score, 4),
                )

        return best

    @property
    def has_semantic(self) -> bool:
        """True if semantic search is available (embeddings cache loaded)."""
        return len(self._case_embeddings) > 0

    def reload(self) -> None:
        """Reload ml_cases.jsonl and optional embeddings cache from disk."""
        self._load()
