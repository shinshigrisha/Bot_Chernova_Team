"""Initial MVP schema: territories, teams, darkstores, users, assets, shift_log, notifications, ingest.

Revision ID: 001_initial_mvp
Revises:
Create Date: 2025-03-01

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "001_initial_mvp"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create enum types (bind from context)
    conn = op.get_bind()
    postgresql.ENUM("admin", "lead", "curator", "viewer", "courier", name="user_role").create(conn)
    postgresql.ENUM("bike", "battery", "bag", "other", name="asset_type").create(conn)
    postgresql.ENUM("available", "assigned", "maintenance", "retired", name="asset_status").create(conn)
    postgresql.ENUM("good", "fair", "poor", "damaged", name="asset_condition").create(conn)
    postgresql.ENUM("incident", "note", "alert", name="log_type").create(conn)
    postgresql.ENUM("low", "medium", "high", "critical", name="severity").create(conn)
    postgresql.ENUM("alerts", "daily", "assets", "incidents", "general", name="chat_binding_category").create(conn)
    postgresql.ENUM("alert", "daily", "assets", "incident", "general", name="notification_type").create(conn)
    postgresql.ENUM("pending", "delivered", "failed", "partial", name="notification_status").create(conn)
    postgresql.ENUM("telegram", "email", "web", name="notification_channel").create(conn)
    postgresql.ENUM("success", "rate_limit", "error", name="attempt_status").create(conn)
    postgresql.ENUM("csv_upload", "superset_api", "db_direct", name="ingest_source").create(conn)
    postgresql.ENUM("pending", "processing", "completed", "failed", name="ingest_status").create(conn)

    op.create_table(
        "territories",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "teams",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("territory_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.ForeignKeyConstraint(["territory_id"], ["territories.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "darkstores",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("team_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("code", sa.String(64), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("is_white", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.ForeignKeyConstraint(["team_id"], ["teams.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tg_user_id", sa.BigInteger(), nullable=False),
        sa.Column("role", postgresql.ENUM("admin", "lead", "curator", "viewer", "courier", name="user_role", create_type=False), nullable=False),
        sa.Column("display_name", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tg_user_id", name="uq_users_tg_user_id"),
    )
    op.create_table(
        "user_scopes",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("team_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("darkstore_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["team_id"], ["teams.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["darkstore_id"], ["darkstores.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "team_id", "darkstore_id", name="uq_user_scope"),
    )
    op.create_table(
        "couriers",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("darkstore_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("external_key", sa.String(128), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.ForeignKeyConstraint(["darkstore_id"], ["darkstores.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "chat_bindings",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("team_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("chat_id", sa.BigInteger(), nullable=False),
        sa.Column("category", postgresql.ENUM("alerts", "daily", "assets", "incidents", "general", name="chat_binding_category", create_type=False), nullable=False),
        sa.Column("topic_id", sa.BigInteger(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.ForeignKeyConstraint(["team_id"], ["teams.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "assets",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("darkstore_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("asset_type", postgresql.ENUM("bike", "battery", "bag", "other", name="asset_type", create_type=False), nullable=False),
        sa.Column("serial", sa.String(128), nullable=False),
        sa.Column("status", postgresql.ENUM("available", "assigned", "maintenance", "retired", name="asset_status", create_type=False), nullable=False),
        sa.Column("condition", postgresql.ENUM("good", "fair", "poor", "damaged", name="asset_condition", create_type=False), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.ForeignKeyConstraint(["darkstore_id"], ["darkstores.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("darkstore_id", "asset_type", "serial", name="uq_asset_ds_type_serial"),
    )
    op.create_table(
        "asset_assignments",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("asset_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("courier_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("assigned_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.Column("returned_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["asset_id"], ["assets.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["courier_id"], ["couriers.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_asset_assignments_active_unique",
        "asset_assignments",
        ["asset_id"],
        unique=True,
        postgresql_where=sa.text("returned_at IS NULL"),
    )
    op.create_table(
        "asset_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("asset_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("assignment_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("event_type", sa.String(64), nullable=False),
        sa.Column("payload", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.ForeignKeyConstraint(["asset_id"], ["assets.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["assignment_id"], ["asset_assignments.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "shift_log",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("darkstore_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("log_type", postgresql.ENUM("incident", "note", "alert", name="log_type", create_type=False), nullable=False),
        sa.Column("severity", postgresql.ENUM("low", "medium", "high", "critical", name="severity", create_type=False), nullable=False),
        sa.Column("title", sa.String(512), nullable=False),
        sa.Column("details", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.ForeignKeyConstraint(["darkstore_id"], ["darkstores.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_shift_log_darkstore_created", "shift_log", ["darkstore_id", "created_at"], unique=False)
    op.create_table(
        "notifications",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("type", postgresql.ENUM("alert", "daily", "assets", "incident", "general", name="notification_type", create_type=False), nullable=False),
        sa.Column("status", postgresql.ENUM("pending", "delivered", "failed", "partial", name="notification_status", create_type=False), nullable=False),
        sa.Column("dedupe_key", sa.String(255), nullable=True),
        sa.Column("payload", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("dedupe_key", name="uq_notifications_dedupe_key"),
    )
    op.create_table(
        "notification_targets",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("notification_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("channel", postgresql.ENUM("telegram", "email", "web", name="notification_channel", create_type=False), nullable=False),
        sa.Column("chat_id", sa.BigInteger(), nullable=False),
        sa.Column("topic_id", sa.BigInteger(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.ForeignKeyConstraint(["notification_id"], ["notifications.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "notification_delivery_attempts",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("notification_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("attempted_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.Column("status", postgresql.ENUM("success", "rate_limit", "error", name="attempt_status", create_type=False), nullable=False),
        sa.Column("error_code", sa.Integer(), nullable=True),
        sa.Column("retry_after", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.ForeignKeyConstraint(["notification_id"], ["notifications.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "ingest_batches",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source", postgresql.ENUM("csv_upload", "superset_api", "db_direct", name="ingest_source", create_type=False), nullable=False),
        sa.Column("content_hash", sa.String(64), nullable=False),
        sa.Column("status", postgresql.ENUM("pending", "processing", "completed", "failed", name="ingest_status", create_type=False), nullable=False),
        sa.Column("rules_version", sa.String(64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("source", "content_hash", name="uq_ingest_batch_source_hash"),
    )
    op.create_table(
        "delivery_orders_raw",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("batch_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("order_key", sa.String(255), nullable=False),
        sa.Column("ds_code", sa.String(64), nullable=False),
        sa.Column("zone_code", sa.String(64), nullable=True),
        sa.Column("start_delivery_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deadline_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finish_at_raw", sa.DateTime(timezone=True), nullable=True),
        sa.Column("durations", postgresql.JSONB(), nullable=True),
        sa.Column("raw", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.ForeignKeyConstraint(["batch_id"], ["ingest_batches.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_delivery_orders_raw_batch", "delivery_orders_raw", ["batch_id"], unique=False)
    op.create_index("ix_delivery_orders_raw_ds", "delivery_orders_raw", ["ds_code"], unique=False)
    op.create_index("ix_delivery_orders_raw_zone", "delivery_orders_raw", ["zone_code"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_delivery_orders_raw_zone", table_name="delivery_orders_raw")
    op.drop_index("ix_delivery_orders_raw_ds", table_name="delivery_orders_raw")
    op.drop_index("ix_delivery_orders_raw_batch", table_name="delivery_orders_raw")
    op.drop_table("delivery_orders_raw")
    op.drop_table("ingest_batches")
    op.drop_table("notification_delivery_attempts")
    op.drop_table("notification_targets")
    op.drop_table("notifications")
    op.drop_index("ix_shift_log_darkstore_created", table_name="shift_log")
    op.drop_table("shift_log")
    op.drop_table("asset_events")
    op.drop_index("ix_asset_assignments_active_unique", table_name="asset_assignments")
    op.drop_table("asset_assignments")
    op.drop_table("assets")
    op.drop_table("chat_bindings")
    op.drop_table("couriers")
    op.drop_table("user_scopes")
    op.drop_table("users")
    op.drop_table("darkstores")
    op.drop_table("teams")
    op.drop_table("territories")

    # Drop enum types (reverse order not required for PostgreSQL TYPE)
    conn = op.get_bind()
    for enum_name in (
        "ingest_status", "ingest_source", "attempt_status", "notification_channel",
        "notification_status", "notification_type", "chat_binding_category",
        "severity", "log_type", "asset_condition", "asset_status", "asset_type", "user_role",
    ):
        postgresql.ENUM(name=enum_name, create_type=False).drop(conn, checkfirst=True)
