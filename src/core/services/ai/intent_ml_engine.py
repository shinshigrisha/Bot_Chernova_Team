from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

import json

from src.core.services.ai.intent_engine import (
    IntentDetectionResult,
    IntentEngine,
)


@dataclass(slots=True)
class _IntentExample:
    intent_raw: str
    intent_coarse: str
    question: str


class IntentMLEngine:
    """Лёгкий ML-слой для intent'ов на основе delivery_intents_90.json.

    Модель: nearest-neighbour по примерным вопросам с использованием
    similarity-метрики IntentEngine._similarity. Не использует внешние ML-библиотеки.
    """

    def __init__(
        self,
        *,
        data_path: str | Path | None = None,
        intents_data: Sequence[Mapping[str, Any]] | None = None,
        min_similarity: float = 0.82,
    ) -> None:
        if data_path is None and intents_data is None:
            # data/ai/delivery_intents_90.json относительно корня проекта
            data_path = (
                Path(__file__)
                .resolve()
                .parents[3]
                / "data"
                / "ai"
                / "delivery_intents_90.json"
            )
        self._examples: list[_IntentExample] = []
        self._min_similarity = float(min_similarity)
        self._load(data_path=data_path, intents_data=intents_data)

    # ---- Public API -------------------------------------------------------------

    def predict(self, text: str) -> IntentDetectionResult:
        """Вернуть IntentDetectionResult на основе ближайшего примера.

        Если уверенности недостаточно, возвращает intent='unknown'.
        """
        normalized = IntentEngine._normalize_text(text)  # type: ignore[attr-defined]
        if not normalized or not self._examples:
            return self._unknown()

        best: _IntentExample | None = None
        best_sim = 0.0
        for ex in self._examples:
            sim = IntentEngine._similarity(normalized, ex.question)  # type: ignore[attr-defined]
            if sim > best_sim:
                best_sim = sim
                best = ex

        if best is None or best_sim < self._min_similarity:
            return self._unknown()

        # Нормализуем к SUPPORTED_INTENTS через coarse-интерпретацию каталога.
        coarse = IntentEngine.coarse_intent_for_catalog_intent(best.intent_raw)
        if coarse == "unknown":
            return self._unknown()

        # Маппим [min_similarity, 1.0] → [0.70, 0.92]
        margin = max(0.0, min(1.0, (best_sim - self._min_similarity) / max(1e-6, 1.0 - self._min_similarity)))
        confidence = 0.70 + margin * 0.22

        return IntentDetectionResult(
            intent=coarse,
            confidence=round(confidence, 4),
            matched_keywords=[],
            matched_catalog_intent=best.intent_raw,
        )

    # ---- Internal --------------------------------------------------------------

    def _load(
        self,
        *,
        data_path: str | Path | None,
        intents_data: Sequence[Mapping[str, Any]] | None,
    ) -> None:
        raw: Sequence[Mapping[str, Any]]
        if intents_data is not None:
            raw = intents_data
        else:
            path = Path(data_path) if data_path is not None else None
            if path is None or not path.exists():
                self._examples = []
                return
            try:
                raw_obj = json.loads(path.read_text(encoding="utf-8"))
                if not isinstance(raw_obj, list):
                    self._examples = []
                    return
                raw = [x for x in raw_obj if isinstance(x, dict)]
            except Exception:
                self._examples = []
                return

        examples: list[_IntentExample] = []
        for item in raw:
            intent_raw = str(item.get("intent") or "").strip()
            if not intent_raw:
                continue
            coarse = IntentEngine.coarse_intent_for_catalog_intent(intent_raw)
            if coarse == "unknown":
                continue
            questions = item.get("questions") or []
            if isinstance(questions, str):
                questions = [questions]
            if not isinstance(questions, Sequence):
                continue
            for q in questions:
                q_norm = IntentEngine._normalize_text(str(q))  # type: ignore[attr-defined]
                if not q_norm:
                    continue
                examples.append(
                    _IntentExample(
                        intent_raw=intent_raw,
                        intent_coarse=coarse,
                        question=q_norm,
                    )
                )

        self._examples = examples

    @staticmethod
    def _unknown() -> IntentDetectionResult:
        return IntentDetectionResult(
            intent="unknown",
            confidence=0.0,
            matched_keywords=[],
            matched_catalog_intent=None,
        )

