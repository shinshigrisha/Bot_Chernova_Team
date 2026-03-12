"""View mart_orders_enriched — нормализованные заказы и расчётные метрики (только Успешно завершен).

Revision ID: 011_mart_orders_enriched
Revises: 010_raw_orders
Create Date: 2026-03-12

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "011_mart_orders_enriched"
down_revision: Union[str, None] = "010_raw_orders"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

MART_ORDERS_ENRICHED_SQL = r"""
CREATE VIEW mart_orders_enriched AS
WITH base AS (
    SELECT
        "Наименование ТТ"                               AS tt_name,
        "Сервис"                                        AS service_name,
        "Служба"                                        AS ziz_name,
        "Курьер"                                        AS courier_name,
        "Ген. заказ"                                    AS gen_order_id,
        "Заказ"                                         AS order_id,
        "Статус заказа"                                 AS order_status,
        "Доставка в срок"                               AS delivery_on_time,
        CAST(NULLIF(TRIM("Дата доставки С"), '') AS TIMESTAMP)            AS delivery_from_ts,
        CAST(NULLIF(TRIM("Дата доставки До"), '') AS TIMESTAMP)           AS delivery_to_ts,
        CAST(NULLIF(TRIM("Дата и время оформления"), '') AS TIMESTAMP)    AS created_ts,
        CAST(NULLIF(TRIM("Дата начала сборки"), '') AS TIMESTAMP)         AS assembly_start_ts,
        CAST(NULLIF(TRIM("Дата окончания сборки"), '') AS TIMESTAMP)      AS assembly_end_ts,
        CAST(NULLIF(TRIM("Дата начала доставки"), '') AS TIMESTAMP)       AS delivery_start_ts,
        CAST(NULLIF(TRIM("Дата окончания доставки"), '') AS TIMESTAMP)   AS delivery_end_ts,
        CAST(REPLACE(NULLIF(TRIM("Время сборки"), ''), ',', '.') AS NUMERIC)              AS assembly_minutes_raw,
        CAST(REPLACE(NULLIF(TRIM("Время ожидания сборки"), ''), ',', '.') AS NUMERIC)     AS assembly_wait_minutes_raw,
        CAST(REPLACE(NULLIF(TRIM("Время доставки"), ''), ',', '.') AS NUMERIC)            AS delivery_minutes_raw,
        CAST(REPLACE(NULLIF(TRIM("Время ожидания доставки"), ''), ',', '.') AS NUMERIC)   AS delivery_wait_minutes_raw
    FROM raw_orders
    WHERE "Статус заказа" = 'Успешно завершен'
),
norms AS (
    SELECT
        *,
        CASE
            WHEN service_name IN ('Сервис Экспресс 15 мин') THEN 15
            WHEN service_name IN ('Экспресс доставка', 'Сервис а') THEN 30
            WHEN service_name IN ('Доставка за 30 минут', '30 минут(без слотов)', 'Доставка за 30 минут (без слотов)') THEN 30
            WHEN service_name IN ('Доставка за 1 час', 'Больше продуктов за 1 час', 'Доставка ВкусВилл Бизнес за 1 час') THEN 60
            WHEN service_name IN ('Доставка за 2 часа', 'Больше продуктов за 2 часа') THEN 120
            ELSE EXTRACT(EPOCH FROM (delivery_to_ts - delivery_from_ts)) / 60.0
        END AS service_total_minutes_norm,
        CASE
            WHEN service_name IN ('Сервис Экспресс 15 мин') THEN 5
            WHEN service_name IN ('Экспресс доставка', 'Сервис а') THEN 10
            WHEN service_name IN ('Доставка за 30 минут', '30 минут(без слотов)', 'Доставка за 30 минут (без слотов)') THEN 10
            WHEN service_name IN ('Доставка за 1 час', 'Больше продуктов за 1 час', 'Доставка ВкусВилл Бизнес за 1 час') THEN 15
            WHEN service_name IN ('Доставка за 2 часа', 'Больше продуктов за 2 часа') THEN 30
            ELSE NULL
        END AS assembly_minutes_norm
    FROM base
),
calc AS (
    SELECT
        *,
        COALESCE(
            assembly_minutes_raw,
            EXTRACT(EPOCH FROM (assembly_end_ts - assembly_start_ts)) / 60.0
        ) AS assembly_minutes,
        COALESCE(
            assembly_wait_minutes_raw,
            CASE
                WHEN assembly_start_ts IS NOT NULL AND created_ts IS NOT NULL
                THEN EXTRACT(EPOCH FROM (assembly_start_ts - created_ts)) / 60.0
            END
        ) AS assembly_wait_minutes,
        COALESCE(
            delivery_minutes_raw,
            EXTRACT(EPOCH FROM (delivery_end_ts - delivery_start_ts)) / 60.0
        ) AS delivery_minutes,
        COALESCE(
            delivery_wait_minutes_raw,
            CASE
                WHEN delivery_start_ts IS NOT NULL AND assembly_end_ts IS NOT NULL
                THEN EXTRACT(EPOCH FROM (delivery_start_ts - assembly_end_ts)) / 60.0
            END
        ) AS delivery_wait_minutes,
        EXTRACT(EPOCH FROM (delivery_to_ts - delivery_from_ts)) / 60.0 AS service_window_minutes,
        EXTRACT(EPOCH FROM (delivery_to_ts - delivery_start_ts)) / 60.0 AS remaining_minutes_at_take,
        CASE
            WHEN delivery_from_ts IS NOT NULL
             AND delivery_to_ts IS NOT NULL
             AND delivery_start_ts IS NOT NULL
             AND delivery_to_ts > delivery_from_ts
            THEN 100.0 * EXTRACT(EPOCH FROM (delivery_to_ts - delivery_start_ts))
                 / EXTRACT(EPOCH FROM (delivery_to_ts - delivery_from_ts))
        END AS remaining_pct_at_take,
        EXTRACT(EPOCH FROM (delivery_end_ts - delivery_from_ts)) / 60.0 AS total_fact_minutes,
        CASE WHEN delivery_end_ts > delivery_to_ts THEN 1 ELSE 0 END AS is_late_fact,
        CASE WHEN delivery_on_time = 'Просрочен' THEN 1 ELSE 0 END AS is_late_by_flag,
        CASE WHEN delivery_on_time = 'офлайн' THEN 1 ELSE 0 END AS is_offline,
        CASE WHEN delivery_end_ts >= delivery_to_ts + INTERVAL '15 minute' THEN 1 ELSE 0 END AS is_late_15_plus,
        CASE
            WHEN COALESCE(
                assembly_minutes_raw,
                EXTRACT(EPOCH FROM (assembly_end_ts - assembly_start_ts)) / 60.0
            ) > assembly_minutes_norm
            THEN 1 ELSE 0
        END AS is_assembly_over_norm,
        CASE
            WHEN EXTRACT(EPOCH FROM (delivery_end_ts - delivery_from_ts)) / 60.0 > service_total_minutes_norm
            THEN 1 ELSE 0
        END AS is_total_over_norm,
        CASE
            WHEN delivery_start_ts IS NOT NULL
             AND delivery_to_ts IS NOT NULL
             AND delivery_start_ts >= delivery_to_ts
            THEN 1 ELSE 0
        END AS is_taken_with_negative_timer,
        CASE
            WHEN delivery_start_ts IS NOT NULL
             AND delivery_end_ts IS NOT NULL
             AND delivery_end_ts < delivery_start_ts
            THEN 1 ELSE 0
        END AS is_finish_before_take_anomaly,
        CASE
            WHEN delivery_start_ts IS NOT NULL
             AND delivery_to_ts IS NOT NULL
             AND delivery_from_ts IS NOT NULL
             AND (EXTRACT(EPOCH FROM (delivery_to_ts - delivery_start_ts)) / 60.0) > 0
             AND (
                 100.0 * EXTRACT(EPOCH FROM (delivery_to_ts - delivery_start_ts))
                 / NULLIF(EXTRACT(EPOCH FROM (delivery_to_ts - delivery_from_ts)), 0)
             ) > 60
             AND delivery_on_time = 'Просрочен'
            THEN 1 ELSE 0
        END AS is_clean_courier_violation,
        CASE
            WHEN delivery_start_ts IS NOT NULL
             AND delivery_to_ts IS NOT NULL
             AND delivery_from_ts IS NOT NULL
             AND (EXTRACT(EPOCH FROM (delivery_to_ts - delivery_start_ts)) / 60.0) > 0
             AND (
                 100.0 * EXTRACT(EPOCH FROM (delivery_to_ts - delivery_start_ts))
                 / NULLIF(EXTRACT(EPOCH FROM (delivery_to_ts - delivery_from_ts)), 0)
             ) < 20
             AND delivery_on_time = 'Успех'
            THEN 1 ELSE 0
        END AS is_saved_order
    FROM norms
)
SELECT * FROM calc
"""


def upgrade() -> None:
    op.execute(sa.text(MART_ORDERS_ENRICHED_SQL))


def downgrade() -> None:
    op.execute(sa.text("DROP VIEW IF EXISTS mart_orders_enriched"))
