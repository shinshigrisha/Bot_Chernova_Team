"""AI chat mode handlers (/ai, /ai_off, /risk, text in AI mode)."""
from __future__ import annotations

import asyncio
import logging

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from src.bot.states import AIChatStates
from src.core.services.ai.ai_courier_service import AICourierService
from src.core.services.ai.ai_facade import AIFacade
from src.core.services.risk import RiskInput

router = Router(name="ai_chat")
logger = logging.getLogger(__name__)
_USER_LOCKS: dict[int, asyncio.Lock] = {}
_REQUEST_TIMEOUT_S = 25

# Демо-контекст для /risk: риск опоздания (ETA > дедлайн)
_DEMO_RISK_INPUT = RiskInput.from_dict({
    "order_id": "demo",
    "courier_id": "demo",
    "minutes_to_deadline": 10,
    "eta_minutes": 25,
    "active_orders_count": 1,
    "has_customer_comment": False,
    "address_flags": {},
    "item_flags": {},
    "zone": "center",
    "tt": "12:00",
    "event_type": "en_route",
})


@router.message(Command("risk"))
async def risk_recommendation(
    message: Message,
    ai_facade: AIFacade | None = None,
    ai_service: AICourierService | None = None,
) -> None:
    """Проактивная рекомендация по риску доставки (risk_engine + recommendation_engine)."""
    engine = ai_facade or ai_service
    if engine is None:
        await message.answer("AI сервис не инициализирован. Проверь запуск.")
        return
    try:
        res = engine.get_risk_recommendation(_DEMO_RISK_INPUT)
        text = getattr(res, "text", str(res))
        await message.answer(text)
        logger.info("risk_recommendation sent user_id=%s route=%s", message.from_user.id if message.from_user else 0, getattr(res, "route", ""))
    except Exception:
        logger.exception("risk_recommendation_failed")
        await message.answer("Не удалось получить рекомендацию по риску. Попробуйте позже.")


@router.message(Command("ai"))
async def ai_on(message: Message, state: FSMContext) -> None:
    await state.set_state(AIChatStates.active)
    await message.answer("AI-режим включен. Пишите вопрос, /ai_off — выключить.")


@router.message(Command("ai_off"))
async def ai_off(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer("AI-режим выключен.")


@router.message(AIChatStates.active, F.text)
async def ai_chat_handler(
    message: Message,
    state: FSMContext,
    ai_facade: AIFacade | None = None,
    ai_service: AICourierService | None = None,
) -> None:
    text = (message.text or "").strip()
    if not text:
        return

    engine = ai_facade or ai_service
    if engine is None:
        await message.answer("AI сервис не инициализирован. Проверь запуск.")
        return

    user_id = message.from_user.id if message.from_user else 0
    lock = _USER_LOCKS.setdefault(user_id, asyncio.Lock())

    if lock.locked():
        await message.answer("Запрос уже обрабатывается. Дождитесь ответа.")
        return

    async with lock:
        try:
            res = await asyncio.wait_for(
                engine.get_answer(user_id=user_id, text=text),
                timeout=_REQUEST_TIMEOUT_S,
            )
            answer_text = getattr(res, "text", str(res))
            route = getattr(res, "route", "unknown")
            debug = getattr(res, "debug", {}) or {}
            provider = debug.get("provider", "unknown")
            logger.info(
                "ai_chat_response user_id=%s route=%s provider=%s question=%r",
                user_id,
                route,
                provider,
                text,
            )
            await message.answer(answer_text)
        except asyncio.TimeoutError:
            logger.warning("ai_chat_timeout user_id=%s question=%r", user_id, text)
            await message.answer(
                "Ответ формируется слишком долго. Попробуйте переформулировать вопрос короче."
            )
        except Exception:
            logger.exception("ai_chat_failed user_id=%s", user_id)
            await message.answer(
                "Произошла ошибка при обработке AI-запроса. Попробуйте еще раз."
            )
