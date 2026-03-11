"""Maps risk result to short message, action steps, and escalate flag."""

from __future__ import annotations

from dataclasses import dataclass

from src.core.services.risk.rules import RiskResult


@dataclass
class Recommendation:
    short_message: str
    action_steps: list[str]
    escalate: bool


_SEVERITY_ESCALATE: dict[str, bool] = {
    "high": True,
    "medium": False,
    "low": False,
}

_MESSAGES: dict[str, str] = {
    "late_delivery_risk": "Риск опоздания к дедлайну",
    "customer_contact_risk": "Требуется контакт с клиентом",
    "missing_items_risk": "Риск недовоза",
    "fragile_goods_risk": "Хрупкий груз — аккуратная доставка",
    "payment_issue_risk": "Особенности оплаты",
    "return_order_risk": "Возврат/отмена заказа",
    "courier_overload_risk": "Высокая загрузка курьера",
}

_ACTION_STEPS: dict[str, list[str]] = {
    "late_delivery_risk": [
        "Оценить реальный ETA",
        "Сообщить куратору при неизбежном опоздании",
        "Зафиксировать причину в комментарии",
    ],
    "customer_contact_risk": [
        "Проверить комментарий к заказу",
        "Позвонить/написать клиенту при необходимости",
        "Уточнить код домофона при отсутствии",
    ],
    "missing_items_risk": [
        "Проверить МП по местам и позициям",
        "Отметить недовоз по регламенту",
        "Сообщить куратору",
    ],
    "fragile_goods_risk": [
        "Проверить целостность упаковки",
        "Аккуратная передача",
        "При повреждении — фото и эскалация",
    ],
    "payment_issue_risk": [
        "Проверить способ оплаты в заказе",
        "Подтвердить сумму при передаче",
    ],
    "return_order_risk": [
        "Соблюдать регламент возврата",
        "Зафиксировать состояние товара",
        "Сообщить куратору",
    ],
    "courier_overload_risk": [
        "Приоритизировать по дедлайнам",
        "Сообщить куратору при срыве сроков",
    ],
}


class RecommendationEngine:
    """Builds recommendation from RiskResult."""

    def recommend(self, risk: RiskResult | None) -> Recommendation | None:
        if risk is None:
            return None
        short_message = _MESSAGES.get(risk.risk_type, risk.risk_type)
        if risk.risk_reasons:
            short_message += ": " + "; ".join(risk.risk_reasons[:2])
        action_steps = _ACTION_STEPS.get(risk.risk_type, ["Связаться с куратором"])
        escalate = _SEVERITY_ESCALATE.get(risk.severity, False)
        return Recommendation(
            short_message=short_message[:500],
            action_steps=action_steps,
            escalate=escalate,
        )
