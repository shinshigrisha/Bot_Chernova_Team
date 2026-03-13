"""Scenario Router: явный слой ветвления по типу флоу.

Определяет канонические сценарии бота и маппинг callback_data / роутеров на флоу.
Отрисовка меню и переходы состояний остаются в navigation.py и menu_renderer.py;
здесь — единый источник истины для типов флоу и привязки к роутерам/FSM.

Флоу (см. план canonical-ai-bot-architecture):
- Admin flows       — управление, отчёты, риск, ingest, верификация заявок.
- Verification flows — регистрация, KYC, статусы заявки.
- Courier UI flows  — смены, TT, справка, пункт входа в AI-куратор.
- Curator UI flows  — аналитика, FAQ, пункт входа в AI-куратор.
- AI Curator flow   — диалоги с AI по кейсам доставки (answer_user/answer_admin).
- AI Analyst flow   — запросы на аналитику и отчёты (admin: CSV и т.п.).
"""

from __future__ import annotations

from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass


class BotFlow(str, Enum):
    """Канонические сценарии бота. Соответствуют веткам Scenario Router."""

    ROOT = "root"
    HELP = "help"
    ADMIN = "admin"
    VERIFICATION = "verification"
    COURIER_UI = "courier_ui"
    CURATOR_UI = "curator_ui"
    AI_CURATOR = "ai_curator"
    AI_ANALYST = "ai_analyst"


# Маппинг: префикс или точный callback_data -> флоу (первое совпадение побеждает)
# Порядок: точные значения, затем префиксы от длинных к коротким.
CALLBACK_TO_FLOW: list[tuple[str, BotFlow]] = [
    # Точные root/nav
    ("root:main", BotFlow.ROOT),
    ("root:help", BotFlow.HELP),
    ("root:verification", BotFlow.VERIFICATION),
    ("root:admin", BotFlow.ADMIN),
    ("root:ai_curator", BotFlow.AI_CURATOR),
    ("nav:main", BotFlow.ROOT),
    ("nav:back", BotFlow.ROOT),
    ("nav:cancel", BotFlow.ROOT),
    ("nav:help", BotFlow.HELP),
    # Префиксы по длине (длинные первыми)
    ("admin:verification", BotFlow.ADMIN),
    ("admin:ai_curator", BotFlow.ADMIN),
    ("admin:ingest", BotFlow.AI_ANALYST),
    ("admin:csv", BotFlow.AI_ANALYST),
    ("admin:", BotFlow.ADMIN),
    ("verification:", BotFlow.VERIFICATION),
    ("pending:", BotFlow.VERIFICATION),
    ("ai_curator:case:", BotFlow.AI_CURATOR),
    ("ai_curator:", BotFlow.AI_CURATOR),
    ("courier:shifts", BotFlow.COURIER_UI),
    ("courier:faq", BotFlow.COURIER_UI),
    ("courier:", BotFlow.COURIER_UI),
    ("curator:analytics", BotFlow.AI_ANALYST),
    ("curator:faq", BotFlow.CURATOR_UI),
    ("curator:", BotFlow.CURATOR_UI),
]

# Роутер (aiogram) -> основной флоу для документации и тестов
ROUTER_TO_FLOW: dict[str, BotFlow] = {
    "navigation": BotFlow.ROOT,
    "start": BotFlow.ROOT,
    "verification": BotFlow.VERIFICATION,
    "admin": BotFlow.ADMIN,
    "ai_chat": BotFlow.AI_CURATOR,
}

# FSM StatesGroup -> флоу (для справки)
STATES_TO_FLOW: dict[str, BotFlow] = {
    "VerificationStates": BotFlow.VERIFICATION,
    "TMCIssueStates": BotFlow.ADMIN,
    "IncidentStates": BotFlow.ADMIN,
    "IngestCSVStates": BotFlow.AI_ANALYST,
    "AIChatStates": BotFlow.AI_CURATOR,
    "AIAddFAQStates": BotFlow.ADMIN,
}


def resolve_flow(callback_data: str | None) -> BotFlow | None:
    """Определить флоу по callback_data (inline-кнопка или аналогичный интент).

    Returns:
        Соответствующий BotFlow или None, если не удалось определить.
    """
    if not callback_data:
        return None
    for prefix_or_exact, flow in CALLBACK_TO_FLOW:
        if prefix_or_exact.endswith(":"):
            if callback_data.startswith(prefix_or_exact):
                return flow
        else:
            if callback_data == prefix_or_exact:
                return flow
    return None
