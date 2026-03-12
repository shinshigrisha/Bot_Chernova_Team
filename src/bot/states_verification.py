from aiogram.fsm.state import State, StatesGroup


class VerificationStates(StatesGroup):
    choose_role = State()
    first_name = State()
    last_name = State()
    tt_number = State()
    phone = State()
    confirm = State()

