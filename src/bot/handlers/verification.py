from __future__ import annotations

import asyncio

from aiogram import F, Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from src.bot.keyboards.verification import (
    CONFIRM_NO_CB,
    CONFIRM_YES_CB,
    ROLE_COURIER_CB,
    ROLE_CURATOR_CB,
    VERIFICATION_CB_PREFIX,
    build_confirmation_keyboard,
    build_registration_entry_keyboard,
    build_role_choice_keyboard,
)
from src.bot.states_verification import VerificationStates
from src.core.events import AutomationEvent
from src.core.services.darkstores import resolve_ds_code_for_tt
from src.core.services.verification_service import (
    VerificationApplicationPayload,
    VerificationService,
)
from src.infra.db.enums import UserRole
from src.infra.n8n.verification_mirror import notify_verification_pending


router = Router(name="verification")

@router.callback_query(F.data == f"{VERIFICATION_CB_PREFIX}start")
async def verification_start(callback: CallbackQuery, state: FSMContext) -> None:
    """Entry point: user pressed 'Регистрация'."""
    await state.set_state(VerificationStates.choose_role)
    await callback.message.answer(
        "Выберите вашу роль. В любой момент можно отменить: напишите «отмена» или «cancel».",
        reply_markup=build_role_choice_keyboard(),
    )
    await callback.answer()


@router.message(
    StateFilter(VerificationStates),
    F.text,
    F.text.lower().in_({"отмена", "cancel"}),
)
async def verification_cancel_by_text(message: Message, state: FSMContext) -> None:
    """Отмена регистрации по тексту (legacy UX)."""
    await state.clear()
    await message.answer(
        "Регистрация отменена.",
        reply_markup=build_registration_entry_keyboard(),
    )


@router.callback_query(F.data.in_({ROLE_COURIER_CB, ROLE_CURATOR_CB}))
async def verification_choose_role(callback: CallbackQuery, state: FSMContext) -> None:
    role = UserRole.COURIER if callback.data == ROLE_COURIER_CB else UserRole.CURATOR
    await state.update_data(role=role.value)
    await state.set_state(VerificationStates.first_name)
    await callback.message.answer("Введите ваше имя:")
    await callback.answer()


@router.message(VerificationStates.first_name)
async def verification_first_name(message: Message, state: FSMContext) -> None:
    text = (message.text or "").strip()
    if not text:
        await message.answer("Имя не может быть пустым. Попробуйте ещё раз.")
        return
    await state.update_data(first_name=text)
    await state.set_state(VerificationStates.last_name)
    await message.answer("Введите вашу фамилию:")


@router.message(VerificationStates.last_name)
async def verification_last_name(message: Message, state: FSMContext) -> None:
    text = (message.text or "").strip()
    if not text:
        await message.answer("Фамилия не может быть пустой. Попробуйте ещё раз.")
        return
    await state.update_data(last_name=text)
    await state.set_state(VerificationStates.tt_number)
    await message.answer("Введите номер ТТ (торговой точки):")


@router.message(VerificationStates.tt_number)
async def verification_tt_number(message: Message, state: FSMContext) -> None:
    text = (message.text or "").strip()
    if not text:
        await message.answer("Номер ТТ не может быть пустым. Попробуйте ещё раз.")
        return
    if not text.isdigit():
        await message.answer("Номер ТТ должен содержать только цифры. Попробуйте ещё раз.")
        return

    ds_code = resolve_ds_code_for_tt(text)
    if ds_code is None:
        await message.answer(
            "Не удалось найти даркстор для указанного номера ТТ.\n"
            "Проверьте номер и попробуйте ещё раз."
        )
        return

    await state.update_data(tt_number=text, ds_code=ds_code)
    await state.set_state(VerificationStates.phone)
    await message.answer("Введите номер телефона:")


@router.message(VerificationStates.phone)
async def verification_phone(message: Message, state: FSMContext) -> None:
    text = (message.text or "").strip()
    if not text:
        await message.answer("Телефон не может быть пустым. Попробуйте ещё раз.")
        return
    await state.update_data(phone=text)
    data = await state.get_data()
    role = data.get("role")
    first_name = data.get("first_name")
    last_name = data.get("last_name")
    tt_number = data.get("tt_number")
    ds_code = data.get("ds_code")
    phone = data.get("phone")
    summary = (
        "Проверьте данные заявки:\n"
        f"- Роль: {role}\n"
        f"- Имя: {first_name}\n"
        f"- Фамилия: {last_name}\n"
        f"- ТТ: {tt_number}\n"
        f"- Даркстор (ДС): {ds_code}\n"
        f"- Телефон: {phone}\n"
    )
    await state.set_state(VerificationStates.confirm)
    await message.answer(summary, reply_markup=build_confirmation_keyboard())


@router.callback_query(F.data == CONFIRM_NO_CB)
async def verification_edit(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(VerificationStates.first_name)
    await callback.message.answer("Ок, давайте начнём заново. Введите ваше имя:")
    await callback.answer()


@router.callback_query(F.data == CONFIRM_YES_CB)
async def verification_confirm(
    callback: CallbackQuery,
    state: FSMContext,
    event_bus=None,
    verification_service: VerificationService | None = None,
) -> None:
    tg_user_id = callback.from_user.id if callback.from_user else 0
    data = await state.get_data()
    role_value = data.get("role", UserRole.COURIER.value)
    role = UserRole(role_value) if role_value in {r.value for r in UserRole} else UserRole.COURIER

    payload = VerificationApplicationPayload(
        tg_user_id=tg_user_id,
        role=role,
        first_name=data.get("first_name", ""),
        last_name=data.get("last_name", ""),
        tt_number=data.get("tt_number", ""),
        ds_code=data.get("ds_code", ""),
        phone=data.get("phone", ""),
    )

    if not verification_service:
        await callback.message.answer("Сервис регистрации временно недоступен. Попробуйте позже.")
        await callback.answer()
        return
    await verification_service.create_application_and_mark_pending(payload)

    # Optional n8n mirror (fire-and-forget; behind N8N_VERIFICATION_MIRROR_ENABLED)
    asyncio.create_task(notify_verification_pending(payload))

    # Проактивный слой: эмит для подписчиков (логи, n8n mirror и т.д.)
    if event_bus:
        await event_bus.emit(
            AutomationEvent.VERIFICATION_PENDING,
            {
                "tg_user_id": payload.tg_user_id,
                "role": payload.role.value,
                "first_name": payload.first_name,
                "last_name": payload.last_name,
                "tt_number": payload.tt_number,
                "ds_code": payload.ds_code,
                "phone": payload.phone,
            },
        )

    await state.clear()
    await callback.message.answer(
        "Заявка на регистрацию отправлена. Ваш статус: pending. "
        "После проверки вам обновят статус.",
    )
    await callback.answer()

