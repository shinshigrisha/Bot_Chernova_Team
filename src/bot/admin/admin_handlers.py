from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardButton, Message

from src.bot.admin.admin_menu import (
    ADMIN_BACK_CB,
    ADMIN_CANCEL_CB,
    AI_CURATOR_CB,
    ASSETS_CB,
    BROADCASTS_CB,
    CSV_ANALYSIS_CB,
    FAQ_KB_CB,
    LEGACY_CB,
    MONITORING_CB,
    VERIFICATION_CB,
    build_admin_main_menu,
    build_legacy_keyboard,
    with_section_nav,
)
from src.bot.access_guards import require_admin_for_callback, require_admin_for_message
from src.bot.keyboards.admin_main import ADMIN_CB_PREFIX
from src.bot.menu_renderer import get_admin_root_message
from src.core.services.access_service import AccessService
from src.core.services.verification_service import VerificationService

router = Router(name="admin_main_menu")

VERIFICATION_APPROVE_PREFIX = f"{ADMIN_CB_PREFIX}verification:approve:"
VERIFICATION_REJECT_PREFIX = f"{ADMIN_CB_PREFIX}verification:reject:"
VERIFICATION_BLOCK_PREFIX = f"{ADMIN_CB_PREFIX}verification:block:"


@router.message(Command("admin"))
async def cmd_admin(
    message: Message,
    access_service: AccessService,
) -> None:
    if not await require_admin_for_message(message, access_service):
        return
    await message.answer(get_admin_root_message(), reply_markup=build_admin_main_menu())


async def _verification_screen_content(verification_service: VerificationService):
    """Текст и клавиатура для экрана верификации (список pending)."""
    pending = await verification_service.list_pending_with_applications()
    if not pending:
        return "Раздел верификации.\n\nЗаявок на рассмотрении нет.", with_section_nav()
    lines = ["**Заявки на регистрацию (pending):**\n"]
    rows: list[list[InlineKeyboardButton]] = []
    for _user, app in pending:
        name = f"{app.first_name} {app.last_name}".strip() or "—"
        lines.append(
            f"• {name} (ТТ {app.tt_number}, {app.role}) — tg_id `{app.tg_user_id}`"
        )
        rows.append([
            InlineKeyboardButton(
                text=f"✅ Одобрить {app.tg_user_id}",
                callback_data=f"{VERIFICATION_APPROVE_PREFIX}{app.tg_user_id}",
            ),
            InlineKeyboardButton(
                text=f"❌ Отклонить {app.tg_user_id}",
                callback_data=f"{VERIFICATION_REJECT_PREFIX}{app.tg_user_id}",
            ),
            InlineKeyboardButton(
                text=f"⛔ Блок {app.tg_user_id}",
                callback_data=f"{VERIFICATION_BLOCK_PREFIX}{app.tg_user_id}",
            ),
        ])
    return "\n".join(lines), with_section_nav(rows)


@router.callback_query(F.data == VERIFICATION_CB)
async def cb_verification_menu(
    callback: CallbackQuery,
    access_service: AccessService,
    verification_service: VerificationService | None = None,
) -> None:
    if not await require_admin_for_callback(callback, access_service):
        return
    if not verification_service:
        await callback.answer("Сервис верификации недоступен.", show_alert=True)
        return
    text, markup = await _verification_screen_content(verification_service)
    await callback.message.edit_text(text, reply_markup=markup)
    await callback.answer()


def _verification_notify_user_text(decision: str) -> str:
    if decision == "approve":
        return (
            "Ваша заявка на регистрацию одобрена. "
            "Нажмите /start для обновления меню."
        )
    if decision == "reject":
        return (
            "Ваша заявка на регистрацию отклонена. "
            "Вы можете подать новую заявку через /start."
        )
    if decision == "block":
        return (
            "Ваш аккаунт заблокирован администратором. "
            "Обратитесь к администратору для выяснения причин."
        )
    return "Статус вашей заявки изменён. Нажмите /start."


@router.callback_query(F.data.startswith(VERIFICATION_APPROVE_PREFIX))
async def cb_verification_approve(
    callback: CallbackQuery,
    access_service: AccessService,
    verification_service: VerificationService | None = None,
) -> None:
    if not await require_admin_for_callback(callback, access_service):
        return
    if not verification_service:
        await callback.answer("Сервис верификации недоступен.", show_alert=True)
        return
    tg_user_id = int(callback.data.replace(VERIFICATION_APPROVE_PREFIX, ""))
    try:
        await verification_service.apply_admin_decision(tg_user_id=tg_user_id, decision="approve")
    except Exception:
        await callback.answer("Ошибка при одобрении.", show_alert=True)
        return
    try:
        await callback.bot.send_message(
            chat_id=tg_user_id,
            text=_verification_notify_user_text("approve"),
        )
    except Exception:
        pass
    await callback.answer("Пользователь одобрен.", show_alert=True)
    text, markup = await _verification_screen_content(verification_service)
    is_alert_msg = callback.message.text and "Новая заявка" in callback.message.text
    if is_alert_msg:
        await callback.message.edit_text("✅ Пользователь одобрен.", reply_markup=None)
    else:
        await callback.message.edit_text(text, reply_markup=markup)


@router.callback_query(F.data.startswith(VERIFICATION_REJECT_PREFIX))
async def cb_verification_reject(
    callback: CallbackQuery,
    access_service: AccessService,
    verification_service: VerificationService | None = None,
) -> None:
    if not await require_admin_for_callback(callback, access_service):
        return
    if not verification_service:
        await callback.answer("Сервис верификации недоступен.", show_alert=True)
        return
    tg_user_id = int(callback.data.replace(VERIFICATION_REJECT_PREFIX, ""))
    try:
        await verification_service.apply_admin_decision(tg_user_id=tg_user_id, decision="reject")
    except Exception:
        await callback.answer("Ошибка при отклонении.", show_alert=True)
        return
    try:
        await callback.bot.send_message(
            chat_id=tg_user_id,
            text=_verification_notify_user_text("reject"),
        )
    except Exception:
        pass
    await callback.answer("Заявка отклонена.", show_alert=True)
    text, markup = await _verification_screen_content(verification_service)
    is_alert_msg = callback.message.text and "Новая заявка" in callback.message.text
    if is_alert_msg:
        await callback.message.edit_text("❌ Заявка отклонена.", reply_markup=None)
    else:
        await callback.message.edit_text(text, reply_markup=markup)


@router.callback_query(F.data.startswith(VERIFICATION_BLOCK_PREFIX))
async def cb_verification_block(
    callback: CallbackQuery,
    access_service: AccessService,
    verification_service: VerificationService | None = None,
) -> None:
    if not await require_admin_for_callback(callback, access_service):
        return
    if not verification_service:
        await callback.answer("Сервис верификации недоступен.", show_alert=True)
        return
    tg_user_id = int(callback.data.replace(VERIFICATION_BLOCK_PREFIX, ""))
    try:
        await verification_service.apply_admin_decision(tg_user_id=tg_user_id, decision="block")
    except Exception:
        await callback.answer("Ошибка при блокировке.", show_alert=True)
        return
    try:
        await callback.bot.send_message(
            chat_id=tg_user_id,
            text=_verification_notify_user_text("block"),
        )
    except Exception:
        pass
    await callback.answer("Пользователь заблокирован.", show_alert=True)
    text, markup = await _verification_screen_content(verification_service)
    is_alert_msg = callback.message.text and "Новая заявка" in callback.message.text
    if is_alert_msg:
        await callback.message.edit_text("⛔ Пользователь заблокирован.", reply_markup=None)
    else:
        await callback.message.edit_text(text, reply_markup=markup)


@router.callback_query(F.data == FAQ_KB_CB)
async def cb_faq_menu(
    callback: CallbackQuery,
    access_service: AccessService,
) -> None:
    if not await require_admin_for_callback(callback, access_service):
        return
    await callback.message.edit_text(
        "Раздел **FAQ / база знаний**:\n"
        "Управление вопросами и ответами для AI-куратора.\n\n"
        "Команды: /ai_add_faq, пересборка эмбеддингов — через раздел AI-куратор.",
        reply_markup=with_section_nav(),
    )
    await callback.answer()


@router.callback_query(F.data == AI_CURATOR_CB)
async def cb_ai_menu(
    callback: CallbackQuery,
    state: FSMContext,
    access_service: AccessService,
) -> None:
    """Вход в AI-куратор из админки: тот же user-facing экран (интро + быстрые кейсы)."""
    if not await require_admin_for_callback(callback, access_service):
        return
    from src.bot.keyboards.ai_curator import build_ai_curator_intro_keyboard
    from src.bot.states import AIChatStates

    await state.set_state(AIChatStates.active)
    await state.update_data(entry_from_curator=True)
    await callback.message.answer(
        "🤖 **AI-куратор**\n\n"
        "Опишите проблему с доставкой — подскажу шаги по регламенту.\n\n"
        "Выберите типовой кейс или напишите свой вопрос текстом.",
        reply_markup=build_ai_curator_intro_keyboard(),
    )
    await callback.answer()


@router.callback_query(F.data == CSV_ANALYSIS_CB)
async def cb_csv_menu(
    callback: CallbackQuery,
    access_service: AccessService,
) -> None:
    if not await require_admin_for_callback(callback, access_service):
        return
    rows = [
        [
            InlineKeyboardButton(
                text="📥 Импорт CSV",
                callback_data=f"{ADMIN_CB_PREFIX}ingest",
            )
        ],
    ]
    await callback.message.edit_text(
        "Раздел анализа CSV:\n"
        "Используйте импорт CSV для загрузки новых батчей данных.",
        reply_markup=with_section_nav(rows),
    )
    await callback.answer()


@router.callback_query(F.data == MONITORING_CB)
async def cb_monitoring_menu(
    callback: CallbackQuery,
    access_service: AccessService,
) -> None:
    if not await require_admin_for_callback(callback, access_service):
        return
    from src.config import get_settings
    settings = get_settings()
    ai_status = "вкл" if settings.ai_enabled else "выкл"
    await callback.message.edit_text(
        "Раздел мониторинга.\n\n"
        f"• Бот: работает\n"
        f"• AI куратор: {ai_status}",
        reply_markup=with_section_nav(),
    )
    await callback.answer()


@router.callback_query(F.data == ASSETS_CB)
async def cb_assets_menu(
    callback: CallbackQuery,
    access_service: AccessService,
) -> None:
    if not await require_admin_for_callback(callback, access_service):
        return
    rows = [
        [
            InlineKeyboardButton(
                text="➕ Выдать ТМЦ",
                callback_data=f"{ADMIN_CB_PREFIX}tmc",
            )
        ],
    ]
    await callback.message.edit_text(
        "Раздел ТМЦ:\n"
        "Управление выдачей и учётом ТМЦ.",
        reply_markup=with_section_nav(rows),
    )
    await callback.answer()


@router.callback_query(F.data == BROADCASTS_CB)
async def cb_broadcast_menu(
    callback: CallbackQuery,
    access_service: AccessService,
) -> None:
    if not await require_admin_for_callback(callback, access_service):
        return
    await callback.message.edit_text(
        "Раздел рассылок:\n"
        "Здесь в будущем появятся рассылки и таргетированные уведомления.",
        reply_markup=with_section_nav(),
    )
    await callback.answer()


@router.callback_query(F.data == LEGACY_CB)
async def cb_legacy_root(
    callback: CallbackQuery,
    access_service: AccessService,
) -> None:
    if not await require_admin_for_callback(callback, access_service):
        return
    legacy_rows = build_legacy_keyboard().inline_keyboard
    await callback.message.edit_text(
        "Legacy / сервисные разделы:\n"
        "ТМЦ, журнал смены, импорт CSV, настройки, мониторинг.",
        reply_markup=with_section_nav(legacy_rows),
    )
    await callback.answer()


@router.callback_query(F.data == f"{ADMIN_CB_PREFIX}monitor")
async def cb_legacy_monitor(
    callback: CallbackQuery,
    access_service: AccessService,
) -> None:
    if not await require_admin_for_callback(callback, access_service):
        return
    from src.config import get_settings
    settings = get_settings()
    ai_status = "вкл" if settings.ai_enabled else "выкл"
    await callback.message.edit_text(
        "Раздел мониторинга (legacy).\n\n"
        f"• Бот: работает\n"
        f"• AI куратор: {ai_status}",
        reply_markup=with_section_nav(),
    )
    await callback.answer()


@router.callback_query(F.data == f"{ADMIN_CB_PREFIX}settings")
async def cb_legacy_settings(
    callback: CallbackQuery,
    access_service: AccessService,
) -> None:
    if not await require_admin_for_callback(callback, access_service):
        return
    await callback.message.edit_text(
        "Настройки бота:\n"
        "Конфигурация через переменные окружения и config. "
        "Расширенный экран настроек — в разработке.",
        reply_markup=with_section_nav(),
    )
    await callback.answer()


@router.callback_query(F.data == ADMIN_BACK_CB)
async def cb_back_to_admin_root(
    callback: CallbackQuery,
    access_service: AccessService,
) -> None:
    if not await require_admin_for_callback(callback, access_service):
        return
    await callback.message.edit_text(
        get_admin_root_message(),
        reply_markup=build_admin_main_menu(),
    )
    await callback.answer()


@router.callback_query(F.data == ADMIN_CANCEL_CB)
async def cb_admin_cancel(
    callback: CallbackQuery,
    access_service: AccessService,
) -> None:
    if not await require_admin_for_callback(callback, access_service):
        return
    await callback.message.edit_text("Админ-действие отменено.", reply_markup=None)
    await callback.answer()


