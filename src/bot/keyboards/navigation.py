from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


BACK_TEXT = "⬅️ Назад"
MAIN_MENU_TEXT = "🏠 Главное меню"
CANCEL_TEXT = "✖️ Отмена"
HELP_TEXT = "❓ Помощь"


def back_button(callback_data: str) -> InlineKeyboardButton:
    return InlineKeyboardButton(text=BACK_TEXT, callback_data=callback_data)


def main_menu_button(callback_data: str) -> InlineKeyboardButton:
    return InlineKeyboardButton(text=MAIN_MENU_TEXT, callback_data=callback_data)


def cancel_button(callback_data: str) -> InlineKeyboardButton:
    return InlineKeyboardButton(text=CANCEL_TEXT, callback_data=callback_data)


def help_button(callback_data: str) -> InlineKeyboardButton:
    return InlineKeyboardButton(text=HELP_TEXT, callback_data=callback_data)


def build_nav_keyboard(
    *,
    back_cb: str | None = None,
    main_cb: str | None = None,
    cancel_cb: str | None = None,
    help_cb: str | None = None,
) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []

    nav_row: list[InlineKeyboardButton] = []
    if back_cb:
        nav_row.append(back_button(back_cb))
    if main_cb:
        nav_row.append(main_menu_button(main_cb))
    if nav_row:
        rows.append(nav_row)

    second_row: list[InlineKeyboardButton] = []
    if cancel_cb:
        second_row.append(cancel_button(cancel_cb))
    if help_cb:
        second_row.append(help_button(help_cb))
    if second_row:
        rows.append(second_row)

    return InlineKeyboardMarkup(inline_keyboard=rows)

