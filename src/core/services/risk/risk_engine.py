"""Proactive risk engine: runs rule-based evaluators and returns top risk."""

from __future__ import annotations

from src.core.services.risk.features import RiskInput
from src.core.services.risk.rules import ALL_RULES, RiskResult


class RiskEngine:
    """Rule-based delivery risk evaluation. Does not depend on AI curator."""

    def evaluate(self, inp: RiskInput) -> RiskResult | None:
        """Run all rules and return the single highest-severity risk (by score)."""
        results: list[RiskResult] = []
        for rule_fn in ALL_RULES:
            r = rule_fn(inp)
            if r is not None:
                results.append(r)
        if not results:
            return None
        severity_order = {"high": 2, "medium": 1, "low": 0}
        results.sort(
            key=lambda x: (severity_order.get(x.severity, 0), x.risk_score),
            reverse=True,
        )
        return results[0]
