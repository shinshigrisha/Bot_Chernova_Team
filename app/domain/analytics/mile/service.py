from __future__ import annotations

from collections import defaultdict

from .calculators import (
    MileOrder,
    filter_successful_orders,
    calc_delay_rate,
    calc_assembly_delay_rate,
    calc_avg_delivery_wait,
    top_couriers_by_delay,
    top_problematic_ziz,
    peak_hours,
)


def build_mile_analysis(orders: list[MileOrder]) -> dict:
    successful = filter_successful_orders(orders)

    ds_groups: dict[str, list[MileOrder]] = defaultdict(list)
    for order in successful:
        ds_groups[order.ds].append(order)

    ds_blocks = []
    for ds_name, ds_orders in ds_groups.items():
        tt_groups: dict[str, list[MileOrder]] = defaultdict(list)
        for order in ds_orders:
            tt_groups[order.tt].append(order)

        tt_blocks = []
        for tt_name, tt_orders in tt_groups.items():
            tt_blocks.append(
                {
                    "tt_name": tt_name,
                    "delay_rate": calc_delay_rate(tt_orders),
                    "assembly_delay_rate": calc_assembly_delay_rate(tt_orders),
                    "avg_delivery_wait": calc_avg_delivery_wait(tt_orders),
                    "top_couriers": top_couriers_by_delay(tt_orders, limit=10),
                    "problematic_ziz": top_problematic_ziz(tt_orders, limit=5),
                    "peak_hours": peak_hours(tt_orders, limit=5),
                }
            )

        ds_blocks.append(
            {
                "ds_name": ds_name,
                "metrics": {
                    "total_orders": len(ds_orders),
                    "successful_orders": len(ds_orders),
                    "delay_rate": calc_delay_rate(ds_orders),
                    "assembly_delay_rate": calc_assembly_delay_rate(ds_orders),
                    "avg_delivery_wait": calc_avg_delivery_wait(ds_orders),
                },
                "tt_blocks": sorted(tt_blocks, key=lambda x: x["delay_rate"], reverse=True),
            }
        )

    ds_blocks.sort(key=lambda x: x["metrics"]["delay_rate"], reverse=True)

    return {
        "analysis_type": "mile_analytics",
        "summary": "Анализ мили выполнен по ДС -> ТТ с выделением проблемных курьеров, ЗиЗ и пиковых часов.",
        "ds_blocks": ds_blocks,
        "recommendations": [],
        "data_limitations": [],
    }

