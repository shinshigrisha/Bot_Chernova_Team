from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

try:  # optional dependency, не должен ломать рантайм
    import joblib  # type: ignore[import]
except Exception:  # pragma: no cover - защитный слой
    joblib = None  # type: ignore[assignment]

from src.core.services.ai.intent_engine import IntentDetectionResult


@dataclass
class IntentMLClassifier:
    """Runtime-обёртка над intent_classifier.joblib (TF-IDF + LogisticRegression).

    Если модель или зависимости недоступны, предсказание всегда даёт unknown.
    """

    model_path: Path
    _model: Any | None = None

    def _load(self) -> None:
        if self._model is not None or joblib is None:
            return
        if not self.model_path.exists():
            return
        try:
            self._model = joblib.load(self.model_path)  # type: ignore[arg-type]
        except Exception:  # pragma: no cover - защитный слой
            self._model = None

    def predict(self, text: str) -> IntentDetectionResult:
        """Вернуть IntentDetectionResult по ML-модели или unknown при ошибке/низкой уверенности."""
        self._load()
        if self._model is None:
            return IntentDetectionResult(
                intent="unknown",
                confidence=0.0,
                matched_keywords=[],
                matched_catalog_intent=None,
            )

        normalized = (text or "").strip()
        if not normalized:
            return IntentDetectionResult(
                intent="unknown",
                confidence=0.0,
                matched_keywords=[],
                matched_catalog_intent=None,
            )

        try:
            proba = self._model.predict_proba([normalized])[0]
            labels = self._model.classes_
        except Exception:  # pragma: no cover - защитный слой
            return IntentDetectionResult(
                intent="unknown",
                confidence=0.0,
                matched_keywords=[],
                matched_catalog_intent=None,
            )

        if not len(proba):
            return IntentDetectionResult(
                intent="unknown",
                confidence=0.0,
                matched_keywords=[],
                matched_catalog_intent=None,
            )

        import numpy as np  # type: ignore[import]

        idx = int(np.argmax(proba))
        intent = str(labels[idx])
        conf_raw = float(proba[idx])

        # Жёстко ограничиваем доверие и отсекаем совсем слабые случаи.
        if conf_raw < 0.4:
            return IntentDetectionResult(
                intent="unknown",
                confidence=0.0,
                matched_keywords=[],
                matched_catalog_intent=None,
            )

        confidence = max(0.7, min(0.95, conf_raw))
        return IntentDetectionResult(
            intent=intent,
            confidence=round(confidence, 4),
            matched_keywords=[],
            matched_catalog_intent=None,
        )

