"""Proactive rule-based delivery risk layer. No integration with AI curator."""

from src.core.services.risk.features import RiskInput
from src.core.services.risk.recommendation_engine import Recommendation, RecommendationEngine
from src.core.services.risk.risk_engine import RiskEngine
from src.core.services.risk.rules import RiskResult

__all__ = [
    "Recommendation",
    "RecommendationEngine",
    "RiskInput",
    "RiskEngine",
    "RiskResult",
    "run_risk_smoke",
]


def run_risk_smoke() -> bool:
    """Дымовая проверка пайплайна RiskEngine + RecommendationEngine. См. smoke_risk_engine.run_smoke."""
    from src.core.services.risk.smoke_risk_engine import run_smoke
    return run_smoke()
