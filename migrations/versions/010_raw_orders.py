"""Таблица raw_orders — сырая выгрузка заказов из CSV (аналитика последней мили).

Revision ID: 010_raw_orders
Revises: 009_tg_user_id_bigint
Create Date: 2026-03-12

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "010_raw_orders"
down_revision: Union[str, None] = "009_tg_user_id_bigint"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "raw_orders",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        # Поля как в CSV (сырые строки)
        sa.Column("Наименование ТТ", sa.Text(), nullable=True),
        sa.Column("Сервис", sa.Text(), nullable=True),
        sa.Column("Служба", sa.Text(), nullable=True),
        sa.Column("Курьер", sa.Text(), nullable=True),
        sa.Column("Ген. заказ", sa.Text(), nullable=True),
        sa.Column("Заказ", sa.Text(), nullable=True),
        sa.Column("Статус заказа", sa.Text(), nullable=True),
        sa.Column("Доставка в срок", sa.Text(), nullable=True),
        sa.Column("Дата доставки С", sa.Text(), nullable=True),
        sa.Column("Дата доставки До", sa.Text(), nullable=True),
        sa.Column("Дата и время оформления", sa.Text(), nullable=True),
        sa.Column("Дата начала сборки", sa.Text(), nullable=True),
        sa.Column("Дата окончания сборки", sa.Text(), nullable=True),
        sa.Column("Дата начала доставки", sa.Text(), nullable=True),
        sa.Column("Дата окончания доставки", sa.Text(), nullable=True),
        sa.Column("Время сборки", sa.Text(), nullable=True),
        sa.Column("Время ожидания сборки", sa.Text(), nullable=True),
        sa.Column("Время доставки", sa.Text(), nullable=True),
        sa.Column("Время ожидания доставки", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_raw_orders_order", "raw_orders", ["Заказ"], unique=False)
    op.create_index("ix_raw_orders_status", "raw_orders", ["Статус заказа"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_raw_orders_status", table_name="raw_orders")
    op.drop_index("ix_raw_orders_order", table_name="raw_orders")
    op.drop_table("raw_orders")
