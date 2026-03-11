"""Rule-based risk evaluators. Each rule returns RiskResult or None."""

from __future__ import annotations

from dataclasses import dataclass

from src.core.services.risk.features import RiskInput


@dataclass
class RiskResult:
    risk_score: float
    risk_type: str
    severity: str
    risk_reasons: list[str]


def late_delivery_risk(inp: RiskInput) -> RiskResult | None:
    if inp.minutes_to_deadline <= 0 or inp.eta_minutes <= 0:
        return None
    if inp.eta_minutes > inp.minutes_to_deadline:
        gap = inp.eta_minutes - inp.minutes_to_deadline
        score = min(1.0, 0.3 + gap / 60.0)
        return RiskResult(
            risk_score=score,
            risk_type="late_delivery_risk",
            severity="high" if score >= 0.7 else "medium",
            risk_reasons=[f"ETA ({inp.eta_minutes} мин) превышает время до дедлайна ({inp.minutes_to_deadline} мин)"],
        )
    if inp.minutes_to_deadline < 15 and inp.eta_minutes >= inp.minutes_to_deadline * 0.8:
        return RiskResult(
            risk_score=0.5,
            risk_type="late_delivery_risk",
            severity="medium",
            risk_reasons=["Мало времени до дедлайна при текущем ETA"],
        )
    return None


def customer_contact_risk(inp: RiskInput) -> RiskResult | None:
    if not inp.has_customer_comment:
        return None
    reasons = ["Есть комментарий клиента — требуется проверка контакта"]
    addr = inp.address_flags or {}
    if addr.get("no_doorcode") or addr.get("hard_to_find"):
        reasons.append("Сложный адрес / нет кода домофона")
    return RiskResult(
        risk_score=0.5,
        risk_type="customer_contact_risk",
        severity="medium",
        risk_reasons=reasons,
    )


def missing_items_risk(inp: RiskInput) -> RiskResult | None:
    items = inp.item_flags or {}
    if not items.get("partial_missing") and not items.get("shortage"):
        return None
    reasons = []
    if items.get("partial_missing"):
        reasons.append("Частичная недовоза")
    if items.get("shortage"):
        reasons.append("Нехватка позиций")
    return RiskResult(
        risk_score=0.7,
        risk_type="missing_items_risk",
        severity="high",
        risk_reasons=reasons or ["Риск недовоза"],
    )


def fragile_goods_risk(inp: RiskInput) -> RiskResult | None:
    items = inp.item_flags or {}
    if not items.get("fragile") and not items.get("glass"):
        return None
    reasons = []
    if items.get("fragile"):
        reasons.append("Хрупкий груз")
    if items.get("glass"):
        reasons.append("Стекло")
    if inp.event_type in ("bump", "delay", "multi_stop"):
        reasons.append(f"Событие в пути: {inp.event_type}")
    return RiskResult(
        risk_score=0.6,
        risk_type="fragile_goods_risk",
        severity="medium",
        risk_reasons=reasons or ["Хрупкие/стекло в заказе"],
    )


def payment_issue_risk(inp: RiskInput) -> RiskResult | None:
    items = inp.item_flags or {}
    addr = inp.address_flags or {}
    if not items.get("prepaid") and not addr.get("cash_only"):
        return None
    reasons = []
    if items.get("prepaid"):
        reasons.append("Предоплата — проверка при передаче")
    if addr.get("cash_only"):
        reasons.append("Только наличные по адресу")
    return RiskResult(
        risk_score=0.5,
        risk_type="payment_issue_risk",
        severity="medium",
        risk_reasons=reasons or ["Особенности оплаты"],
    )


def return_order_risk(inp: RiskInput) -> RiskResult | None:
    if "return" not in (inp.event_type or "").lower() and "refund" not in (inp.event_type or "").lower():
        return None
    return RiskResult(
        risk_score=0.6,
        risk_type="return_order_risk",
        severity="medium",
        risk_reasons=["Возврат/отмена — соблюдать регламент передачи"],
    )


def courier_overload_risk(inp: RiskInput) -> RiskResult | None:
    if inp.active_orders_count < 3:
        return None
    score = min(1.0, 0.3 + (inp.active_orders_count - 3) * 0.15)
    return RiskResult(
        risk_score=score,
        risk_type="courier_overload_risk",
        severity="high" if inp.active_orders_count >= 6 else "medium",
        risk_reasons=[f"Активных заказов у курьера: {inp.active_orders_count}"],
    )


ALL_RULES = [
    late_delivery_risk,
    customer_contact_risk,
    missing_items_risk,
    fragile_goods_risk,
    payment_issue_risk,
    return_order_risk,
    courier_overload_risk,
]
