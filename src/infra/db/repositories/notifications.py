"""Notifications and delivery attempts repository."""
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.infra.db.enums import AttemptStatus, NotificationChannel, NotificationStatus, NotificationType
from src.infra.db.models import Notification, NotificationDeliveryAttempt, NotificationTarget


class NotificationRepository:
    """Repository for notifications, targets, and delivery attempts."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create_notification(
        self,
        type_: NotificationType,
        payload: dict | None = None,
        dedupe_key: str | None = None,
    ) -> Notification:
        notification = Notification(
            type=type_,
            status=NotificationStatus.PENDING,
            dedupe_key=dedupe_key,
            payload=payload,
        )
        self._session.add(notification)
        await self._session.flush()
        return notification

    async def create_targets(
        self,
        notification_id: UUID,
        targets: list[tuple[NotificationChannel, int, int | None]],
    ) -> list[NotificationTarget]:
        created = []
        for channel, chat_id, topic_id in targets:
            t = NotificationTarget(
                notification_id=notification_id,
                channel=channel,
                chat_id=chat_id,
                topic_id=topic_id,
            )
            self._session.add(t)
            created.append(t)
        await self._session.flush()
        return created

    async def add_attempt(
        self,
        notification_id: UUID,
        status: AttemptStatus,
        error_code: int | None = None,
        retry_after: int | None = None,
    ) -> NotificationDeliveryAttempt:
        attempt = NotificationDeliveryAttempt(
            notification_id=notification_id,
            status=status,
            error_code=error_code,
            retry_after=retry_after,
        )
        self._session.add(attempt)
        await self._session.flush()
        return attempt

    async def update_notification_status(self, notification_id: UUID, status: NotificationStatus) -> None:
        result = await self._session.execute(
            select(Notification).where(Notification.id == notification_id)
        )
        notification = result.scalars().one_or_none()
        if notification:
            notification.status = status

    async def get_notification_with_targets(self, notification_id: UUID) -> Notification | None:
        result = await self._session.execute(
            select(Notification)
            .where(Notification.id == notification_id)
            .options(selectinload(Notification.targets))
        )
        return result.scalars().one_or_none()