"""Тесты AIFacade: единая точка входа в AI-слой, делегирование в AICourierService."""
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.core.services.ai.ai_courier_service import AICourierResult, AICourierService
from src.core.services.ai.ai_facade import AIFacade
from src.core.services.ai.provider_router import ProviderRouter
from src.core.services.risk import RiskInput


@pytest.mark.asyncio
async def test_ai_facade_answer_user_delegates_to_courier() -> None:
    """answer_user вызывает courier.get_answer и возвращает результат."""
    expected = AICourierResult(
        text="Ответ",
        route="must_match",
        confidence=1.0,
        intent="test",
        need_clarify=False,
        clarify_question="",
        escalate=False,
        source="must_match",
    )
    mock_courier = MagicMock(spec=AICourierService)
    mock_courier.get_answer = AsyncMock(return_value=expected)
    facade = AIFacade(_courier=mock_courier, _router=None)

    result = await facade.answer_user(user_id=1, text="тест")

    mock_courier.get_answer.assert_called_once_with(user_id=1, text="тест", role="courier")
    assert result.text == "Ответ"
    assert result.route == "must_match"


@pytest.mark.asyncio
async def test_ai_facade_answer_admin_delegates_to_courier() -> None:
    """answer_admin вызывает courier.get_answer с role=admin."""
    expected = AICourierResult(
        text="Ответ админу",
        route="faq",
        confidence=0.9,
        intent="admin",
        need_clarify=False,
        clarify_question="",
        escalate=False,
        source="faq",
    )
    mock_courier = MagicMock(spec=AICourierService)
    mock_courier.get_answer = AsyncMock(return_value=expected)
    facade = AIFacade(_courier=mock_courier, _router=None)

    result = await facade.answer_admin(admin_id=2, text="вопрос")

    mock_courier.get_answer.assert_called_once_with(user_id=2, text="вопрос", role="admin")
    assert result.text == "Ответ админу"


def test_ai_facade_proactive_hint_delegates_to_courier() -> None:
    """proactive_hint вызывает courier.get_risk_recommendation."""
    expected = AICourierResult(
        text="Риск опоздания",
        route="delivery_risk",
        confidence=0.8,
        intent="late_delivery_risk",
        need_clarify=False,
        clarify_question="",
        escalate=False,
        source="delivery_risk",
    )
    mock_courier = MagicMock(spec=AICourierService)
    mock_courier.get_risk_recommendation = MagicMock(return_value=expected)
    facade = AIFacade(_courier=mock_courier, _router=None)
    risk_input = RiskInput.from_dict(
        {
            "order_id": "o1",
            "courier_id": "c1",
            "minutes_to_deadline": 10,
            "eta_minutes": 25,
            "active_orders_count": 1,
            "has_customer_comment": False,
            "address_flags": {},
            "item_flags": {},
            "zone": "",
            "tt": "",
            "event_type": "en_route",
        }
    )

    result = facade.proactive_hint(risk_input)

    mock_courier.get_risk_recommendation.assert_called_once_with(risk_input)
    assert result.route == "delivery_risk"


def test_ai_facade_get_provider_names_empty_when_no_router() -> None:
    """get_provider_names возвращает пустой список при router=None."""
    mock_courier = MagicMock(spec=AICourierService)
    facade = AIFacade(_courier=mock_courier, _router=None)
    assert facade.get_provider_names() == []


def test_ai_facade_get_provider_names_returns_router_keys() -> None:
    """get_provider_names возвращает отсортированные имена провайдеров роутера."""
    mock_courier = MagicMock(spec=AICourierService)
    mock_router = MagicMock(spec=ProviderRouter)
    mock_router.providers = {"openai": None, "groq": None}
    facade = AIFacade(_courier=mock_courier, _router=mock_router)
    assert facade.get_provider_names() == ["groq", "openai"]


def test_ai_facade_reload_policy_calls_courier() -> None:
    """reload_policy вызывает courier.reload_policy."""
    mock_courier = MagicMock(spec=AICourierService)
    facade = AIFacade(_courier=mock_courier, _router=None)
    facade.reload_policy()
    mock_courier.reload_policy.assert_called_once()
