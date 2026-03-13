"""Admin commands for AI subsystem."""
from __future__ import annotations

import redis.asyncio as redis
from aiogram import Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from sqlalchemy import text

from src.bot.states import AIAddFAQStates
from src.config import get_settings
from src.core.events import AutomationEvent
from src.core.services.access_service import AccessService
from src.core.services.ai.ai_facade import AIFacade
from src.infra.db.repositories.faq_repo import FAQRepository
from src.infra.db.session import async_session_factory

from src.bot.access_guards import require_admin_for_message

router = Router(name="ai_admin")


@router.message(Command("ai_status"))
async def ai_status(
    message: Message,
    access_service: AccessService,
    ai_facade: AIFacade | None = None,
) -> None:
    if not await require_admin_for_message(message, access_service):
        return

    settings = get_settings()
    if not settings.ai_enabled:
        await message.answer("AI STATUS\nAI: disabled")
        return

    faq_count = None
    db_ok = False
    err = ""
    try:
        async with async_session_factory() as session:
            repo = FAQRepository()
            faq_count = await repo.count(session=session)
        db_ok = True
    except Exception as e:
        err = f"{type(e).__name__}: {e}"

    providers: list[str] = ai_facade.get_provider_names() if ai_facade else []

    providers_text = ", ".join(providers) if providers else "no providers enabled"
    lines = ["AI STATUS", "AI: enabled", f"Providers: {providers_text}"]
    if db_ok:
        lines.append(f"FAQ count: {faq_count if faq_count is not None else '-'}")
    else:
        lines.append("FAQ DB: FAIL")
    if err:
        lines.append(f"DB error: {err}")

    await message.answer("\n".join(lines))


@router.message(Command("status"))
async def status(
    message: Message,
    ai_facade: AIFacade | None = None,
) -> None:
    access_service: AccessService = message.conf.get("access_service")  # type: ignore[attr-defined]
    if not await require_admin_for_message(message, access_service):
        return

    settings = get_settings()

    db_ok = False
    alembic_revision = "-"
    try:
        async with async_session_factory() as session:
            await session.execute(text("SELECT 1"))
            db_ok = True
            try:
                rev_result = await session.execute(
                    text("SELECT version_num FROM alembic_version LIMIT 1")
                )
                alembic_revision = rev_result.scalar_one_or_none() or "-"
            except Exception as exc:
                alembic_revision = f"FAIL ({type(exc).__name__})"
    except Exception:
        db_ok = False
        alembic_revision = "FAIL"

    redis_ok = False
    redis_client = redis.from_url(settings.redis_url)
    try:
        redis_ok = bool(await redis_client.ping())
    except Exception:
        redis_ok = False
    finally:
        await redis_client.aclose()

    providers_count = len(ai_facade.get_provider_names()) if ai_facade else 0

    lines = [
        "STATUS",
        f"DB: {'OK' if db_ok else 'FAIL'}",
        f"Redis: {'OK' if redis_ok else 'FAIL'}",
        f"Alembic current: {alembic_revision}",
        f"AI_ENABLED: {str(settings.ai_enabled).lower()}",
        f"AI providers count: {providers_count}",
        "bot mode: polling",
    ]
    await message.answer("\n".join(lines))


@router.message(Command("ai_policy_reload"))
async def ai_policy_reload(
    message: Message,
    access_service: AccessService,
    ai_facade: AIFacade | None = None,
) -> None:
    if not await require_admin_for_message(message, access_service):
        return

    if ai_facade is None:
        await message.answer("AI сервис не инициализирован.")
        return

    try:
        ai_facade.reload_policy()
        await message.answer("Policy перезагружена.")
    except Exception as exc:
        await message.answer(f"Не удалось перезагрузить policy: {exc}")


@router.message(Command("ai_add_faq"))
async def ai_add_faq_start(message: Message, state: FSMContext) -> None:
    access_service: AccessService = message.conf.get("access_service")  # type: ignore[attr-defined]
    if not await require_admin_for_message(message, access_service):
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
        repo = FAQRepository()
        faq_id = await repo.add_faq(
            session=session,
            question=question,
            answer=answer,
            category=category,
            tag=tag,
            keywords=keywords,
            is_active=True,
        )
        await session.commit()

    event_bus = message.conf.get("event_bus")  # type: ignore[attr-defined]
    if event_bus:
        await event_bus.emit(
            AutomationEvent.FAQ_ADDED,
            {"faq_id": faq_id, "question": question, "answer": answer, "category": category, "tag": tag},
        )

    await state.clear()
    await message.answer(f"FAQ добавлен. id={faq_id}")


@router.message(Command("ai_search_faq"))
async def ai_search_faq(message: Message) -> None:
    access_service: AccessService = message.conf.get("access_service")  # type: ignore[attr-defined]
    if not await require_admin_for_message(message, access_service):
        return

    query = (message.text or "").replace("/ai_search_faq", "", 1).strip()
    if not query:
        await message.answer("Формат: /ai_search_faq <текст>")
        return

    async with async_session_factory() as session:
        repo = FAQRepository()
        found = await repo.search_hybrid(session=session, query=query, limit=5)

    if not found:
        await message.answer("Ничего не найдено.")
        return

    out = []
    for faq in found:
        short_answer = (
            faq["answer"][:160] + "..."
            if len(faq["answer"]) > 160
            else faq["answer"]
        )
        meta_parts = [f"id={faq['id']}", f"score={faq['score']:.2f}"]
        if faq.get("tag"):
            meta_parts.append(f"tag={faq['tag']}")
        if faq.get("category"):
            meta_parts.append(f"category={faq['category']}")
        out.append(
            f"- {faq['question']}\n  {' | '.join(meta_parts)}\n  A: {short_answer}"
        )
    await message.answer("\n".join(out))
