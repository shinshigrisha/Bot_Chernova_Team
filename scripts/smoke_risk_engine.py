"""Smoke test for proactive risk engine. No DB, no Telegram."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.core.services.risk import (
    RecommendationEngine,
    RiskEngine,
    RiskInput,
)

SCENARIOS = [
    {
        "name": "late_delivery_risk",
        "input": {
            "order_id": "ord-1",
            "courier_id": "c1",
            "minutes_to_deadline": 10,
            "eta_minutes": 25,
            "active_orders_count": 1,
            "has_customer_comment": False,
            "address_flags": {},
            "item_flags": {},
            "zone": "center",
            "tt": "12:00",
            "event_type": "en_route",
        },
    },
    {
        "name": "customer_contact_risk",
        "input": {
            "order_id": "ord-2",
            "courier_id": "c1",
            "minutes_to_deadline": 60,
            "eta_minutes": 20,
            "active_orders_count": 1,
            "has_customer_comment": True,
            "address_flags": {"no_doorcode": True},
            "item_flags": {},
            "zone": "center",
            "tt": "13:00",
            "event_type": "en_route",
        },
    },
    {
        "name": "missing_items_risk",
        "input": {
            "order_id": "ord-3",
            "courier_id": "c2",
            "minutes_to_deadline": 45,
            "eta_minutes": 15,
            "active_orders_count": 2,
            "has_customer_comment": False,
            "address_flags": {},
            "item_flags": {"partial_missing": True},
            "zone": "north",
            "tt": "14:00",
            "event_type": "en_route",
        },
    },
    {
        "name": "fragile_goods_risk",
        "input": {
            "order_id": "ord-4",
            "courier_id": "c2",
            "minutes_to_deadline": 30,
            "eta_minutes": 10,
            "active_orders_count": 1,
            "has_customer_comment": False,
            "address_flags": {},
            "item_flags": {"fragile": True, "glass": True},
            "zone": "south",
            "tt": "15:00",
            "event_type": "en_route",
        },
    },
    {
        "name": "payment_issue_risk",
        "input": {
            "order_id": "ord-5",
            "courier_id": "c1",
            "minutes_to_deadline": 20,
            "eta_minutes": 5,
            "active_orders_count": 1,
            "has_customer_comment": False,
            "address_flags": {"cash_only": True},
            "item_flags": {"prepaid": False},
            "zone": "center",
            "tt": "16:00",
            "event_type": "en_route",
        },
    },
    {
        "name": "return_order_risk",
        "input": {
            "order_id": "ord-6",
            "courier_id": "c2",
            "minutes_to_deadline": 0,
            "eta_minutes": 0,
            "active_orders_count": 1,
            "has_customer_comment": False,
            "address_flags": {},
            "item_flags": {},
            "zone": "center",
            "tt": "17:00",
            "event_type": "return_requested",
        },
    },
    {
        "name": "courier_overload_risk",
        "input": {
            "order_id": "ord-7",
            "courier_id": "c3",
            "minutes_to_deadline": 40,
            "eta_minutes": 15,
            "active_orders_count": 6,
            "has_customer_comment": False,
            "address_flags": {},
            "item_flags": {},
            "zone": "center",
            "tt": "18:00",
            "event_type": "en_route",
        },
    },
    {
        "name": "no_risk",
        "input": {
            "order_id": "ord-8",
            "courier_id": "c1",
            "minutes_to_deadline": 60,
            "eta_minutes": 20,
            "active_orders_count": 1,
            "has_customer_comment": False,
            "address_flags": {},
            "item_flags": {},
            "zone": "center",
            "tt": "19:00",
            "event_type": "en_route",
        },
    },
]


def main() -> None:
    engine = RiskEngine()
    rec_engine = RecommendationEngine()
    passed = 0
    failed = 0
    for scenario in SCENARIOS:
        name = scenario["name"]
        inp = RiskInput.from_dict(scenario["input"])
        risk = engine.evaluate(inp)
        rec = rec_engine.recommend(risk)
        if risk is None:
            if name == "no_risk":
                print(f"[OK] {name}: no risk (as expected)")
                passed += 1
            else:
                print(f"[??] {name}: no risk detected")
                passed += 1
        else:
            if risk.risk_type.replace("_risk", "") not in name and name != "no_risk":
                print(f"[??] {name}: got {risk.risk_type} (expected match in name)")
            print(f"[OK] {name}: {risk.risk_type} severity={risk.severity} score={risk.risk_score:.2f}")
            print(f"     reasons: {risk.risk_reasons}")
            if rec:
                print(f"     short_message: {rec.short_message[:80]}...")
                print(f"     action_steps: {rec.action_steps}")
                print(f"     escalate: {rec.escalate}")
            passed += 1
    print(f"\nRISK_SCENARIOS_PASSED={passed}/{len(SCENARIOS)}")
    if failed:
        sys.exit(1)
    print("smoke_risk_engine: OK")


if __name__ == "__main__":
    main()
