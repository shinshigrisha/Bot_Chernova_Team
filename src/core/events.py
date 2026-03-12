"""Event system for automation / n8n: canonical event types and optional in-process bus."""

from __future__ import annotations

import asyncio
import logging
from enum import StrEnum
from typing import Any, Callable

logger = logging.getLogger(__name__)


class AutomationEvent(StrEnum):
    """Canonical events for automation webhook and in-app emission."""

    USER_QUESTION = "user_question"
    POLL_CLOSED = "poll_closed"
    COURIER_WARNING = "courier_warning"
    FAQ_ADDED = "faq_added"
    # Proactive layer
    VERIFICATION_PENDING = "verification.pending"
    HIGH_RISK_DETECTED = "high_risk_detected"
    SIMILAR_CASE_SHOWN = "similar_case_shown"


# Legacy alias for webhook payloads
EVENT_COURIER_QUESTION = "courier_question"

# Webhook-only: приходит извне, не из бота
EVENT_DELIVERY_RISK_EVAL = "delivery_risk_eval"

ALLOWED_EVENT_STRINGS = (
    {e.value for e in AutomationEvent}
    | {EVENT_COURIER_QUESTION, EVENT_DELIVERY_RISK_EVAL}
)

# Events that require AI curator (user_question / courier_question)
AI_EVENTS = {AutomationEvent.USER_QUESTION.value, EVENT_COURIER_QUESTION}


def parse_event(value: str | None) -> str | None:
    """Return canonical event string if valid, else None."""
    if not value or not isinstance(value, str):
        return None
    v = value.strip().lower()
    return v if v in ALLOWED_EVENT_STRINGS else None


class EventBus:
    """In-process async event bus: emit events for subscribers (e.g. n8n mirror, logging)."""

    def __init__(self) -> None:
        self._handlers: list[Callable[[str, dict[str, Any]], Any]] = []

    def subscribe(self, handler: Callable[[str, dict[str, Any]], Any]) -> None:
        self._handlers.append(handler)

    def unsubscribe(self, handler: Callable[[str, dict[str, Any]], Any]) -> None:
        if handler in self._handlers:
            self._handlers.remove(handler)

    async def emit(self, event: str, payload: dict[str, Any]) -> None:
        for h in self._handlers:
            try:
                out = h(event, payload)
                if asyncio.iscoroutine(out):
                    await out
            except Exception as e:
                logger.warning("event_handler_error", event=event, error=str(e))
