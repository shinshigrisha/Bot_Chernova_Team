"""FSM states for admin flows."""
from aiogram.fsm.state import State, StatesGroup


class TMCIssueStates(StatesGroup):
    darkstore_code = State()
    courier_key = State()
    asset_type = State()
    serial = State()
    condition = State()
    photo = State()
    confirm = State()


class IncidentStates(StatesGroup):
    darkstore_code = State()
    severity = State()
    title = State()
    details = State()
    confirm = State()


class IngestCSVStates(StatesGroup):
    upload = State()


class AIChatStates(StatesGroup):
    active = State()


class AIAddFAQStates(StatesGroup):
    question = State()
    answer = State()
    category = State()
    tag = State()
    keywords = State()
