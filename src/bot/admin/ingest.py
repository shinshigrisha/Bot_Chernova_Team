"""FSM: CSV ingest upload."""
from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from src.bot.states import IngestCSVStates
from src.core.services.access_service import AccessService
from src.core.services.ingest import IngestService
from src.infra.db.enums import IngestSource

from src.bot.access_guards import require_admin_for_callback

router = Router(name="admin_ingest")
ADMIN_CB_PREFIX = "admin:"


@router.callback_query(F.data == f"{ADMIN_CB_PREFIX}ingest")
async def start_ingest(
    callback: CallbackQuery,
    state: FSMContext,
    access_service: AccessService,
) -> None:
    if not await require_admin_for_callback(callback, access_service):
        return
    await state.clear()
    await state.set_state(IngestCSVStates.upload)
    await callback.message.answer("Отправьте CSV файл (документом):")
    await callback.answer()


@router.message(IngestCSVStates.upload, F.document)
async def ingest_document(
    message: Message,
    state: FSMContext,
    ingest_service: IngestService | None = None,
) -> None:
    doc = message.document
    if not doc or not doc.file_name or not doc.file_name.lower().endswith(".csv"):
        await message.answer("Нужен файл с расширением .csv. Отправьте документ снова.")
        return
    if not ingest_service:
        await message.answer("Сервис импорта временно недоступен.")
        await state.clear()
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
    batch_id, is_new = await ingest_service.accept_csv_upload(
        file_bytes=content,
        filename=doc.file_name or "upload.csv",
        source=IngestSource.CSV_UPLOAD,
    )
    if is_new:
        await message.answer(f"Batch создан. ID: {batch_id}. Парсинг поставлен в очередь.")
    else:
        await message.answer(f"Дубликат по content_hash. Существующий batch ID: {batch_id}")
    await state.clear()
