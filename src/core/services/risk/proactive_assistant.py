from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from src.core.services.risk import RiskInput


@dataclass(slots=True)
class ProactiveRiskSignal:
    """Resolved proactive risk signal for delivery events."""

    risk_type: str
    severity: str
    text: str
    escalate: bool
    courier_tg_id: int | None = None
    curator_tg_id: int | None = None


class _RiskAssistantEngine(Protocol):
    """Narrow protocol for AI courier/curator assistant used by proactive layer."""

    def get_risk_recommendation(self, risk_input: RiskInput):
        ...


class ProactiveRiskAssistant:
    """Conservative proactive risk assistant over RiskEngine + RecommendationEngine.

    Этот слой НЕ шлёт сообщения сам:
    - только решает, есть ли сигнал для алерта;
    - возвращает короткий текст и флаги эскалации.

    Отправка уведомлений (ботом/очередью) остаётся на стороне вызывающего кода.
    """

    def __init__(
        self,
        engine: _RiskAssistantEngine,
        *,
        min_severity: str = "high",
    ) -> None:
        self._engine = engine
        # escalation threshold: "high" → только high; "medium" → medium+high и т.п.
        self._min_severity = min_severity

    def _severity_passes(self, severity: str) -> bool:
        order = {"low": 0, "medium": 1, "high": 2}
        return order.get(severity, 0) >= order.get(self._min_severity, 2)

    def evaluate_event(
        self,
        *,
        risk_input: RiskInput,
        courier_tg_id: int | None = None,
        curator_tg_id: int | None = None,
    ) -> ProactiveRiskSignal | None:
        """Evaluate delivery event and, if needed, produce a proactive signal.

        Conservative policy by default:
        - только риски с достаточной тяжестью (min_severity, по умолчанию high);
        - дополнительно опираемся на флаг escalate внутри AI-ответа.
        """
        res = self._engine.get_risk_recommendation(risk_input)
        text = getattr(res, "text", "")
        escalate = bool(getattr(res, "escalate", False))
        debug = getattr(res, "debug", {}) or {}
        risk_type = str(debug.get("risk_type") or "")
        severity = str(debug.get("severity") or "")

        if not text or not risk_type or not severity:
            return None

        if not self._severity_passes(severity) and not escalate:
            # Считаем сигнал слишком слабым для проактивного алерта.
            return None

        return ProactiveRiskSignal(
            risk_type=risk_type,
            severity=severity,
            text=text,
            escalate=escalate,
            courier_tg_id=courier_tg_id,
            curator_tg_id=curator_tg_id,
        )

