"""Views: mart_service_rollout_cluster, mart_service_rollout_tt, mart_tt_quality, mart_courier_violations.

Revision ID: 012_mart_rollout_quality_violations
Revises: 011_mart_orders_enriched
Create Date: 2026-03-12

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "012_mart_views"
down_revision: Union[str, None] = "011_mart_orders_enriched"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

VIEW_ROLLOUT_CLUSTER = """
CREATE OR REPLACE VIEW mart_service_rollout_cluster AS
SELECT
    service_name,
    COUNT(*) AS orders_cnt,
    ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 2) AS rollout_pct
FROM mart_orders_enriched
GROUP BY service_name
ORDER BY orders_cnt DESC
"""

VIEW_ROLLOUT_TT = """
CREATE OR REPLACE VIEW mart_service_rollout_tt AS
SELECT
    tt_name,
    service_name,
    COUNT(*) AS orders_cnt,
    ROUND(
        100.0 * COUNT(*) / SUM(COUNT(*)) OVER (PARTITION BY tt_name),
        2
    ) AS rollout_pct
FROM mart_orders_enriched
GROUP BY tt_name, service_name
"""

VIEW_TT_QUALITY = """
CREATE OR REPLACE VIEW mart_tt_quality AS
SELECT
    tt_name,
    COUNT(*) AS success_orders,
    COUNT(DISTINCT courier_name) AS couriers_cnt,
    ROUND(100.0 * AVG(is_assembly_over_norm), 2) AS assembly_over_norm_pct,
    ROUND(100.0 * AVG(is_total_over_norm), 2) AS total_over_norm_pct,
    ROUND(100.0 * AVG(CASE WHEN is_late_by_flag = 1 OR is_offline = 1 THEN 1 ELSE 0 END), 2) AS late_with_offline_pct,
    ROUND(100.0 * AVG(is_late_by_flag), 2) AS late_flag_pct,
    ROUND(100.0 * AVG(is_late_15_plus), 2) AS late_15_plus_pct,
    ROUND(AVG(delivery_wait_minutes), 2) AS avg_delivery_wait_minutes,
    ROUND(AVG(assembly_wait_minutes), 2) AS avg_assembly_wait_minutes,
    ROUND(AVG(assembly_minutes), 2) AS avg_assembly_minutes,
    ROUND(AVG(delivery_minutes), 2) AS avg_delivery_minutes
FROM mart_orders_enriched
GROUP BY tt_name
"""

VIEW_COURIER_VIOLATIONS = """
CREATE OR REPLACE VIEW mart_courier_violations AS
SELECT
    tt_name,
    ziz_name,
    courier_name,
    COUNT(*) AS success_orders,
    SUM(is_late_by_flag) AS late_orders,
    ROUND(100.0 * AVG(is_late_by_flag), 2) AS late_pct,
    SUM(is_clean_courier_violation) AS clean_courier_violations,
    ROUND(100.0 * AVG(is_clean_courier_violation), 2) AS clean_courier_violations_pct,
    ROUND(AVG(delivery_wait_minutes), 2) AS avg_delivery_wait_minutes,
    ROUND(AVG(delivery_minutes), 2) AS avg_delivery_minutes
FROM mart_orders_enriched
GROUP BY tt_name, ziz_name, courier_name
"""


def upgrade() -> None:
    op.execute(sa.text(VIEW_ROLLOUT_CLUSTER))
    op.execute(sa.text(VIEW_ROLLOUT_TT))
    op.execute(sa.text(VIEW_TT_QUALITY))
    op.execute(sa.text(VIEW_COURIER_VIOLATIONS))


def downgrade() -> None:
    op.execute(sa.text("DROP VIEW IF EXISTS mart_courier_violations"))
    op.execute(sa.text("DROP VIEW IF EXISTS mart_tt_quality"))
    op.execute(sa.text("DROP VIEW IF EXISTS mart_service_rollout_tt"))
    op.execute(sa.text("DROP VIEW IF EXISTS mart_service_rollout_cluster"))
