"""Ingest batches and delivery_orders_raw repository."""
from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.infra.db.enums import IngestSource, IngestStatus
from src.infra.db.models import DeliveryOrderRaw, IngestBatch


class IngestRepository:
    """Repository for ingest batches and raw rows."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_batch_by_source_hash(
        self, source: IngestSource, content_hash: str
    ) -> IngestBatch | None:
        result = await self._session.execute(
            select(IngestBatch).where(
                IngestBatch.source == source,
                IngestBatch.content_hash == content_hash,
            )
        )
        return result.scalars().one_or_none()

    async def create_batch(
        self,
        source: IngestSource,
        content_hash: str,
        rules_version: str | None = None,
        status: IngestStatus = IngestStatus.PENDING,
    ) -> IngestBatch:
        batch = IngestBatch(
            source=source,
            content_hash=content_hash,
            status=status,
            rules_version=rules_version,
        )
        self._session.add(batch)
        await self._session.flush()
        return batch

    async def insert_raw_rows(
        self,
        batch_id: UUID,
        rows: list[dict],
    ) -> None:
        for r in rows:
            row = DeliveryOrderRaw(
                batch_id=batch_id,
                order_key=r.get("order_key", ""),
                ds_code=r.get("ds_code", ""),
                zone_code=r.get("zone_code"),
                start_delivery_at=r.get("start_delivery_at"),
                deadline_at=r.get("deadline_at"),
                finish_at_raw=r.get("finish_at_raw"),
                durations=r.get("durations"),
                raw=r.get("raw"),
            )
            self._session.add(row)
        await self._session.flush()

    async def update_batch_status(self, batch_id: UUID, status: IngestStatus) -> None:
        result = await self._session.execute(
            select(IngestBatch).where(IngestBatch.id == batch_id)
        )
        batch = result.scalars().one_or_none()
        if batch:
            batch.status = status
