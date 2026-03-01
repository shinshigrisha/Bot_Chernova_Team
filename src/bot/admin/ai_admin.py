"""Admin commands for AI subsystem."""
from __future__ import annotations

import os
from uuid import uuid4

from aiogram import Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from src.bot.states import AIAddFAQStates
from src.infra.db.repositories.faq_ai import FAQAIRepository
from src.infra.db.session import async_session_factory

router = Router(name="ai_admin")


def _is_admin(user_id: int) -> bool:
    raw = os.getenv("ADMIN_USER_ID", "").strip()
    if not raw:
        return False
    try:
        return int(raw) == int(user_id)
    except ValueError:
        return False


async def _require_admin(message: Message) -> bool:
    uid = message.from_user.id if message.from_user else 0
    if not _is_admin(uid):
        await message.answer("Нет доступа.")
        return False
    return True


@router.message(Command("ai_status"))
async def ai_status(message: Message) -> None:
    if not await _require_admin(message):
        return

    faq_count = None
    db_ok = False
    err = ""
    try:
        async with async_session_factory() as session:
            repo = FAQAIRepository()
            faq_count = await repo.count(session)
        db_ok = True
    except Exception as e:
        err = f"{type(e).__name__}: {e}"

    ai_router = message.bot.get("ai_router")
    providers: list[str] = []
    if ai_router and getattr(ai_router, "providers", None):
        providers = sorted(ai_router.providers.keys())

    lines = [
        "AI STATUS",
        f"DB: {'OK' if db_ok else 'FAIL'}",
        f"FAQ count: {faq_count if faq_count is not None else '-'}",
        f"Providers: {', '.join(providers) if providers else '(no providers enabled)'}",
    ]
    if err:
        lines.append(f"DB error: {err}")

    await message.answer("\n".join(lines))


@router.message(Command("ai_policy_reload"))
async def ai_policy_reload(message: Message) -> None:
    if not await _require_admin(message):
        return

    ai_service = message.bot.get("ai_service")
    if ai_service is None:
        await message.answer("AI сервис не инициализирован.")
        return

    try:
        ai_service.reload_policy()
        await message.answer("Policy перезагружена.")
    except Exception as exc:
        await message.answer(f"Не удалось перезагрузить policy: {exc}")


@router.message(Command("ai_add_faq"))
async def ai_add_faq_start(message: Message, state: FSMContext) -> None:
    if not await _require_admin(message):
        return
    await state.set_state(AIAddFAQStates.question)
    await message.answer("Шаг 1/5. Введите question:")


@router.message(AIAddFAQStates.question)
async def ai_add_faq_question(message: Message, state: FSMContext) -> None:
    await state.update_data(question=(message.text or "").strip())
    await state.set_state(AIAddFAQStates.answer)
    await message.answer("Шаг 2/5. Введите answer:")


@router.message(AIAddFAQStates.answer)
async def ai_add_faq_answer(message: Message, state: FSMContext) -> None:
    await state.update_data(answer=(message.text or "").strip())
    await state.set_state(AIAddFAQStates.category)
    await message.answer("Шаг 3/5. Введите category (или '-' если пусто):")


@router.message(AIAddFAQStates.category)
async def ai_add_faq_category(message: Message, state: FSMContext) -> None:
    category = (message.text or "").strip()
    await state.update_data(category=None if category == "-" else category)
    await state.set_state(AIAddFAQStates.tag)
    await message.answer("Шаг 4/5. Введите tag (или '-' если пусто):")


@router.message(AIAddFAQStates.tag)
async def ai_add_faq_tag(message: Message, state: FSMContext) -> None:
    tag = (message.text or "").strip()
    await state.update_data(tag=None if tag == "-" else tag)
    await state.set_state(AIAddFAQStates.keywords)
    await message.answer("Шаг 5/5. Введите keywords через запятую (или '-' если пусто):")


@router.message(AIAddFAQStates.keywords)
async def ai_add_faq_keywords(message: Message, state: FSMContext) -> None:
    raw = (message.text or "").strip()
    keywords = [] if raw == "-" else [x.strip() for x in raw.split(",") if x.strip()]
    data = await state.get_data()
    question = data.get("question", "")
    answer = data.get("answer", "")
    category = data.get("category")
    tag = data.get("tag")

    if not question or not answer:
        await state.clear()
        await message.answer("Question/answer обязательны. Начните заново: /ai_add_faq")
        return

    async with async_session_factory() as session:
        repo = FAQAIRepository()
        merged_tags: list[str] = []
        if category:
            merged_tags.append(f"category:{category}")
        if tag:
            merged_tags.append(f"tag:{tag}")
        merged_tags.extend(keywords)
        faq_id = f"manual_{uuid4().hex[:10]}"
        await repo.upsert(
            session=session,
            faq_id=faq_id,
            q=question,
            a=answer,
            tags=merged_tags,
        )
        await session.commit()

    await state.clear()
    await message.answer(f"FAQ добавлен. id={faq_id}")


@router.message(Command("ai_search_faq"))
async def ai_search_faq(message: Message) -> None:
    if not await _require_admin(message):
        return

    query = (message.text or "").replace("/ai_search_faq", "", 1).strip()
    if not query:
        await message.answer("Формат: /ai_search_faq <текст>")
        return

    async with async_session_factory() as session:
        repo = FAQAIRepository()
        found = await repo.search(session=session, text=query, top_k=5)

    if not found:
        await message.answer("Ничего не найдено.")
        return

    out = []
    for f in found:
        short_a = (f["a"][:160] + "...") if len(f["a"]) > 160 else f["a"]
        out.append(f"- {f['q']}\n  A: {short_a}")
    await message.answer("\n".join(out))
