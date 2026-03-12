from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


VERIFICATION_CB_PREFIX = "verification:"

ROLE_COURIER_CB = f"{VERIFICATION_CB_PREFIX}role:courier"
ROLE_CURATOR_CB = f"{VERIFICATION_CB_PREFIX}role:curator"

CONFIRM_YES_CB = f"{VERIFICATION_CB_PREFIX}confirm:yes"
CONFIRM_NO_CB = f"{VERIFICATION_CB_PREFIX}confirm:no"


def build_registration_entry_keyboard() -> InlineKeyboardMarkup:
    """Single 'Регистрация' button to start verification FSM."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✅ Регистрация", callback_data=f"{VERIFICATION_CB_PREFIX}start")],
        ]
    )


def build_role_choice_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="Курьер", callback_data=ROLE_COURIER_CB),
                InlineKeyboardButton(text="Куратор", callback_data=ROLE_CURATOR_CB),
            ],
        ]
    )


def build_confirmation_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Подтвердить", callback_data=CONFIRM_YES_CB),
                InlineKeyboardButton(text="↩️ Изменить", callback_data=CONFIRM_NO_CB),
            ],
        ]
    )

