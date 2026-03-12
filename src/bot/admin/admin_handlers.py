from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, InlineKeyboardButton, Message

from src.bot.admin.admin_menu import (
    ADMIN_BACK_CB,
    ADMIN_CANCEL_CB,
    AI_CURATOR_CB,
    ASSETS_CB,
    BROADCASTS_CB,
    CSV_ANALYSIS_CB,
    FAQ_KB_CB,
    MONITORING_CB,
    VERIFICATION_CB,
    build_admin_main_menu,
    with_section_nav,
)
from src.bot.keyboards.admin_main import ADMIN_CB_PREFIX
from src.core.services.access_service import AccessService
from src.core.services.verification_service import VerificationService
from src.infra.db.session import async_session_factory

router = Router(name="admin_main_menu")

VERIFICATION_APPROVE_PREFIX = f"{ADMIN_CB_PREFIX}verification:approve:"
VERIFICATION_REJECT_PREFIX = f"{ADMIN_CB_PREFIX}verification:reject:"


async def _ensure_admin_message(
    message: Message,
    access_service: AccessService,
) -> bool:
    tg_user_id = message.from_user.id if message.from_user else 0
    if not await access_service.can_access_admin(tg_user_id):
        await message.answer("Доступ запрещён.")
        return False
    return True


async def _ensure_admin_callback(
    callback: CallbackQuery,
    access_service: AccessService,
) -> bool:
    tg_user_id = callback.from_user.id if callback.from_user else 0
    if not await access_service.can_access_admin(tg_user_id):
        await callback.answer("Доступ запрещён.", show_alert=True)
        return False
    return True


@router.message(Command("admin"))
async def cmd_admin(
    message: Message,
    access_service: AccessService,
) -> None:
    if not await _ensure_admin_message(message, access_service):
        return
    await message.answer("Админ-панель:", reply_markup=build_admin_main_menu())


async def _verification_screen_content():
    """Текст и клавиатура для экрана верификации (список pending)."""
    service = VerificationService(async_session_factory)
    pending = await service.list_pending_with_applications()
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
        ])
    return "\n".join(lines), with_section_nav(rows)


@router.callback_query(F.data == VERIFICATION_CB)
async def cb_verification_menu(
    callback: CallbackQuery,
    access_service: AccessService,
) -> None:
    if not await _ensure_admin_callback(callback, access_service):
        return
    text, markup = await _verification_screen_content()
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
    return "Статус вашей заявки изменён. Нажмите /start."


@router.callback_query(F.data.startswith(VERIFICATION_APPROVE_PREFIX))
async def cb_verification_approve(
    callback: CallbackQuery,
    access_service: AccessService,
) -> None:
    if not await _ensure_admin_callback(callback, access_service):
        return
    tg_user_id = int(callback.data.replace(VERIFICATION_APPROVE_PREFIX, ""))
    service = VerificationService(async_session_factory)
    try:
        await service.apply_admin_decision(tg_user_id=tg_user_id, decision="approve")
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
    text, markup = await _verification_screen_content()
    is_alert_msg = callback.message.text and "Новая заявка" in callback.message.text
    if is_alert_msg:
        await callback.message.edit_text("✅ Пользователь одобрен.", reply_markup=None)
    else:
        await callback.message.edit_text(text, reply_markup=markup)


@router.callback_query(F.data.startswith(VERIFICATION_REJECT_PREFIX))
async def cb_verification_reject(
    callback: CallbackQuery,
    access_service: AccessService,
) -> None:
    if not await _ensure_admin_callback(callback, access_service):
        return
    tg_user_id = int(callback.data.replace(VERIFICATION_REJECT_PREFIX, ""))
    service = VerificationService(async_session_factory)
    try:
        await service.apply_admin_decision(tg_user_id=tg_user_id, decision="reject")
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
    text, markup = await _verification_screen_content()
    is_alert_msg = callback.message.text and "Новая заявка" in callback.message.text
    if is_alert_msg:
        await callback.message.edit_text("❌ Заявка отклонена.", reply_markup=None)
    else:
        await callback.message.edit_text(text, reply_markup=markup)


@router.callback_query(F.data == FAQ_KB_CB)
async def cb_faq_menu(
    callback: CallbackQuery,
    access_service: AccessService,
) -> None:
    if not await _ensure_admin_callback(callback, access_service):
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
    access_service: AccessService,
) -> None:
    if not await _ensure_admin_callback(callback, access_service):
        return
    await callback.message.edit_text(
        "Раздел AI-куратора:\n"
        "- мониторинг статуса AI,\n"
        "- управление FAQ и политиками.\n\n"
        "Существующие команды /ai_status, /ai_add_faq и др. остаются доступны.",
        reply_markup=with_section_nav(),
    )
    await callback.answer()


@router.callback_query(F.data == CSV_ANALYSIS_CB)
async def cb_csv_menu(
    callback: CallbackQuery,
    access_service: AccessService,
) -> None:
    if not await _ensure_admin_callback(callback, access_service):
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
    if not await _ensure_admin_callback(callback, access_service):
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
    if not await _ensure_admin_callback(callback, access_service):
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
    if not await _ensure_admin_callback(callback, access_service):
        return
    await callback.message.edit_text(
        "Раздел рассылок:\n"
        "Здесь в будущем появятся рассылки и таргетированные уведомления.",
        reply_markup=with_section_nav(),
    )
    await callback.answer()


@router.callback_query(F.data == ADMIN_BACK_CB)
async def cb_back_to_admin_root(
    callback: CallbackQuery,
    access_service: AccessService,
) -> None:
    if not await _ensure_admin_callback(callback, access_service):
        return
    await callback.message.edit_text(
        "Админ-панель:",
        reply_markup=build_admin_main_menu(),
    )
    await callback.answer()


@router.callback_query(F.data == ADMIN_CANCEL_CB)
async def cb_admin_cancel(
    callback: CallbackQuery,
    access_service: AccessService,
) -> None:
    if not await _ensure_admin_callback(callback, access_service):
        return
    await callback.message.edit_text("Админ-действие отменено.", reply_markup=None)
    await callback.answer()


