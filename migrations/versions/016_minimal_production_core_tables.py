"""Minimal production core: audit_logs, ai_requests_log, uploaded_files, analysis_jobs, groups, group_members, polls, poll_answers, poll_schedules, poll_slots.

Revision ID: 016_minimal_production_core
Revises: 015_ai_delivery_aggregates
Create Date: 2026-03-13

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "016_minimal_production_core"
down_revision: Union[str, None] = "015_ai_delivery_aggregates"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- audit_logs ---
    op.create_table(
        "audit_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("actor_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("actor_tg_id", sa.BigInteger(), nullable=True),
        sa.Column("action", sa.String(64), nullable=False),
        sa.Column("entity_type", sa.String(64), nullable=True),
        sa.Column("entity_id", sa.String(255), nullable=True),
        sa.Column("payload", postgresql.JSONB(), nullable=True),
        sa.Column("ip", sa.String(64), nullable=True),
        sa.ForeignKeyConstraint(["actor_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_audit_logs_created_at", "audit_logs", ["created_at"], unique=False)
    op.create_index("ix_audit_logs_actor_id", "audit_logs", ["actor_id"], unique=False)
    op.create_index("ix_audit_logs_entity", "audit_logs", ["entity_type", "entity_id"], unique=False)

    # --- ai_requests_log ---
    op.create_table(
        "ai_requests_log",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("tg_user_id", sa.BigInteger(), nullable=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("mode", sa.String(32), nullable=False),
        sa.Column("request_preview", sa.Text(), nullable=True),
        sa.Column("response_preview", sa.Text(), nullable=True),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("provider", sa.String(64), nullable=True),
        sa.Column("model", sa.String(64), nullable=True),
        sa.Column("tokens_input", sa.Integer(), nullable=True),
        sa.Column("tokens_output", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(32), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_ai_requests_log_created_at", "ai_requests_log", ["created_at"], unique=False)
    op.create_index("ix_ai_requests_log_user_id", "ai_requests_log", ["user_id"], unique=False)
    op.create_index("ix_ai_requests_log_tg_user_id", "ai_requests_log", ["tg_user_id"], unique=False)

    # --- uploaded_files ---
    op.create_table(
        "uploaded_files",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("filename", sa.String(512), nullable=False),
        sa.Column("content_type", sa.String(128), nullable=True),
        sa.Column("size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("storage_path", sa.String(1024), nullable=False),
        sa.Column("batch_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("uploaded_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.ForeignKeyConstraint(["batch_id"], ["ingest_batches.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["uploaded_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_uploaded_files_batch_id", "uploaded_files", ["batch_id"], unique=False)
    op.create_index("ix_uploaded_files_uploaded_by", "uploaded_files", ["uploaded_by"], unique=False)

    # --- analysis_jobs ---
    op.create_table(
        "analysis_jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("job_type", sa.String(64), nullable=False),
        sa.Column("input_file_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("input_batch_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("result", postgresql.JSONB(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.ForeignKeyConstraint(["input_file_id"], ["uploaded_files.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["input_batch_id"], ["ingest_batches.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_analysis_jobs_created_at", "analysis_jobs", ["created_at"], unique=False)
    op.create_index("ix_analysis_jobs_status", "analysis_jobs", ["status"], unique=False)
    op.create_index("ix_analysis_jobs_created_by", "analysis_jobs", ["created_by"], unique=False)

    # --- groups ---
    op.create_table(
        "groups",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tg_chat_id", sa.BigInteger(), nullable=False),
        sa.Column("title", sa.String(512), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tg_chat_id", name="uq_groups_tg_chat_id"),
    )
    op.create_index("ix_groups_tg_chat_id", "groups", ["tg_chat_id"], unique=True)

    # --- group_members ---
    op.create_table(
        "group_members",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("group_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("tg_user_id", sa.BigInteger(), nullable=True),
        sa.Column("role", sa.String(32), nullable=True),
        sa.Column("joined_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["group_id"], ["groups.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_group_members_group_id", "group_members", ["group_id"], unique=False)
    op.create_index("ix_group_members_user_id", "group_members", ["user_id"], unique=False)
    op.create_index("ix_group_members_tg_user_id", "group_members", ["tg_user_id"], unique=False)

    # --- polls ---
    op.create_table(
        "polls",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("group_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("title", sa.String(512), nullable=True),
        sa.Column("question_text", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.ForeignKeyConstraint(["group_id"], ["groups.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_polls_group_id", "polls", ["group_id"], unique=False)
    op.create_index("ix_polls_created_at", "polls", ["created_at"], unique=False)
    op.create_index("ix_polls_created_by", "polls", ["created_by"], unique=False)

    # --- poll_answers ---
    op.create_table(
        "poll_answers",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("poll_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tg_user_id", sa.BigInteger(), nullable=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("option_index", sa.Integer(), nullable=False),
        sa.Column("option_text", sa.String(512), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["poll_id"], ["polls.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_poll_answers_poll_id", "poll_answers", ["poll_id"], unique=False)
    op.create_index("ix_poll_answers_tg_user_id", "poll_answers", ["tg_user_id"], unique=False)
    op.create_index("ix_poll_answers_user_id", "poll_answers", ["user_id"], unique=False)

    # --- poll_schedules ---
    op.create_table(
        "poll_schedules",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("poll_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("scheduled_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("recurrence", sa.String(32), nullable=True),
        sa.ForeignKeyConstraint(["poll_id"], ["polls.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_poll_schedules_poll_id", "poll_schedules", ["poll_id"], unique=False)
    op.create_index("ix_poll_schedules_scheduled_at", "poll_schedules", ["scheduled_at"], unique=False)

    # --- poll_slots ---
    op.create_table(
        "poll_slots",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("poll_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("slot_index", sa.Integer(), nullable=False),
        sa.Column("option_text", sa.String(1024), nullable=False),
        sa.Column("is_correct", sa.Boolean(), nullable=True),
        sa.ForeignKeyConstraint(["poll_id"], ["polls.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("poll_id", "slot_index", name="uq_poll_slots_poll_slot"),
    )
    op.create_index("ix_poll_slots_poll_id", "poll_slots", ["poll_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_poll_slots_poll_id", table_name="poll_slots")
    op.drop_table("poll_slots")
    op.drop_index("ix_poll_schedules_scheduled_at", table_name="poll_schedules")
    op.drop_index("ix_poll_schedules_poll_id", table_name="poll_schedules")
    op.drop_table("poll_schedules")
    op.drop_index("ix_poll_answers_user_id", table_name="poll_answers")
    op.drop_index("ix_poll_answers_tg_user_id", table_name="poll_answers")
    op.drop_index("ix_poll_answers_poll_id", table_name="poll_answers")
    op.drop_table("poll_answers")
    op.drop_index("ix_polls_created_by", table_name="polls")
    op.drop_index("ix_polls_created_at", table_name="polls")
    op.drop_index("ix_polls_group_id", table_name="polls")
    op.drop_table("polls")
    op.drop_index("ix_group_members_tg_user_id", table_name="group_members")
    op.drop_index("ix_group_members_user_id", table_name="group_members")
    op.drop_index("ix_group_members_group_id", table_name="group_members")
    op.drop_table("group_members")
    op.drop_index("ix_groups_tg_chat_id", table_name="groups")
    op.drop_table("groups")
    op.drop_index("ix_analysis_jobs_created_by", table_name="analysis_jobs")
    op.drop_index("ix_analysis_jobs_status", table_name="analysis_jobs")
    op.drop_index("ix_analysis_jobs_created_at", table_name="analysis_jobs")
    op.drop_table("analysis_jobs")
    op.drop_index("ix_uploaded_files_uploaded_by", table_name="uploaded_files")
    op.drop_index("ix_uploaded_files_batch_id", table_name="uploaded_files")
    op.drop_table("uploaded_files")
    op.drop_index("ix_ai_requests_log_tg_user_id", table_name="ai_requests_log")
    op.drop_index("ix_ai_requests_log_user_id", table_name="ai_requests_log")
    op.drop_index("ix_ai_requests_log_created_at", table_name="ai_requests_log")
    op.drop_table("ai_requests_log")
    op.drop_index("ix_audit_logs_entity", table_name="audit_logs")
    op.drop_index("ix_audit_logs_actor_id", table_name="audit_logs")
    op.drop_index("ix_audit_logs_created_at", table_name="audit_logs")
    op.drop_table("audit_logs")
