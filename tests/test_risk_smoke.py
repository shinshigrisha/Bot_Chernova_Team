"""Дымовые тесты пайплайна рисков: RiskEngine + RecommendationEngine."""

import pytest

from src.core.services.risk import run_risk_smoke


pytestmark = pytest.mark.smoke


def test_risk_smoke_pipeline() -> None:
    """Прогон всех smoke-сценариев risk-слоя без исключений."""
    assert run_risk_smoke() is True
