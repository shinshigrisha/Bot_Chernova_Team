"""HTTP endpoint for n8n automation: POST /automation/event → event system + AI curator."""

from __future__ import annotations

import logging
from typing import Any

from aiohttp import web

from aiogram import Dispatcher
from src.core.events import (
    AI_EVENTS,
    EVENT_DELIVERY_RISK_EVAL,
    AutomationEvent,
    parse_event,
)
from src.core.services.ai.ai_facade import AIFacade
from src.core.services.risk import RiskInput

logger = logging.getLogger(__name__)


async def _handle_automation_event(request: web.Request) -> web.Response:
    """POST /automation/event — validate event, route user_question to AI curator, return JSON."""
    try:
        body = await request.json()
    except Exception as e:
        logger.warning("automation_event_invalid_json", error=str(e))
        return web.json_response(
            {"ok": False, "error": "invalid_json", "message": "Invalid JSON body"},
            status=400,
        )

    event = parse_event(body.get("event"))
    if not event:
        return web.json_response(
            {
                "ok": False,
                "error": "validation",
                "message": "event is required and must be one of: user_question, poll_closed, courier_warning, faq_added, courier_question, delivery_risk_eval",
            },
            status=400,
        )

    user_id_raw = body.get("user_id")
    text = (body.get("text") or "").strip()

    try:
        user_id = int(user_id_raw) if user_id_raw is not None else None
    except (TypeError, ValueError):
        return web.json_response(
            {"ok": False, "error": "validation", "message": "user_id must be an integer"},
            status=400,
        )

    # AI events: require text and user_id, call curator
    if event in AI_EVENTS:
        if not text:
            return web.json_response(
                {"ok": False, "error": "validation", "message": "text is required for user_question/courier_question"},
                status=400,
            )
        if user_id is None:
            return web.json_response(
                {"ok": False, "error": "validation", "message": "user_id is required for user_question/courier_question"},
                status=400,
            )

        dp: Dispatcher | None = request.app.get("dp")
        if not dp:
            return web.json_response(
                {"ok": False, "error": "config", "message": "Automation not configured"},
                status=503,
            )
        ai_facade: AIFacade | None = dp.get("ai_facade")
        if not ai_facade:
            return web.json_response(
                {"ok": False, "error": "config", "message": "AI curator not available"},
                status=503,
            )

        try:
            result = await ai_facade.answer_user(user_id=user_id, text=text)
        except Exception as e:
            logger.exception("automation_event_ai_error", user_id=user_id, error=str(e))
            return web.json_response(
                {"ok": False, "error": "ai_error", "message": "AI curator failed"},
                status=500,
            )

        payload = {
            "ok": True,
            "event": event,
            "user_id": user_id,
            "text": result.text,
            "route": result.route,
            "intent": result.intent,
            "confidence": result.confidence,
            "source": getattr(result, "source", ""),
            "needs_escalation": result.needs_escalation,
            "needs_clarification": result.needs_clarification,
        }
        if result.evidence:
            payload["evidence"] = result.evidence
        return web.json_response(payload)

    # delivery_risk_eval: оценка риска доставки, при высоком риске — hint для проактивной подсказки
    if event == EVENT_DELIVERY_RISK_EVAL:
        dp = request.app.get("dp")
        ai_facade = dp.get("ai_facade") if dp else None
        if not ai_facade:
            return web.json_response(
                {"ok": False, "error": "config", "message": "AI curator not available"},
                status=503,
            )
        try:
            risk_input = RiskInput.from_dict(body)
        except (TypeError, ValueError) as e:
            return web.json_response(
                {"ok": False, "error": "validation", "message": str(e)},
                status=400,
            )
        result = ai_facade.proactive_hint(risk_input)
        debug = getattr(result, "debug", {}) or {}
        severity = debug.get("severity", "")
        risk_type = debug.get("risk_type", "")
        escalate = getattr(result, "escalate", False)
        if severity == "high" or escalate:
            event_bus = dp.get("event_bus") if dp else None
            if event_bus:
                try:
                    await event_bus.emit(
                        AutomationEvent.HIGH_RISK_DETECTED,
                        {
                            "courier_tg_id": body.get("courier_tg_id"),
                            "risk_type": risk_type,
                            "severity": severity,
                            "hint": result.text,
                            "escalate": escalate,
                            "order_id": risk_input.order_id,
                        },
                    )
                except Exception as emit_err:
                    logger.warning("high_risk_emit_failed", error=str(emit_err))
        return web.json_response({
            "ok": True,
            "event": event,
            "hint": result.text,
            "severity": severity,
            "risk_type": risk_type,
            "escalate": escalate,
            "courier_tg_id": body.get("courier_tg_id"),
        })

    # Non-AI events: acknowledge, optional user_id/text in response
    return web.json_response({
        "ok": True,
        "event": event,
        "user_id": user_id,
        "text": text or None,
    })


def create_automation_app(dp: Dispatcher) -> web.Application:
    """Create aiohttp app with POST /automation/event, using dp for AI facade."""
    app = web.Application()
    app["dp"] = dp
    app.router.add_post("/automation/event", _handle_automation_event)
    return app
