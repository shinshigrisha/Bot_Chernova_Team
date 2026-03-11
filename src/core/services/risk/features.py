"""Input features for the proactive risk engine."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class RiskInput:
    """Input context for rule-based risk evaluation."""

    order_id: str
    courier_id: str
    minutes_to_deadline: int
    eta_minutes: int
    active_orders_count: int
    has_customer_comment: bool
    address_flags: dict[str, Any]
    item_flags: dict[str, Any]
    zone: str
    tt: str
    event_type: str

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> RiskInput:
        return cls(
            order_id=str(data.get("order_id", "")),
            courier_id=str(data.get("courier_id", "")),
            minutes_to_deadline=int(data.get("minutes_to_deadline", 0)),
            eta_minutes=int(data.get("eta_minutes", 0)),
            active_orders_count=int(data.get("active_orders_count", 0)),
            has_customer_comment=bool(data.get("has_customer_comment", False)),
            address_flags=dict(data.get("address_flags") or {}),
            item_flags=dict(data.get("item_flags") or {}),
            zone=str(data.get("zone", "")),
            tt=str(data.get("tt", "")),
            event_type=str(data.get("event_type", "")),
        )
