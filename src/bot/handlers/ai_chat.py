"""AI chat mode handlers (/ai, /ai_off, /risk, text in AI mode, AI-куратор из меню)."""
from __future__ import annotations

import asyncio
import logging

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from src.bot.keyboards.ai_curator import (
    AI_CURATOR_CB_PREFIX,
    AI_CURATOR_OTHER,
    QUICK_CASE_LABELS,
    build_ai_curator_back_keyboard,
    build_ai_curator_intro_keyboard,
)
from src.bot.navigation import ROOT_AI_CURATOR
from src.bot.states import AIChatStates
from src.config import get_settings
from src.core.events import AutomationEvent
from src.core.services.access_service import AccessService
from src.core.services.ai.ai_facade import AIFacade
from src.core.services.risk import RiskInput
from src.infra.db.enums import UserRole

router = Router(name="ai_chat")
logger = logging.getLogger(__name__)
_USER_LOCKS: dict[int, asyncio.Lock] = {}
_REQUEST_TIMEOUT_S = 25

# Текст приветствия AI-куратора
_AI_CURATOR_INTRO = (
    "🤖 **AI-куратор**\n\n"
    "Опишите проблему с доставкой — подскажу шаги по регламенту.\n\n"
    "Выберите типовой кейс или напишите свой вопрос текстом."
)

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
) -> None:
    """Проактивная рекомендация по риску доставки (risk_engine + recommendation_engine)."""
    if ai_facade is None:
        await message.answer("AI сервис не инициализирован. Проверь запуск.")
        return
    try:
        res = ai_facade.proactive_hint(_DEMO_RISK_INPUT)
        text = getattr(res, "text", str(res))
        await message.answer(text)
        logger.info("risk_recommendation sent user_id=%s route=%s", message.from_user.id if message.from_user else 0, getattr(res, "route", ""))
    except Exception:
        logger.exception("risk_recommendation_failed")
        await message.answer("Не удалось получить рекомендацию по риску. Попробуйте позже.")


@router.callback_query(F.data == ROOT_AI_CURATOR)
async def ai_curator_entry(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    """Вход в AI-куратор из меню: интро + быстрые кейсы."""
    await state.set_state(AIChatStates.active)
    await state.update_data(entry_from_curator=True)
    await callback.message.answer(
        _AI_CURATOR_INTRO,
        reply_markup=build_ai_curator_intro_keyboard(),
    )
    await callback.answer()


@router.callback_query(F.data == AI_CURATOR_OTHER)
async def ai_curator_other(callback: CallbackQuery, state: FSMContext) -> None:
    """Кейс «Другое»: пользователь введёт текст сам; кнопка «Назад в меню» доступна."""
    await callback.message.answer(
        "Опишите вашу проблему в следующем сообщении — дам рекомендации по регламенту.",
        reply_markup=build_ai_curator_back_keyboard(),
    )
    await callback.answer()


def _ai_role_for_user(principal) -> str:
    """Роль для пайплайна AI: admin/lead → 'admin', иначе 'courier'."""
    if principal and getattr(principal, "role", None) in (UserRole.ADMIN, UserRole.LEAD):
        return "admin"
    return "courier"


async def _ai_answer(ai_facade: AIFacade, user_id: int, text: str, role: str):
    """Единая точка вызова AI: answer_admin для админа при ENABLE_AI_CHAT_V2, иначе answer_user."""
    settings = get_settings()
    if getattr(settings, "enable_ai_chat_v2", False) and role == "admin":
        return await ai_facade.answer_admin(admin_id=user_id, text=text)
    return await ai_facade.answer_user(user_id=user_id, text=text)


@router.callback_query(F.data.startswith(AI_CURATOR_CB_PREFIX))
async def ai_curator_quick_case(
    callback: CallbackQuery,
    state: FSMContext,
    ai_facade: AIFacade | None = None,
    access_service: AccessService | None = None,
    event_bus=None,
) -> None:
    """Обработка быстрого кейса: запрос в AI, ответ + кнопка «Назад в меню»."""
    if ai_facade is None:
        await callback.message.answer("AI сервис не инициализирован. Проверь запуск.")
        await callback.answer()
        return

    raw = callback.data or ""
    key = raw.replace(AI_CURATOR_CB_PREFIX, "", 1).strip()
    text = QUICK_CASE_LABELS.get(key)
    if not text:
        await callback.answer()
        return

    user_id = callback.from_user.id if callback.from_user else 0
    role = "courier"
    if access_service:
        try:
            principal = await access_service.get_principal(user_id)
            role = _ai_role_for_user(principal)
        except Exception:
            pass
    lock = _USER_LOCKS.setdefault(user_id, asyncio.Lock())
    if lock.locked():
        await callback.message.answer("Запрос уже обрабатывается. Дождитесь ответа.")
        await callback.answer()
        return

    async with lock:
        try:
            res = await asyncio.wait_for(
                _ai_answer(ai_facade, user_id, text, role),
                timeout=_REQUEST_TIMEOUT_S,
            )
            answer_text = getattr(res, "text", str(res))
            route = getattr(res, "route", "")
            logger.info(
                "ai_curator_quick_case user_id=%s key=%s route=%s",
                user_id,
                key,
                route,
            )
            if route == "semantic_case" and event_bus:
                evidence = getattr(res, "evidence", []) or []
                await event_bus.emit(
                    AutomationEvent.SIMILAR_CASE_SHOWN,
                    {
                        "user_id": user_id,
                        "evidence": evidence,
                        "text_preview": (answer_text or "")[:300],
                        "intent": getattr(res, "intent", ""),
                    },
                )
            await callback.message.answer(
                answer_text,
                reply_markup=build_ai_curator_back_keyboard(),
            )
        except asyncio.TimeoutError:
            await callback.message.answer(
                "Ответ формируется слишком долго. Попробуйте ещё раз или опишите короче.",
                reply_markup=build_ai_curator_back_keyboard(),
            )
        except Exception:
            logger.exception("ai_curator_quick_case_failed user_id=%s key=%s", user_id, key)
            await callback.message.answer(
                "Произошла ошибка. Попробуйте ещё раз или опишите проблему текстом.",
                reply_markup=build_ai_curator_back_keyboard(),
            )
    await callback.answer()


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
    access_service: AccessService | None = None,
    event_bus=None,
) -> None:
    text = (message.text or "").strip()
    if not text:
        return

    if ai_facade is None:
        await message.answer("AI сервис не инициализирован. Проверь запуск.")
        return

    data = await state.get_data()
    entry_from_curator = data.get("entry_from_curator", False)
    nav_kw: dict = {}
    if entry_from_curator:
        nav_kw["reply_markup"] = build_ai_curator_back_keyboard()

    user_id = message.from_user.id if message.from_user else 0
    role = "courier"
    if access_service:
        try:
            principal = await access_service.get_principal(user_id)
            role = _ai_role_for_user(principal)
        except Exception:
            pass
    lock = _USER_LOCKS.setdefault(user_id, asyncio.Lock())

    if lock.locked():
        await message.answer("Запрос уже обрабатывается. Дождитесь ответа.", **nav_kw)
        return

    async with lock:
        try:
            res = await asyncio.wait_for(
                _ai_answer(ai_facade, user_id, text, role),
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
            # Проактивный слой: при ответе по похожему кейсу — эмит для памятки/аналитики
            if route == "semantic_case" and event_bus:
                evidence = getattr(res, "evidence", []) or []
                await event_bus.emit(
                    AutomationEvent.SIMILAR_CASE_SHOWN,
                    {
                        "user_id": user_id,
                        "evidence": evidence,
                        "text_preview": answer_text[:300] if answer_text else "",
                        "intent": getattr(res, "intent", ""),
                    },
                )
            await message.answer(answer_text, **nav_kw)
        except asyncio.TimeoutError:
            logger.warning("ai_chat_timeout user_id=%s question=%r", user_id, text)
            await message.answer(
                "Ответ формируется слишком долго. Попробуйте переформулировать вопрос короче.",
                **nav_kw,
            )
        except Exception:
            logger.exception("ai_chat_failed user_id=%s", user_id)
            await message.answer(
                "Произошла ошибка при обработке AI-запроса. Попробуйте еще раз.",
                **nav_kw,
            )
