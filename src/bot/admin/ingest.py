"""FSM: CSV ingest upload."""
from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from src.bot.states import IngestCSVStates
from src.core.services.access_service import AccessService
from src.core.services.ingest import IngestService
from src.infra.db.enums import IngestSource

router = Router(name="admin_ingest")
ADMIN_CB_PREFIX = "admin:"


async def _ensure_admin_callback(callback: CallbackQuery, access_service: AccessService) -> bool:
    tg_user_id = callback.from_user.id if callback.from_user else 0
    if not await access_service.can_access_admin(tg_user_id):
        await callback.answer("Доступ запрещён.", show_alert=True)
        return False
    return True


@router.callback_query(F.data == f"{ADMIN_CB_PREFIX}ingest")
async def start_ingest(
    callback: CallbackQuery,
    state: FSMContext,
    access_service: AccessService,
) -> None:
    if not await _ensure_admin_callback(callback, access_service):
        return
    await state.clear()
    await state.set_state(IngestCSVStates.upload)
    await callback.message.answer("Отправьте CSV файл (документом):")
    await callback.answer()


@router.message(IngestCSVStates.upload, F.document)
async def ingest_document(message: Message, state: FSMContext) -> None:
    doc = message.document
    if not doc or not doc.file_name or not doc.file_name.lower().endswith(".csv"):
        await message.answer("Нужен файл с расширением .csv. Отправьте документ снова.")
        return
    await message.answer("Скачиваю и обрабатываю…")
    bot = message.bot
    file = await bot.get_file(doc.file_id)
    file_bytes = await bot.download_file(file.file_path)
    if file_bytes is None:
        await message.answer("Не удалось скачать файл.")
        await state.clear()
        return
    content = file_bytes.read()
    service = IngestService()
    batch_id, is_new = await service.accept_csv_upload(
        file_bytes=content,
        filename=doc.file_name or "upload.csv",
        source=IngestSource.CSV_UPLOAD,
    )
    if is_new:
        await message.answer(f"Batch создан. ID: {batch_id}. Парсинг поставлен в очередь.")
    else:
        await message.answer(f"Дубликат по content_hash. Существующий batch ID: {batch_id}")
    await state.clear()
