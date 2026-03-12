from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from sqlalchemy.ext.asyncio import async_sessionmaker

from src.core.services.ai.ai_courier_service import AICourierResult, AICourierService
from src.core.services.ai.ai_modes import AIMode
from src.core.services.ai.analytics_assistant import DeliveryMetrics, AnalyticsAssistant
from src.core.services.ai.provider_router import ProviderRouter
from src.core.services.risk import RiskInput


@dataclass
class AIFacade:
    """Единственная точка входа в AI-слой. Три режима, не один «умный ответчик».

    Все вызовы LLM только через фасад. Handlers/admin/API не вызывают
    ProviderRouter, AICourierService, RAGService, AnalyticsAssistant напрямую.

    Режимы (см. docs/AI_MODES.md):
    1) Courier assistant   — answer_user, proactive_hint (кейсы доставки).
    2) Admin copilot       — answer_admin (FAQ, рассылки, анализ для админа).
    3) Analytics assistant — analyze_csv (анализ CSV/xlsx/pdf/таблиц).
    """

    _courier: AICourierService
    _router: ProviderRouter | None = None
    _data_root: str | Path = "data/ai"
    _analytics: AnalyticsAssistant | None = None

    def _get_analytics(self) -> AnalyticsAssistant | None:
        if self._analytics is not None:
            return self._analytics
        if self._router is None:
            return None
        self._analytics = AnalyticsAssistant(
            self._router,
            data_root=Path(self._data_root) / "prompts",
        )
        return self._analytics

    # --- (1) Courier assistant: кейсы доставки ---

    async def answer_user(self, user_id: int, text: str) -> AICourierResult:
        """[Courier assistant] Ответ курьеру по каскаду: must_match → rules → FAQ → ML → LLM → fallback.

        Access check (шаг 1 каскада) — обязанность вызывающего: убедиться, что user_id
        имеет право на использование AI-куратора, до вызова answer_user."""
        return await self._courier.get_answer(user_id=user_id, text=text, role="courier")

    def proactive_hint(self, risk_input: RiskInput) -> AICourierResult:
        """[Courier assistant] Проактивная рекомендация по риску доставки (risk_engine + recommendation_engine)."""
        return self._courier.get_risk_recommendation(risk_input)

    # --- (2) Admin copilot: помощь админу ---

    async def answer_admin(self, admin_id: int, text: str) -> AICourierResult:
        """[Admin copilot] Ответ админу: FAQ, подсказки по рассылкам и анализу.

        Сейчас использует тот же пайплайн, что и курьер (get_answer); в перспективе —
        отдельный контекст/политика для админских задач."""
        return await self._courier.get_answer(user_id=admin_id, text=text, role="admin")

    # --- (3) Analytics assistant: анализ данных ---

    async def analyze_csv(
        self,
        *,
        tt_metrics: Iterable[DeliveryMetrics],
        global_summary: dict[str, Any] | None = None,
        raw_sample_notes: str | None = None,
    ) -> str:
        """[Analytics assistant] Аналитический отчёт по метрикам успешных доставок (CSV-данные).

        В перспективе: анализ xlsx, pdf, произвольных таблиц."""
        analytics = self._get_analytics()
        if analytics is None:
            return "Аналитический ассистент недоступен: нет подключённых LLM-провайдеров."
        return await analytics.build_report(
            tt_metrics=tt_metrics,
            global_summary=global_summary,
            raw_sample_notes=raw_sample_notes,
        )

    # --- Служебные (не LLM) ---

    def reload_policy(self) -> None:
        """Перечитать core_policy и связанные конфиги."""
        self._courier.reload_policy()

    def get_provider_names(self) -> list[str]:
        """Список имён включённых LLM-провайдеров (для статуса админки)."""
        if self._router is None or not getattr(self._router, "providers", None):
            return []
        return sorted(self._router.providers.keys())

    @property
    def courier(self) -> AICourierService:
        """Доступ к низкоуровневому сервису только для тестов и совместимости."""
        return self._courier


def build_ai_facade(
    session_factory: async_sessionmaker,
    router: ProviderRouter | None = None,
    data_root: str | Path = "data/ai",
) -> AIFacade:
    """Сконструировать фасад: единственная точка входа в AI для бота и API."""
    courier = AICourierService(session_factory=session_factory, router=router, data_root=data_root)
    return AIFacade(_courier=courier, _router=router, _data_root=data_root)

