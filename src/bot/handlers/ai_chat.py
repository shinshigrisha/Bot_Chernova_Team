"""AI chat mode handlers (/ai, /ai_off, text in AI mode)."""
from __future__ import annotations

import asyncio
import logging

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from src.bot.states import AIChatStates

router = Router(name="ai_chat")
logger = logging.getLogger(__name__)
_USER_LOCKS: dict[int, asyncio.Lock] = {}
_REQUEST_TIMEOUT_S = 25


@router.message(Command("ai"))
async def ai_on(message: Message, state: FSMContext) -> None:
    await state.set_state(AIChatStates.active)
    await message.answer("AI-режим включен. Пишите вопрос, /ai_off — выключить.")


@router.message(Command("ai_off"))
async def ai_off(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer("AI-режим выключен.")


@router.message(AIChatStates.active, F.text)
async def ai_chat_handler(message: Message, state: FSMContext, ai_service=None) -> None:
    text = (message.text or "").strip()
    if not text:
        return

    if ai_service is None:
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
                ai_service.get_answer(user_id=user_id, text=text),
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
