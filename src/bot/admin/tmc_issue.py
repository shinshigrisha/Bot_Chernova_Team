"""FSM: TMC issue flow."""
from uuid import UUID

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder

from src.bot.states import TMCIssueStates
from src.core.domain.exceptions import AssetAlreadyAssignedError
from src.core.services.assets import AssetsService
from src.infra.db.enums import AssetCondition, AssetType
from src.infra.db.repositories.assets import AssetsRepository
from src.infra.db.repositories.darkstores import DarkstoreRepository
from src.infra.db.session import async_session_factory

router = Router(name="admin_tmc")
ADMIN_CB_PREFIX = "admin:"


@router.callback_query(F.data == f"{ADMIN_CB_PREFIX}tmc")
async def start_tmc_issue(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await state.set_state(TMCIssueStates.darkstore_code)
    await callback.message.answer("Введите код тёмного магазина (ДС):")
    await callback.answer()


@router.message(TMCIssueStates.darkstore_code, F.text)
async def tmc_darkstore(message: Message, state: FSMContext) -> None:
    code = (message.text or "").strip()
    async with async_session_factory() as session:
        repo = DarkstoreRepository(session)
        ds = await repo.get_by_code(code)
        await session.commit()
    if not ds:
        await message.answer("ДС с таким кодом не найден. Введите код снова:")
        return
    await state.update_data(darkstore_id=str(ds.id))
    await state.set_state(TMCIssueStates.courier_key)
    await message.answer("Введите внешний ключ курьера (external_key):")


@router.message(TMCIssueStates.courier_key, F.text)
async def tmc_courier(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    darkstore_id = UUID(data["darkstore_id"])
    key = (message.text or "").strip()
    async with async_session_factory() as session:
        repo = AssetsRepository(session)
        courier = await repo.get_courier_by_external_key(darkstore_id, key)
        await session.commit()
    if not courier:
        await message.answer("Курьер не найден. Введите ключ снова:")
        return
    await state.update_data(courier_id=str(courier.id))
    await state.set_state(TMCIssueStates.asset_type)
    builder = InlineKeyboardBuilder()
    for t in AssetType:
        builder.button(text=t.value, callback_data=f"tmc_type:{t.value}")
    builder.adjust(2)
    await message.answer("Выберите тип ТМЦ:", reply_markup=builder.as_markup())


@router.callback_query(F.data.startswith("tmc_type:"), TMCIssueStates.asset_type)
async def tmc_asset_type(callback: CallbackQuery, state: FSMContext) -> None:
    asset_type = callback.data.replace("tmc_type:", "")
    await state.update_data(asset_type=asset_type)
    await state.set_state(TMCIssueStates.serial)
    await callback.message.answer("Введите серийный номер:")
    await callback.answer()


@router.message(TMCIssueStates.serial, F.text)
async def tmc_serial(message: Message, state: FSMContext) -> None:
    await state.update_data(serial=(message.text or "").strip())
    await state.set_state(TMCIssueStates.condition)
    builder = InlineKeyboardBuilder()
    for c in AssetCondition:
        builder.button(text=c.value, callback_data=f"tmc_cond:{c.value}")
    builder.adjust(2)
    await message.answer("Выберите состояние:", reply_markup=builder.as_markup())


@router.callback_query(F.data.startswith("tmc_cond:"), TMCIssueStates.condition)
async def tmc_condition(callback: CallbackQuery, state: FSMContext) -> None:
    cond = callback.data.replace("tmc_cond:", "")
    await state.update_data(condition=cond)
    await state.set_state(TMCIssueStates.photo)
    await callback.message.answer(
        "Отправьте фото (опционально) или нажмите /skip чтобы пропустить."
    )
    await callback.answer()


@router.message(TMCIssueStates.photo, F.photo)
async def tmc_photo(message: Message, state: FSMContext) -> None:
    photo = message.photo[-1] if message.photo else None
    file_id = photo.file_id if photo else None
    await state.update_data(photo_file_id=file_id)
    await _ask_confirm(message, state)


@router.message(TMCIssueStates.photo, F.text)
async def tmc_photo_skip(message: Message, state: FSMContext) -> None:
    if (message.text or "").strip().lower() != "/skip":
        await message.answer("Отправьте фото или /skip")
        return
    await state.update_data(photo_file_id=None)
    await _ask_confirm(message, state)


async def _ask_confirm(message: Message, state: FSMContext) -> None:
    await state.set_state(TMCIssueStates.confirm)
    data = await state.get_data()
    text = (
        f"Подтвердите выдачу ТМЦ:\n"
        f"ДС: {data.get('darkstore_id')}\n"
        f"Курьер: {data.get('courier_id')}\n"
        f"Тип: {data.get('asset_type')}, серийный: {data.get('serial')}\n"
        f"Состояние: {data.get('condition')}"
    )
    builder = InlineKeyboardBuilder()
    builder.button(text="Подтвердить", callback_data="tmc_confirm:yes")
    builder.button(text="Отмена", callback_data="tmc_confirm:no")
    await message.answer(text, reply_markup=builder.as_markup())


@router.callback_query(F.data == "tmc_confirm:yes", TMCIssueStates.confirm)
async def tmc_confirm_yes(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    darkstore_id = UUID(data["darkstore_id"])
    courier_id = UUID(data["courier_id"])
    asset_type = AssetType(data["asset_type"])
    serial = data["serial"]
    condition = AssetCondition(data["condition"])
    photo_file_id = data.get("photo_file_id")
    try:
        service = AssetsService()
        assignment_id = await service.issue_asset(
            darkstore_id=darkstore_id,
            courier_id=courier_id,
            asset_type=asset_type,
            serial=serial,
            condition=condition,
            photo_file_id=photo_file_id,
        )
        await callback.message.answer(f"Записано. Assignment ID: {assignment_id}")
    except AssetAlreadyAssignedError as e:
        await callback.message.answer(f"Ошибка: {e}")
    await state.clear()
    await callback.answer()


@router.callback_query(F.data == "tmc_confirm:no", TMCIssueStates.confirm)
async def tmc_confirm_no(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await callback.message.answer("Отменено.")
    await callback.answer()
