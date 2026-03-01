"""Celery tasks: deliver_notification, parse_ingest_batch."""
import asyncio
import csv
from datetime import datetime
from io import StringIO
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
    """Parse ingest CSV from MinIO, insert raw rows, update batch status."""

    from src.infra.db.enums import IngestStatus
    from src.infra.db.repositories.ingest import IngestRepository
    from src.infra.db.session import async_session_factory
    from src.infra.storage.s3 import get_latest_ingest_file

    bid = UUID(batch_id)

    def _pick(row: dict, keys: list[str]) -> str | None:
        for key in keys:
            value = row.get(key)
            if value is not None and str(value).strip() != "":
                return str(value).strip()
        return None

    def _parse_dt(value: str | None) -> datetime | None:
        if not value:
            return None
        raw = value.strip()
        if not raw:
            return None
        try:
            # Accept UTC `Z` suffix from typical exports.
            return datetime.fromisoformat(raw.replace("Z", "+00:00"))
        except ValueError:
            return None

    def _to_int(value: str | None) -> int | None:
        if value is None or value == "":
            return None
        try:
            return int(float(value))
        except ValueError:
            return None

    def _to_rows(content: bytes) -> list[dict]:
        text = content.decode("utf-8-sig", errors="replace")
        reader = csv.DictReader(StringIO(text))
        parsed_rows: list[dict] = []
        for idx, row in enumerate(reader, start=1):
            order_key = _pick(
                row,
                ["order_key", "order_id", "order", "id", "order_number"],
            ) or f"row-{idx}"
            ds_code = _pick(
                row,
                ["ds_code", "darkstore_code", "store_code", "darkstore", "ds"],
            ) or "unknown"
            zone_code = _pick(row, ["zone_code", "zone", "zone_id"])
            start_delivery_at = _parse_dt(_pick(row, ["start_delivery_at", "start_at", "start"]))
            deadline_at = _parse_dt(_pick(row, ["deadline_at", "deadline", "deadline_ts"]))
            finish_at_raw = _parse_dt(_pick(row, ["finish_at_raw", "finish_at", "finished_at"]))
            durations = {
                "wait": _to_int(_pick(row, ["wait", "wait_min", "wait_minutes"])),
                "assembly": _to_int(_pick(row, ["assembly", "assembly_min", "assembly_minutes"])),
                "delivery": _to_int(_pick(row, ["delivery", "delivery_min", "delivery_minutes"])),
                "total": _to_int(_pick(row, ["total", "total_min", "total_minutes"])),
            }
            if all(v is None for v in durations.values()):
                durations = None

            parsed_rows.append(
                {
                    "order_key": order_key,
                    "ds_code": ds_code,
                    "zone_code": zone_code,
                    "start_delivery_at": start_delivery_at,
                    "deadline_at": deadline_at,
                    "finish_at_raw": finish_at_raw,
                    "durations": durations,
                    "raw": row,
                }
            )
        return parsed_rows

    async def _parse() -> None:
        try:
            async with async_session_factory() as session:
                repo = IngestRepository(session)
                await repo.update_batch_status(bid, IngestStatus.PROCESSING)
                await session.commit()

            _, content = get_latest_ingest_file(bid)
            rows = _to_rows(content)

            async with async_session_factory() as session:
                repo = IngestRepository(session)
                if rows:
                    await repo.insert_raw_rows(bid, rows)
                await repo.update_batch_status(bid, IngestStatus.COMPLETED)
                await session.commit()
        except Exception:
            async with async_session_factory() as session:
                repo = IngestRepository(session)
                await repo.update_batch_status(bid, IngestStatus.FAILED)
                await session.commit()
            raise

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(_parse())
    finally:
        loop.close()
