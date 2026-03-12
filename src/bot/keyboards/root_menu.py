from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from src.infra.db.enums import UserRole

from .navigation import help_button
from src.bot.navigation import ROOT_ADMIN, ROOT_AI_CURATOR, ROOT_HELP, ROOT_VERIFICATION


def build_root_menu_keyboard(role: UserRole | str | None = None) -> InlineKeyboardMarkup:
    """Базовое корневое меню, единое для всех ролей.

    На этом этапе задачи мы не реализуем полную role-based логику,
    но даём единый каркас и точку расширения для следующих задач.
    """
    rows: list[list[InlineKeyboardButton]] = []

    verification_row = [
        InlineKeyboardButton(
            text="✅ Регистрация",
            callback_data=ROOT_VERIFICATION,
        )
    ]
    rows.append(verification_row)

    rows.append(
        [
            InlineKeyboardButton(
                text="🤖 AI-куратор",
                callback_data=ROOT_AI_CURATOR,
            )
        ]
    )

    # Для администраторов сразу подсвечиваем переход в админский раздел.
    is_admin = False
    if isinstance(role, UserRole):
        is_admin = role is UserRole.ADMIN
    elif isinstance(role, str):
        try:
            is_admin = UserRole(role) is UserRole.ADMIN
        except ValueError:
            is_admin = False

    if is_admin:
        rows.append(
            [
                InlineKeyboardButton(
                    text="🛠 Админ-панель",
                    callback_data=ROOT_ADMIN,
                )
            ]
        )

    rows.append(
        [
            help_button(callback_data=ROOT_HELP),
        ]
    )

    return InlineKeyboardMarkup(inline_keyboard=rows)

