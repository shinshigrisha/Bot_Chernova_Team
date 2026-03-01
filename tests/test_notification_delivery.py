"""Tests for notification delivery: attempt recorded on failure (e.g. 429)."""
import pytest

from src.infra.db.enums import AttemptStatus, NotificationChannel, NotificationStatus, NotificationType
from src.infra.db.models import Notification, NotificationTarget
from src.infra.db.repositories.notifications import NotificationRepository

pytestmark = pytest.mark.asyncio


async def test_notification_attempt_inserted_on_delivery_failure(async_session) -> None:
    """When delivery fails (e.g. 429), a record is added to notification_delivery_attempts."""
    repo = NotificationRepository(async_session)
    notification = await repo.create_notification(
        type_=NotificationType.ALERT,
        payload={"text": "Test"},
        dedupe_key=None,
    )
    await repo.create_targets(
        notification.id,
        [(NotificationChannel.TELEGRAM, 12345, None)],
    )
    await async_session.commit()

    # Simulate worker recording a failed attempt (429)
    await repo.add_attempt(
        notification.id,
        AttemptStatus.RATE_LIMIT,
        error_code=429,
        retry_after=60,
    )
    await async_session.commit()

    # Reload and check attempts
    from sqlalchemy import select
    from src.infra.db.models import NotificationDeliveryAttempt

    result = await async_session.execute(
        select(NotificationDeliveryAttempt).where(
            NotificationDeliveryAttempt.notification_id == notification.id
        )
    )
    attempts = list(result.scalars().all())
    assert len(attempts) == 1
    assert attempts[0].status == AttemptStatus.RATE_LIMIT
    assert attempts[0].error_code == 429
    assert attempts[0].retry_after == 60
