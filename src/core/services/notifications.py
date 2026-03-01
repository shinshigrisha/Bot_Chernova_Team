"""Notification service: enqueue notifications (no direct send from here)."""
from uuid import UUID

from src.infra.db.enums import NotificationChannel, NotificationType
from src.infra.db.repositories.notifications import NotificationRepository
from src.infra.db.session import async_session_factory


class NotificationService:
    """Service for creating notifications and enqueueing delivery. Delivery is done by worker."""

    async def enqueue_notification(
        self,
        type_: NotificationType,
        targets: list[tuple[NotificationChannel, int, int | None]],
        payload: dict | None = None,
        dedupe_key: str | None = None,
    ) -> UUID:
        """Create notification + targets in DB and enqueue deliver_notification task. Does not send."""
        async with async_session_factory() as session:
            repo = NotificationRepository(session)
            notification = await repo.create_notification(
                type_=type_,
                payload=payload,
                dedupe_key=dedupe_key,
            )
            await repo.create_targets(notification.id, targets)
            await session.commit()
            nid = notification.id

        # Enqueue after commit so worker sees the record
        from src.infra.queue.tasks import deliver_notification_task

        deliver_notification_task.delay(str(nid))
        return nid
