"""Celery tasks: deliver_notification, parse_ingest_batch."""
import asyncio
from uuid import UUID

from src.infra.queue.celery_app import app
from src.infra.db.enums import AttemptStatus, NotificationChannel as ChannelEnum, NotificationStatus
from src.infra.db.repositories.notifications import NotificationRepository
from src.infra.db.session import async_session_factory
from src.infra.notifications.telegram_channel import TelegramChannel


@app.task(bind=True, max_retries=10)
def deliver_notification_task(self, notification_id: str) -> None:
    """Load notification + targets, deliver via channel. On 429 record attempt and retry with countdown."""
    nid = UUID(notification_id)

    async def _deliver() -> tuple[bool, int | None]:
        async with async_session_factory() as session:
            repo = NotificationRepository(session)
            notification = await repo.get_notification_with_targets(nid)
            if not notification:
                return True, None
            payload = notification.payload or {}
            text = payload.get("text", "—")
            channels: dict[ChannelEnum, type] = {
                ChannelEnum.TELEGRAM: TelegramChannel,
            }
            retry_after: int | None = None
            for target in notification.targets:
                channel_impl = channels.get(target.channel)
                if not channel_impl:
                    await repo.add_attempt(nid, AttemptStatus.ERROR, error_code=None)
                    continue
                chan = channel_impl()
                result = chan.send_message(
                    chat_id=target.chat_id,
                    text=text,
                    topic_id=target.topic_id,
                )
                if result.success:
                    await repo.add_attempt(nid, AttemptStatus.SUCCESS)
                else:
                    await repo.add_attempt(
                        nid,
                        AttemptStatus.RATE_LIMIT if result.error_code == 429 else AttemptStatus.ERROR,
                        error_code=result.error_code,
                        retry_after=result.retry_after,
                    )
                    if result.error_code == 429 and result.retry_after:
                        retry_after = result.retry_after
                        break
            if retry_after is not None:
                await session.commit()
                return False, retry_after
            await repo.update_notification_status(nid, NotificationStatus.DELIVERED)
            await session.commit()
            return True, None

    try:
        success, retry_after = asyncio.run(_deliver())
    except Exception as exc:
        raise self.retry(exc=exc, countdown=60)

    if not success and retry_after is not None:
        raise self.retry(countdown=min(retry_after, 60))


@app.task(bind=True, max_retries=3)
def parse_ingest_batch_task(self, batch_id: str) -> None:
    """Parse ingest file from MinIO, insert raw rows, update batch status. Stub: just set completed."""
    from uuid import UUID
    from src.infra.db.enums import IngestStatus
    from src.infra.db.repositories.ingest import IngestRepository
    from src.infra.db.session import async_session_factory

    bid = UUID(batch_id)

    async def _parse() -> None:
        async with async_session_factory() as session:
            repo = IngestRepository(session)
            await repo.update_batch_status(bid, IngestStatus.PROCESSING)
            await session.commit()
        # MVP: no actual CSV parse; optional: read from MinIO, parse, insert_raw_rows
        async with async_session_factory() as session:
            repo = IngestRepository(session)
            await repo.update_batch_status(bid, IngestStatus.COMPLETED)
            await session.commit()

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(_parse())
    finally:
        loop.close()
