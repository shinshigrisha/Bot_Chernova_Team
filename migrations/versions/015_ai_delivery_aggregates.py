"""Aggregate tables for ai_delivery schema.

Revision ID: 015_ai_delivery_aggregates
Revises: 014_ai_delivery_fact_tables
Create Date: 2026-03-12

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "015_ai_delivery_aggregates"
down_revision: Union[str, None] = "014_ai_delivery_fact_tables"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _common_mile_metric_columns() -> list[sa.Column]:
    """Набор метрик мили, которые могут использоваться в разных агрегатах."""

    return [
        sa.Column("orders_total", sa.Integer(), nullable=True),
        sa.Column("orders_success", sa.Integer(), nullable=True),
        sa.Column("orders_late", sa.Integer(), nullable=True),
        sa.Column("orders_late_15_plus", sa.Integer(), nullable=True),
        sa.Column("saved_orders", sa.Integer(), nullable=True),
        sa.Column("clean_courier_violations", sa.Integer(), nullable=True),
        sa.Column("avg_delivery_minutes", sa.Numeric(), nullable=True),
        sa.Column("avg_delivery_wait_minutes", sa.Numeric(), nullable=True),
        sa.Column("avg_assembly_minutes", sa.Numeric(), nullable=True),
        sa.Column("avg_assembly_wait_minutes", sa.Numeric(), nullable=True),
    ]


def _common_quality_metric_columns() -> list[sa.Column]:
    """Набор метрик качества/жалоб для агрегатов."""

    return [
        sa.Column("complaints_total", sa.Integer(), nullable=True),
        sa.Column("complaints_per_100_orders", sa.Numeric(), nullable=True),
        sa.Column("damage_count", sa.Integer(), nullable=True),
        sa.Column("return_count", sa.Integer(), nullable=True),
        sa.Column("courier_issue_count", sa.Integer(), nullable=True),
        sa.Column("store_issue_count", sa.Integer(), nullable=True),
    ]


def upgrade() -> None:
    # Агрегаты по ДС за день
    op.create_table(
        "agg_ds_daily",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("ds_name", sa.Text(), nullable=False),
        sa.Column("service_name", sa.Text(), nullable=True),
        *_common_mile_metric_columns(),
        *_common_quality_metric_columns(),
        sa.Column("load_batch_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "load_ts",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name="pk_agg_ds_daily"),
        schema="ai_delivery",
    )
    op.create_index(
        "ix_agg_ds_daily_date_ds",
        "agg_ds_daily",
        ["date", "ds_name"],
        unique=False,
        schema="ai_delivery",
    )

    # Агрегаты по ДС по часам
    op.create_table(
        "agg_ds_hourly",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("hour", sa.Integer(), nullable=False),
        sa.Column("ds_name", sa.Text(), nullable=False),
        sa.Column("service_name", sa.Text(), nullable=True),
        *_common_mile_metric_columns(),
        sa.Column("load_batch_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "load_ts",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name="pk_agg_ds_hourly"),
        schema="ai_delivery",
    )
    op.create_index(
        "ix_agg_ds_hourly_date_hour_ds",
        "agg_ds_hourly",
        ["date", "hour", "ds_name"],
        unique=False,
        schema="ai_delivery",
    )

    # Агрегаты по ЗиЗ за день
    op.create_table(
        "agg_ziz_daily",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("ziz_name", sa.Text(), nullable=False),
        sa.Column("service_name", sa.Text(), nullable=True),
        *_common_mile_metric_columns(),
        *_common_quality_metric_columns(),
        sa.Column("load_batch_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "load_ts",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name="pk_agg_ziz_daily"),
        schema="ai_delivery",
    )
    op.create_index(
        "ix_agg_ziz_daily_date_ziz",
        "agg_ziz_daily",
        ["date", "ziz_name"],
        unique=False,
        schema="ai_delivery",
    )

    # Агрегаты по курьерам за день
    op.create_table(
        "agg_courier_daily",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("courier_name", sa.Text(), nullable=False),
        sa.Column("ds_name", sa.Text(), nullable=True),
        sa.Column("ziz_name", sa.Text(), nullable=True),
        *_common_mile_metric_columns(),
        *_common_quality_metric_columns(),
        sa.Column("load_batch_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "load_ts",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name="pk_agg_courier_daily"),
        schema="ai_delivery",
    )
    op.create_index(
        "ix_agg_courier_daily_date_courier",
        "agg_courier_daily",
        ["date", "courier_name"],
        unique=False,
        schema="ai_delivery",
    )

    # Агрегаты по ТТ за день
    op.create_table(
        "agg_tt_daily",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("tt_name", sa.Text(), nullable=False),
        sa.Column("ds_name", sa.Text(), nullable=True),
        sa.Column("ziz_name", sa.Text(), nullable=True),
        *_common_mile_metric_columns(),
        *_common_quality_metric_columns(),
        sa.Column("load_batch_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "load_ts",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name="pk_agg_tt_daily"),
        schema="ai_delivery",
    )
    op.create_index(
        "ix_agg_tt_daily_date_tt",
        "agg_tt_daily",
        ["date", "tt_name"],
        unique=False,
        schema="ai_delivery",
    )

    # Общий агрегат качества по дню (гибкий разрез по уровню)
    op.create_table(
        "agg_quality_daily",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("level", sa.Text(), nullable=False),  # например: ds / tt / ziz / courier
        sa.Column("entity_name", sa.Text(), nullable=False),
        sa.Column("ds_name", sa.Text(), nullable=True),
        sa.Column("tt_name", sa.Text(), nullable=True),
        sa.Column("ziz_name", sa.Text(), nullable=True),
        sa.Column("courier_name", sa.Text(), nullable=True),
        *_common_quality_metric_columns(),
        sa.Column("load_batch_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "load_ts",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name="pk_agg_quality_daily"),
        schema="ai_delivery",
    )
    op.create_index(
        "ix_agg_quality_daily_date_level_entity",
        "agg_quality_daily",
        ["date", "level", "entity_name"],
        unique=False,
        schema="ai_delivery",
    )


def downgrade() -> None:
    op.drop_index(
        "ix_agg_quality_daily_date_level_entity",
        table_name="agg_quality_daily",
        schema="ai_delivery",
    )
    op.drop_table("agg_quality_daily", schema="ai_delivery")

    op.drop_index(
        "ix_agg_tt_daily_date_tt",
        table_name="agg_tt_daily",
        schema="ai_delivery",
    )
    op.drop_table("agg_tt_daily", schema="ai_delivery")

    op.drop_index(
        "ix_agg_courier_daily_date_courier",
        table_name="agg_courier_daily",
        schema="ai_delivery",
    )
    op.drop_table("agg_courier_daily", schema="ai_delivery")

    op.drop_index(
        "ix_agg_ziz_daily_date_ziz",
        table_name="agg_ziz_daily",
        schema="ai_delivery",
    )
    op.drop_table("agg_ziz_daily", schema="ai_delivery")

    op.drop_index(
        "ix_agg_ds_hourly_date_hour_ds",
        table_name="agg_ds_hourly",
        schema="ai_delivery",
    )
    op.drop_table("agg_ds_hourly", schema="ai_delivery")

    op.drop_index(
        "ix_agg_ds_daily_date_ds",
        table_name="agg_ds_daily",
        schema="ai_delivery",
    )
    op.drop_table("agg_ds_daily", schema="ai_delivery")

