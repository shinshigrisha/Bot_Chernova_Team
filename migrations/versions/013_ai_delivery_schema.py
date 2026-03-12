"""Schema ai_delivery for analytical delivery data.

Revision ID: 013_ai_delivery_schema
Revises: 012_mart_orders_enriched
Create Date: 2026-03-12

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "013_ai_delivery_schema"
down_revision: Union[str, None] = "012_mart_views"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(sa.text("CREATE SCHEMA IF NOT EXISTS ai_delivery"))


def downgrade() -> None:
    op.execute(sa.text("DROP SCHEMA IF EXISTS ai_delivery CASCADE"))

