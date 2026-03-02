"""SQLAlchemy ORM models for Delivery Assistant MVP."""
from datetime import datetime
from typing import Any, Optional
from uuid import uuid4

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    TypeDecorator,
    UniqueConstraint,
)
from sqlalchemy import text
from sqlalchemy.dialects.postgresql import ENUM, JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from src.infra.db.enums import (
    AssetCondition,
    AssetStatus,
    AssetType,
    AttemptStatus,
    ChatBindingCategory,
    IngestSource,
    IngestStatus,
    LogType,
    NotificationChannel,
    NotificationStatus,
    NotificationType,
    Severity,
    UserRole,
    coerce_user_role,
)


class UserRoleType(TypeDecorator):
    """TypeDecorator для колонки user_role.

    Гарантирует, что в PostgreSQL всегда попадает lowercase-значение ('admin',
    не 'ADMIN'), даже если где-то в коде передана строка или str(enum)-repr
    вида 'UserRole.ADMIN' (поведение Python ≤3.10).
    Использует coerce_user_role как единственную точку нормализации.
    """

    impl = ENUM(
        *[r.value for r in UserRole],
        name="user_role",
        create_type=False,
    )
    cache_ok = True

    def process_bind_param(self, value, dialect):  # Python → DB
        if value is None:
            return None
        return coerce_user_role(value, default=UserRole.COURIER).value

    def process_result_value(self, value, dialect):  # DB → Python
        if value is None:
            return None
        return coerce_user_role(value, default=UserRole.COURIER)


def _pg_enum(enum_class: type, name: str) -> ENUM:
    """Create a PostgreSQL ENUM column type using enum values (not names)."""
    return ENUM(
        enum_class,
        name=name,
        create_type=False,
        values_callable=lambda obj: [e.value for e in obj],
    )


class Base(DeclarativeBase):
    """Declarative base for all models."""

    type_annotation_map = {
        dict[str, Any]: JSONB,
    }


class Territory(Base):
    __tablename__ = "territories"

    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    teams: Mapped[list["Team"]] = relationship(back_populates="territory")


class Team(Base):
    __tablename__ = "teams"

    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    territory_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("territories.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    territory: Mapped["Territory"] = relationship(back_populates="teams")
    darkstores: Mapped[list["Darkstore"]] = relationship(back_populates="team")
    chat_bindings: Mapped[list["ChatBinding"]] = relationship(back_populates="team")


class Darkstore(Base):
    __tablename__ = "darkstores"

    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    team_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("teams.id", ondelete="CASCADE"), nullable=False
    )
    code: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    is_white: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    team: Mapped["Team"] = relationship(back_populates="darkstores")
    couriers: Mapped[list["Courier"]] = relationship(back_populates="darkstore")
    assets: Mapped[list["Asset"]] = relationship(back_populates="darkstore")
    shift_logs: Mapped[list["ShiftLog"]] = relationship(back_populates="darkstore")


class User(Base):
    __tablename__ = "users"

    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    tg_user_id: Mapped[int] = mapped_column(nullable=False, unique=True)
    role: Mapped[UserRole] = mapped_column(UserRoleType(), nullable=False)
    display_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow
    )

    scopes: Mapped[list["UserScope"]] = relationship(back_populates="user")
    shift_logs: Mapped[list["ShiftLog"]] = relationship(back_populates="created_by_user")


class UserScope(Base):
    __tablename__ = "user_scopes"

    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    team_id: Mapped[Optional[UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("teams.id", ondelete="CASCADE"), nullable=True
    )
    darkstore_id: Mapped[Optional[UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("darkstores.id", ondelete="CASCADE"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("user_id", "team_id", "darkstore_id", name="uq_user_scope"),
    )

    user: Mapped["User"] = relationship(back_populates="scopes")


class Courier(Base):
    __tablename__ = "couriers"

    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    darkstore_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("darkstores.id", ondelete="CASCADE"), nullable=False
    )
    external_key: Mapped[str] = mapped_column(String(128), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    darkstore: Mapped["Darkstore"] = relationship(back_populates="couriers")
    assignments: Mapped[list["AssetAssignment"]] = relationship(back_populates="courier")


class ChatBinding(Base):
    __tablename__ = "chat_bindings"

    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    team_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("teams.id", ondelete="CASCADE"), nullable=False
    )
    chat_id: Mapped[int] = mapped_column(nullable=False)
    category: Mapped[ChatBindingCategory] = mapped_column(
        _pg_enum(ChatBindingCategory, "chat_binding_category"), nullable=False
    )
    topic_id: Mapped[Optional[int]] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    team: Mapped["Team"] = relationship(back_populates="chat_bindings")


class Asset(Base):
    __tablename__ = "assets"

    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    darkstore_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("darkstores.id", ondelete="CASCADE"), nullable=False
    )
    asset_type: Mapped[AssetType] = mapped_column(
        _pg_enum(AssetType, "asset_type"), nullable=False
    )
    serial: Mapped[str] = mapped_column(String(128), nullable=False)
    status: Mapped[AssetStatus] = mapped_column(
        _pg_enum(AssetStatus, "asset_status"), nullable=False
    )
    condition: Mapped[AssetCondition] = mapped_column(
        _pg_enum(AssetCondition, "asset_condition"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow
    )

    __table_args__ = (
        UniqueConstraint("darkstore_id", "asset_type", "serial", name="uq_asset_ds_type_serial"),
    )

    darkstore: Mapped["Darkstore"] = relationship(back_populates="assets")
    assignments: Mapped[list["AssetAssignment"]] = relationship(back_populates="asset")
    events: Mapped[list["AssetEvent"]] = relationship(back_populates="asset")


class AssetAssignment(Base):
    __tablename__ = "asset_assignments"

    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    asset_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("assets.id", ondelete="CASCADE"), nullable=False
    )
    courier_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("couriers.id", ondelete="CASCADE"), nullable=False
    )
    assigned_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    returned_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index(
            "ix_asset_assignments_active_unique",
            "asset_id",
            unique=True,
            postgresql_where=text("returned_at IS NULL"),
        ),
    )

    asset: Mapped["Asset"] = relationship(back_populates="assignments")
    courier: Mapped["Courier"] = relationship(back_populates="assignments")
    events: Mapped[list["AssetEvent"]] = relationship(back_populates="assignment")


class AssetEvent(Base):
    __tablename__ = "asset_events"

    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    asset_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("assets.id", ondelete="CASCADE"), nullable=False
    )
    assignment_id: Mapped[Optional[UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("asset_assignments.id", ondelete="SET NULL"), nullable=True
    )
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    payload: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    asset: Mapped["Asset"] = relationship(back_populates="events")
    assignment: Mapped[Optional["AssetAssignment"]] = relationship(back_populates="events")


class ShiftLog(Base):
    __tablename__ = "shift_log"

    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    darkstore_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("darkstores.id", ondelete="CASCADE"), nullable=False
    )
    log_type: Mapped[LogType] = mapped_column(
        _pg_enum(LogType, "log_type"), nullable=False
    )
    severity: Mapped[Severity] = mapped_column(
        _pg_enum(Severity, "severity"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    details: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    created_by: Mapped[Optional[UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    __table_args__ = (
        Index("ix_shift_log_darkstore_created", "darkstore_id", "created_at"),
    )

    darkstore: Mapped["Darkstore"] = relationship(back_populates="shift_logs")
    created_by_user: Mapped[Optional["User"]] = relationship(back_populates="shift_logs")


class Notification(Base):
    __tablename__ = "notifications"

    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    type: Mapped[NotificationType] = mapped_column(
        _pg_enum(NotificationType, "notification_type"), nullable=False
    )
    status: Mapped[NotificationStatus] = mapped_column(
        _pg_enum(NotificationStatus, "notification_status"), nullable=False
    )
    dedupe_key: Mapped[Optional[str]] = mapped_column(String(255), unique=True, nullable=True)
    payload: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    targets: Mapped[list["NotificationTarget"]] = relationship(back_populates="notification")
    attempts: Mapped[list["NotificationDeliveryAttempt"]] = relationship(
        back_populates="notification"
    )


class NotificationTarget(Base):
    __tablename__ = "notification_targets"

    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    notification_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("notifications.id", ondelete="CASCADE"), nullable=False
    )
    channel: Mapped[NotificationChannel] = mapped_column(
        _pg_enum(NotificationChannel, "notification_channel"), nullable=False
    )
    chat_id: Mapped[int] = mapped_column(nullable=False)
    topic_id: Mapped[Optional[int]] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    notification: Mapped["Notification"] = relationship(back_populates="targets")


class NotificationDeliveryAttempt(Base):
    __tablename__ = "notification_delivery_attempts"

    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    notification_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("notifications.id", ondelete="CASCADE"), nullable=False
    )
    attempted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    status: Mapped[AttemptStatus] = mapped_column(
        _pg_enum(AttemptStatus, "attempt_status"), nullable=False
    )
    error_code: Mapped[Optional[int]] = mapped_column(nullable=True)
    retry_after: Mapped[Optional[int]] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    notification: Mapped["Notification"] = relationship(back_populates="attempts")


class IngestBatch(Base):
    __tablename__ = "ingest_batches"

    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    source: Mapped[IngestSource] = mapped_column(
        _pg_enum(IngestSource, "ingest_source"), nullable=False
    )
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[IngestStatus] = mapped_column(
        _pg_enum(IngestStatus, "ingest_status"), nullable=False
    )
    rules_version: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    __table_args__ = (UniqueConstraint("source", "content_hash", name="uq_ingest_batch_source_hash"),)

    raw_rows: Mapped[list["DeliveryOrderRaw"]] = relationship(back_populates="batch")


class DeliveryOrderRaw(Base):
    __tablename__ = "delivery_orders_raw"

    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    batch_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("ingest_batches.id", ondelete="CASCADE"), nullable=False
    )
    order_key: Mapped[str] = mapped_column(String(255), nullable=False)
    ds_code: Mapped[str] = mapped_column(String(64), nullable=False)
    zone_code: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    start_delivery_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    deadline_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    finish_at_raw: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    durations: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    raw: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    __table_args__ = (
        Index("ix_delivery_orders_raw_batch", "batch_id"),
        Index("ix_delivery_orders_raw_ds", "ds_code"),
        Index("ix_delivery_orders_raw_zone", "zone_code"),
    )

    batch: Mapped["IngestBatch"] = relationship(back_populates="raw_rows")


class FAQItem(Base):
    __tablename__ = "faq_ai"

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    tags: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    q: Mapped[str] = mapped_column(Text, nullable=False)
    a: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow
    )


# Backward-compatible alias for faq_ai model naming.
FAQAI = FAQItem
