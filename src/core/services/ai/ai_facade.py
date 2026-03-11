from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from sqlalchemy.ext.asyncio import async_sessionmaker

from src.core.services.ai.ai_courier_service import AICourierResult, AICourierService
from src.core.services.ai.provider_router import ProviderRouter
from src.core.services.risk import RiskInput


@dataclass
class AIFacade:
    """Канонический фасад AI-курьера для бота и админки.

    Отвечает за единый entrypoint в AI-слой и делегирует всю бизнес-логику
    маршрутизации (rules/FAQ/LLM/эскалация) внутрь AICourierService.
    """

    _courier: AICourierService

    async def get_answer(self, user_id: int, text: str) -> AICourierResult:
        """Вернуть ответ курьера с сохранением Explainability-контекста."""
        return await self._courier.get_answer(user_id=user_id, text=text)

    def get_risk_recommendation(self, risk_input: RiskInput) -> AICourierResult:
        """Проактивная рекомендация по риску доставки (risk_engine + recommendation_engine)."""
        return self._courier.get_risk_recommendation(risk_input)

    def reload_policy(self) -> None:
        """Перечитать core_policy и связанные конфиги."""
        self._courier.reload_policy()

    @property
    def courier(self) -> AICourierService:
        """Доступ к низкоуровневому сервису для совместимости и тестов."""
        return self._courier


def build_ai_facade(
    session_factory: async_sessionmaker,
    router: ProviderRouter | None = None,
    data_root: str | Path = "data/ai",
) -> AIFacade:
    """Сконструировать фасад поверх канонического AICourierService.

    Используется как точка входа для новых интеграций, при этом
    существующий код может продолжать работать с самим AICourierService.
    """
    courier = AICourierService(session_factory=session_factory, router=router, data_root=data_root)
    return AIFacade(_courier=courier)

