"""Три раздельных режима AI и классы маршрутов (route classes).

- AIMode: Courier assistant / Admin copilot / Analytics assistant.
- AirRouteClass: no_llm | fast_chat | reasoning | analytics | fallback — для маршрутизации и запрета LLM в критических флоу.
"""
from __future__ import annotations

from enum import Enum


class AIMode(str, Enum):
    """Режим работы AI. Каждый режим — отдельная зона ответственности."""

    COURIER_ASSISTANT = "courier_assistant"
    """Courier assistant: ответы по кейсам доставки (must_match, rules, FAQ, ML, LLM)."""

    ADMIN_COPILOT = "admin_copilot"
    """Admin copilot: помощь админу — FAQ, рассылки, анализ, подсказки по админке."""

    ANALYTICS_ASSISTANT = "analytics_assistant"
    """Analytics assistant: анализ CSV / xlsx / pdf / таблиц, отчёты по метрикам."""


class AirRouteClass(str, Enum):
    """Класс маршрута ответа: определяет, использовался ли LLM и тип контура.

    Menu/access/verification/navigation никогда не должны вызывать LLM;
    при необходимости только no_llm или детерминистские правила.
    """

    NO_LLM = "no_llm"
    """Ответ без вызова LLM: must_match, case_engine, faq, semantic_faq, semantic_case, safety_blocker."""

    FAST_CHAT = "fast_chat"
    """Быстрый ответ (FAQ/правила с минимальным контекстом)."""

    REASONING = "reasoning"
    """Использован LLM для рассуждения/форматирования (llm_reason)."""

    ANALYTICS = "analytics"
    """Аналитический контур (Analytics assistant)."""

    FALLBACK = "fallback"
    """Эскалация или запасной ответ при недоступности/низкой уверенности."""


# Маппинг route (строка из AICourierResult.route) -> класс маршрута
ROUTE_TO_CLASS: dict[str, AirRouteClass] = {
    "safety_blocker": AirRouteClass.NO_LLM,
    "must_match": AirRouteClass.NO_LLM,
    "case_engine": AirRouteClass.NO_LLM,
    "faq": AirRouteClass.NO_LLM,
    "semantic_faq": AirRouteClass.NO_LLM,
    "semantic_case": AirRouteClass.NO_LLM,
    "structured_faq": AirRouteClass.FAST_CHAT,
    "llm_reason": AirRouteClass.REASONING,
    "fallback": AirRouteClass.FALLBACK,
    "delivery_risk": AirRouteClass.NO_LLM,
}


def route_class(route: str) -> AirRouteClass:
    """Вернуть класс маршрута по строке route из AICourierResult."""
    return ROUTE_TO_CLASS.get(route, AirRouteClass.FALLBACK)
