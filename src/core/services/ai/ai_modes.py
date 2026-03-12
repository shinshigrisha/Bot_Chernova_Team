"""Три раздельных режима AI: не один «умный ответчик», а явные роли.

- Courier assistant   — ответы по кейсам доставки (куратор для курьеров).
- Admin copilot       — помощь админу: FAQ, рассылки, анализ.
- Analytics assistant — анализ CSV / xlsx / pdf / таблиц.
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
