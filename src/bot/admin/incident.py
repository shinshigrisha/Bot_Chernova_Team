"""FSM: Incident (shift log) flow."""
from uuid import UUID

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from src.bot.states import IncidentStates
from src.core.services.shift_log import ShiftLogService
from src.infra.db.enums import Severity
from src.infra.db.repositories.darkstores import DarkstoreRepository
from src.infra.db.repositories.users import UserRepository
from src.infra.db.session import async_session_factory

router = Router(name="admin_incident")
ADMIN_CB_PREFIX = "admin:"


@router.callback_query(F.data == f"{ADMIN_CB_PREFIX}journal")
async def start_incident(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await state.set_state(IncidentStates.darkstore_code)
    await callback.message.answer("Введите код тёмного магазина (ДС):")
    await callback.answer()


@router.message(IncidentStates.darkstore_code, F.text)
async def incident_darkstore(message: Message, state: FSMContext) -> None:
    code = (message.text or "").strip()
    async with async_session_factory() as session:
        repo = DarkstoreRepository(session)
        ds = await repo.get_by_code(code)
        await session.commit()
    if not ds:
        await message.answer("ДС с таким кодом не найден. Введите код снова:")
        return
    await state.update_data(darkstore_id=str(ds.id))
    await state.set_state(IncidentStates.severity)
    await message.answer(
        "Введите степень серьёзности: low, medium, high, critical"
    )


@router.message(IncidentStates.severity, F.text)
async def incident_severity(message: Message, state: FSMContext) -> None:
    raw = (message.text or "").strip().lower()
    try:
        severity = Severity(raw)
    except ValueError:
        await message.answer("Укажите: low, medium, high или critical")
        return
    await state.update_data(severity=severity.value)
    await state.set_state(IncidentStates.title)
    await message.answer("Введите заголовок инцидента:")


@router.message(IncidentStates.title, F.text)
async def incident_title(message: Message, state: FSMContext) -> None:
    await state.update_data(title=(message.text or "").strip())
    await state.set_state(IncidentStates.details)
    await message.answer("Введите описание (или /skip):")


@router.message(IncidentStates.details, F.text)
async def incident_details(message: Message, state: FSMContext) -> None:
    details = (message.text or "").strip()
    if details == "/skip":
        details = ""
    await state.update_data(details=details)
    await state.set_state(IncidentStates.confirm)
    data = await state.get_data()
    text = (
        f"Подтвердите запись в журнал смены:\n"
        f"ДС: {data.get('darkstore_id')}\n"
        f"Серьёзность: {data.get('severity')}\n"
        f"Заголовок: {data.get('title')}\n"
        f"Описание: {data.get('details') or '—'}"
    )
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    builder = InlineKeyboardBuilder()
    builder.button(text="Подтвердить", callback_data="inc_confirm:yes")
    builder.button(text="Отмена", callback_data="inc_confirm:no")
    await message.answer(text, reply_markup=builder.as_markup())


@router.callback_query(F.data == "inc_confirm:yes", IncidentStates.confirm)
async def incident_confirm_yes(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    darkstore_id = UUID(data["darkstore_id"])
    severity = Severity(data["severity"])
    title = data["title"]
    details = data.get("details") or None
    user_id = None
    if callback.from_user:
        async with async_session_factory() as session:
            repo = UserRepository(session)
            user = await repo.get_by_tg_id(callback.from_user.id)
            await session.commit()
            if user:
                user_id = user.id
    service = ShiftLogService()
    entry_id = await service.create_incident(
        darkstore_id=darkstore_id,
        severity=severity,
        title=title,
        details=details,
        user_id=user_id,
    )
    await callback.message.answer(f"Записано в журнал смены. ID: {entry_id}")
    await state.clear()
    await callback.answer()


@router.callback_query(F.data == "inc_confirm:no", IncidentStates.confirm)
async def incident_confirm_no(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await callback.message.answer("Отменено.")
    await callback.answer()
