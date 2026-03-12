"""Fact tables for ai_delivery schema: fact_delivery_orders, fact_delivery_complaints.

Revision ID: 014_ai_delivery_fact_tables
Revises: 013_ai_delivery_schema
Create Date: 2026-03-12

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "014_ai_delivery_fact_tables"
down_revision: Union[str, None] = "013_ai_delivery_schema"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Основная факт-таблица заказов доставки
    op.create_table(
        "fact_delivery_orders",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("order_id", sa.Text(), nullable=False),
        sa.Column("gen_order_id", sa.Text(), nullable=True),
        sa.Column("tt_name", sa.Text(), nullable=True),
        sa.Column("service_name", sa.Text(), nullable=True),
        sa.Column("ziz_name", sa.Text(), nullable=True),
        sa.Column("courier_name", sa.Text(), nullable=True),
        sa.Column("created_ts", sa.DateTime(timezone=True), nullable=True),
        sa.Column("assembly_start_ts", sa.DateTime(timezone=True), nullable=True),
        sa.Column("assembly_end_ts", sa.DateTime(timezone=True), nullable=True),
        sa.Column("delivery_start_ts", sa.DateTime(timezone=True), nullable=True),
        sa.Column("delivery_end_ts", sa.DateTime(timezone=True), nullable=True),
        sa.Column("delivery_from_ts", sa.DateTime(timezone=True), nullable=True),
        sa.Column("delivery_to_ts", sa.DateTime(timezone=True), nullable=True),
        sa.Column("assembly_minutes", sa.Numeric(), nullable=True),
        sa.Column("assembly_wait_minutes", sa.Numeric(), nullable=True),
        sa.Column("delivery_minutes", sa.Numeric(), nullable=True),
        sa.Column("delivery_wait_minutes", sa.Numeric(), nullable=True),
        sa.Column("service_window_minutes", sa.Numeric(), nullable=True),
        sa.Column("remaining_minutes_at_take", sa.Numeric(), nullable=True),
        sa.Column("remaining_pct_at_take", sa.Numeric(), nullable=True),
        sa.Column("total_fact_minutes", sa.Numeric(), nullable=True),
        sa.Column("is_late_fact", sa.Boolean(), nullable=True),
        sa.Column("is_late_by_flag", sa.Boolean(), nullable=True),
        sa.Column("is_offline", sa.Boolean(), nullable=True),
        sa.Column("is_late_15_plus", sa.Boolean(), nullable=True),
        sa.Column("is_assembly_over_norm", sa.Boolean(), nullable=True),
        sa.Column("is_total_over_norm", sa.Boolean(), nullable=True),
        sa.Column("is_taken_with_negative_timer", sa.Boolean(), nullable=True),
        sa.Column("is_finish_before_take_anomaly", sa.Boolean(), nullable=True),
        sa.Column("is_clean_courier_violation", sa.Boolean(), nullable=True),
        sa.Column("is_saved_order", sa.Boolean(), nullable=True),
        sa.Column("order_status", sa.Text(), nullable=True),
        sa.Column("delivery_on_time", sa.Text(), nullable=True),
        sa.Column("load_batch_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("load_ts", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_fact_delivery_orders"),
        schema="ai_delivery",
    )

    op.create_index(
        "ix_fact_delivery_orders_order_id",
        "fact_delivery_orders",
        ["order_id"],
        unique=False,
        schema="ai_delivery",
    )
    op.create_index(
        "ix_fact_delivery_orders_created_ts",
        "fact_delivery_orders",
        ["created_ts"],
        unique=False,
        schema="ai_delivery",
    )
    op.create_index(
        "ix_fact_delivery_orders_tt_service",
        "fact_delivery_orders",
        ["tt_name", "service_name"],
        unique=False,
        schema="ai_delivery",
    )
    op.create_index(
        "ix_fact_delivery_orders_ziz",
        "fact_delivery_orders",
        ["ziz_name"],
        unique=False,
        schema="ai_delivery",
    )
    op.create_index(
        "ix_fact_delivery_orders_courier",
        "fact_delivery_orders",
        ["courier_name"],
        unique=False,
        schema="ai_delivery",
    )

    # Факт-таблица по обращениям / жалобам (структура минимальная, без привязки к источнику)
    op.create_table(
        "fact_delivery_complaints",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("external_id", sa.Text(), nullable=True),
        sa.Column("order_id", sa.Text(), nullable=True),
        sa.Column("tt_name", sa.Text(), nullable=True),
        sa.Column("ziz_name", sa.Text(), nullable=True),
        sa.Column("courier_name", sa.Text(), nullable=True),
        sa.Column("complaint_created_ts", sa.DateTime(timezone=True), nullable=True),
        sa.Column("complaint_category", sa.Text(), nullable=True),
        sa.Column("complaint_subcategory", sa.Text(), nullable=True),
        sa.Column("complaint_tags", sa.Text(), nullable=True),
        sa.Column("is_damage", sa.Boolean(), nullable=True),
        sa.Column("is_return", sa.Boolean(), nullable=True),
        sa.Column("is_courier_issue", sa.Boolean(), nullable=True),
        sa.Column("is_store_issue", sa.Boolean(), nullable=True),
        sa.Column("load_batch_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("load_ts", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_fact_delivery_complaints"),
        schema="ai_delivery",
    )

    op.create_index(
        "ix_fact_delivery_complaints_order_id",
        "fact_delivery_complaints",
        ["order_id"],
        unique=False,
        schema="ai_delivery",
    )
    op.create_index(
        "ix_fact_delivery_complaints_created_ts",
        "fact_delivery_complaints",
        ["complaint_created_ts"],
        unique=False,
        schema="ai_delivery",
    )
    op.create_index(
        "ix_fact_delivery_complaints_tt",
        "fact_delivery_complaints",
        ["tt_name"],
        unique=False,
        schema="ai_delivery",
    )
    op.create_index(
        "ix_fact_delivery_complaints_ziz",
        "fact_delivery_complaints",
        ["ziz_name"],
        unique=False,
        schema="ai_delivery",
    )
    op.create_index(
        "ix_fact_delivery_complaints_courier",
        "fact_delivery_complaints",
        ["courier_name"],
        unique=False,
        schema="ai_delivery",
    )


def downgrade() -> None:
    op.drop_index(
        "ix_fact_delivery_complaints_courier",
        table_name="fact_delivery_complaints",
        schema="ai_delivery",
    )
    op.drop_index(
        "ix_fact_delivery_complaints_ziz",
        table_name="fact_delivery_complaints",
        schema="ai_delivery",
    )
    op.drop_index(
        "ix_fact_delivery_complaints_tt",
        table_name="fact_delivery_complaints",
        schema="ai_delivery",
    )
    op.drop_index(
        "ix_fact_delivery_complaints_created_ts",
        table_name="fact_delivery_complaints",
        schema="ai_delivery",
    )
    op.drop_index(
        "ix_fact_delivery_complaints_order_id",
        table_name="fact_delivery_complaints",
        schema="ai_delivery",
    )
    op.drop_table("fact_delivery_complaints", schema="ai_delivery")

    op.drop_index(
        "ix_fact_delivery_orders_courier",
        table_name="fact_delivery_orders",
        schema="ai_delivery",
    )
    op.drop_index(
        "ix_fact_delivery_orders_ziz",
        table_name="fact_delivery_orders",
        schema="ai_delivery",
    )
    op.drop_index(
        "ix_fact_delivery_orders_tt_service",
        table_name="fact_delivery_orders",
        schema="ai_delivery",
    )
    op.drop_index(
        "ix_fact_delivery_orders_created_ts",
        table_name="fact_delivery_orders",
        schema="ai_delivery",
    )
    op.drop_index(
        "ix_fact_delivery_orders_order_id",
        table_name="fact_delivery_orders",
        schema="ai_delivery",
    )
    op.drop_table("fact_delivery_orders", schema="ai_delivery")

