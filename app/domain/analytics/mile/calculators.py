from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable
from collections import defaultdict


@dataclass
class MileOrder:
    ds: str
    vs: str | None
    tt: str
    courier_name: str | None
    ziz: str | None
    status: str
    delay_flag: bool
    assembly_delay_flag: bool = False
    delivery_wait_minutes: float | None = None
    hour_bucket: str | None = None
    trip_id: str | None = None
    replenishment_flag: bool = False
    negative_replenishment_flag: bool = False


def filter_successful_orders(orders: Iterable[MileOrder]) -> list[MileOrder]:
    return [o for o in orders if o.status == "Успешно завершен"]


def calc_delay_rate(orders: Iterable[MileOrder]) -> float:
    orders = list(orders)
    if not orders:
        return 0.0
    delayed = sum(1 for o in orders if o.delay_flag)
    return round(delayed / len(orders) * 100, 2)


def calc_assembly_delay_rate(orders: Iterable[MileOrder]) -> float:
    orders = list(orders)
    if not orders:
        return 0.0
    delayed = sum(1 for o in orders if o.assembly_delay_flag)
    return round(delayed / len(orders) * 100, 2)


def calc_avg_delivery_wait(orders: Iterable[MileOrder]) -> float:
    values = [o.delivery_wait_minutes for o in orders if o.delivery_wait_minutes is not None]
    if not values:
        return 0.0
    return round(sum(values) / len(values), 2)


def top_couriers_by_delay(orders: Iterable[MileOrder], limit: int = 10) -> list[dict]:
    stats: dict[str, dict] = defaultdict(lambda: {"orders": 0, "delayed_orders": 0})
    for o in orders:
        if not o.courier_name:
            continue
        stats[o.courier_name]["orders"] += 1
        if o.delay_flag:
            stats[o.courier_name]["delayed_orders"] += 1

    result = []
    for courier_name, s in stats.items():
        orders_count = s["orders"]
        delayed_orders = s["delayed_orders"]
        delay_rate = round(delayed_orders / orders_count * 100, 2) if orders_count else 0.0
        result.append({
            "courier_name": courier_name,
            "orders": orders_count,
            "delayed_orders": delayed_orders,
            "delay_rate": delay_rate,
        })

    result.sort(key=lambda x: (x["delay_rate"], x["delayed_orders"]), reverse=True)
    return result[:limit]


def top_problematic_ziz(orders: Iterable[MileOrder], limit: int = 10) -> list[dict]:
    stats: dict[str, dict] = defaultdict(lambda: {"orders": 0, "delayed_orders": 0})
    for o in orders:
        if not o.ziz:
            continue
        stats[o.ziz]["orders"] += 1
        if o.delay_flag:
            stats[o.ziz]["delayed_orders"] += 1

    result = []
    for ziz, s in stats.items():
        orders_count = s["orders"]
        delayed_orders = s["delayed_orders"]
        delay_rate = round(delayed_orders / orders_count * 100, 2) if orders_count else 0.0
        result.append({
            "ziz": ziz,
            "orders": orders_count,
            "delayed_orders": delayed_orders,
            "delay_rate": delay_rate,
        })

    result.sort(key=lambda x: (x["delay_rate"], x["delayed_orders"]), reverse=True)
    return result[:limit]


def peak_hours(orders: Iterable[MileOrder], limit: int = 5) -> list[dict]:
    stats: dict[str, dict] = defaultdict(lambda: {"orders": 0, "delayed_orders": 0})
    for o in orders:
        if not o.hour_bucket:
            continue
        stats[o.hour_bucket]["orders"] += 1
        if o.delay_flag:
            stats[o.hour_bucket]["delayed_orders"] += 1

    result = []
    for hour, s in stats.items():
        delay_rate = round(s["delayed_orders"] / s["orders"] * 100, 2) if s["orders"] else 0.0
        result.append({
            "hour": hour,
            "orders": s["orders"],
            "delayed_orders": s["delayed_orders"],
            "delay_rate": delay_rate,
        })

    result.sort(key=lambda x: (x["orders"], x["delay_rate"]), reverse=True)
    return result[:limit]

