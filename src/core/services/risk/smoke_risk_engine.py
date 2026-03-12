"""Smoke tests for the proactive risk pipeline: RiskEngine + RecommendationEngine.

Запуск без pytest:
    python -m src.core.services.risk.smoke_risk_engine

Использование в коде:
    from src.core.services.risk.smoke_risk_engine import run_smoke
    assert run_smoke()
"""

from __future__ import annotations

from src.core.services.risk.features import RiskInput
from src.core.services.risk.recommendation_engine import RecommendationEngine
from src.core.services.risk.risk_engine import RiskEngine
from src.core.services.risk.rules import RiskResult


def _input_no_risk() -> RiskInput:
    """Обычный заказ без флагов риска."""
    return RiskInput.from_dict({
        "order_id": "ord-1",
        "courier_id": "c-1",
        "minutes_to_deadline": 60,
        "eta_minutes": 20,
        "active_orders_count": 1,
        "has_customer_comment": False,
        "address_flags": {},
        "item_flags": {},
        "zone": "zone-a",
        "tt": "tt-1",
        "event_type": "delivery",
    })


def _input_late_delivery() -> RiskInput:
    """ETA больше времени до дедлайна — риск опоздания."""
    return RiskInput.from_dict({
        "order_id": "ord-2",
        "courier_id": "c-2",
        "minutes_to_deadline": 15,
        "eta_minutes": 30,
        "active_orders_count": 2,
        "has_customer_comment": False,
        "address_flags": {},
        "item_flags": {},
        "zone": "zone-b",
        "tt": "tt-2",
        "event_type": "delivery",
    })


def _input_customer_contact() -> RiskInput:
    """Комментарий клиента + сложный адрес."""
    return RiskInput.from_dict({
        "order_id": "ord-3",
        "courier_id": "c-3",
        "minutes_to_deadline": 45,
        "eta_minutes": 25,
        "active_orders_count": 1,
        "has_customer_comment": True,
        "address_flags": {"no_doorcode": True},
        "item_flags": {},
        "zone": "zone-c",
        "tt": "tt-3",
        "event_type": "delivery",
    })


def _input_missing_items() -> RiskInput:
    """Недовоз / нехватка позиций."""
    return RiskInput.from_dict({
        "order_id": "ord-4",
        "courier_id": "c-4",
        "minutes_to_deadline": 30,
        "eta_minutes": 10,
        "active_orders_count": 1,
        "has_customer_comment": False,
        "address_flags": {},
        "item_flags": {"partial_missing": True, "shortage": True},
        "zone": "zone-d",
        "tt": "tt-4",
        "event_type": "delivery",
    })


def _input_fragile() -> RiskInput:
    """Хрупкий груз / стекло."""
    return RiskInput.from_dict({
        "order_id": "ord-5",
        "courier_id": "c-5",
        "minutes_to_deadline": 40,
        "eta_minutes": 15,
        "active_orders_count": 2,
        "has_customer_comment": False,
        "address_flags": {},
        "item_flags": {"fragile": True, "glass": True},
        "zone": "zone-e",
        "tt": "tt-5",
        "event_type": "delivery",
    })


def _input_courier_overload() -> RiskInput:
    """Много активных заказов у курьера."""
    return RiskInput.from_dict({
        "order_id": "ord-6",
        "courier_id": "c-6",
        "minutes_to_deadline": 25,
        "eta_minutes": 20,
        "active_orders_count": 6,
        "has_customer_comment": False,
        "address_flags": {},
        "item_flags": {},
        "zone": "zone-f",
        "tt": "tt-6",
        "event_type": "delivery",
    })


def _input_return_order() -> RiskInput:
    """Возврат/отмена."""
    return RiskInput.from_dict({
        "order_id": "ord-7",
        "courier_id": "c-7",
        "minutes_to_deadline": 50,
        "eta_minutes": 10,
        "active_orders_count": 1,
        "has_customer_comment": False,
        "address_flags": {},
        "item_flags": {},
        "zone": "zone-g",
        "tt": "tt-7",
        "event_type": "return",
    })


def run_smoke() -> bool:
    """Прогоняет дымовые сценарии: RiskEngine.evaluate + RecommendationEngine.recommend.

    Returns:
        True, если все сценарии прошли без ошибок и инварианты выполнены.
    """
    engine = RiskEngine()
    rec_engine = RecommendationEngine()

    # 1) Нет риска — результат может быть None или любой низкий риск
    inp_no = _input_no_risk()
    risk_no = engine.evaluate(inp_no)
    rec_no = rec_engine.recommend(risk_no)
    if risk_no is not None:
        # Если что-то сработало — рекомендация должна быть
        assert rec_no is not None
        assert rec_no.short_message
        assert isinstance(rec_no.action_steps, list)

    # 2) Риск опоздания — ожидаем late_delivery_risk
    inp_late = _input_late_delivery()
    risk_late = engine.evaluate(inp_late)
    assert risk_late is not None, "late_delivery input should yield a risk"
    assert risk_late.risk_type == "late_delivery_risk"
    rec_late = rec_engine.recommend(risk_late)
    assert rec_late is not None
    assert "опоздан" in rec_late.short_message.lower() or "дедлайн" in rec_late.short_message.lower()
    assert len(rec_late.action_steps) >= 1

    # 3) Контакт с клиентом
    inp_cc = _input_customer_contact()
    risk_cc = engine.evaluate(inp_cc)
    assert risk_cc is not None
    assert risk_cc.risk_type == "customer_contact_risk"
    rec_cc = rec_engine.recommend(risk_cc)
    assert rec_cc is not None
    assert rec_cc.short_message and rec_cc.action_steps

    # 4) Недовоз
    inp_miss = _input_missing_items()
    risk_miss = engine.evaluate(inp_miss)
    assert risk_miss is not None
    assert risk_miss.risk_type == "missing_items_risk"
    rec_miss = rec_engine.recommend(risk_miss)
    assert rec_miss is not None

    # 5) Хрупкий груз
    inp_frag = _input_fragile()
    risk_frag = engine.evaluate(inp_frag)
    assert risk_frag is not None
    assert risk_frag.risk_type == "fragile_goods_risk"
    rec_frag = rec_engine.recommend(risk_frag)
    assert rec_frag is not None

    # 6) Перегрузка курьера
    inp_over = _input_courier_overload()
    risk_over = engine.evaluate(inp_over)
    assert risk_over is not None
    assert risk_over.risk_type == "courier_overload_risk"
    rec_over = rec_engine.recommend(risk_over)
    assert rec_over is not None

    # 7) Возврат
    inp_ret = _input_return_order()
    risk_ret = engine.evaluate(inp_ret)
    assert risk_ret is not None
    assert risk_ret.risk_type == "return_order_risk"
    rec_ret = rec_engine.recommend(risk_ret)
    assert rec_ret is not None

    # 8) RecommendationEngine(None) -> None
    assert rec_engine.recommend(None) is None

    return True


if __name__ == "__main__":
    try:
        ok = run_smoke()
        if ok:
            print("OK smoke_risk_engine")
            raise SystemExit(0)
    except Exception as e:
        print(f"FAIL smoke_risk_engine: {e}")
        raise SystemExit(1)
    raise SystemExit(1)
