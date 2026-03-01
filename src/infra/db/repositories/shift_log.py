"""Shift log repository."""
from datetime import date, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.infra.db.enums import LogType, Severity
from src.infra.db.models import ShiftLog


class ShiftLogRepository:
    """Repository for shift log entries."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create_log(
        self,
        darkstore_id: UUID,
        log_type: LogType,
        severity: Severity,
        title: str,
        details: str | None = None,
        created_by: UUID | None = None,
    ) -> ShiftLog:
        entry = ShiftLog(
            darkstore_id=darkstore_id,
            log_type=log_type,
            severity=severity,
            title=title,
            details=details,
            created_by=created_by,
        )
        self._session.add(entry)
        await self._session.flush()
        return entry

    async def list_by_darkstore_date(
        self,
        darkstore_id: UUID,
        date_from: date,
        date_to: date,
    ) -> list[ShiftLog]:
        # date_from 00:00 UTC to date_to 23:59:59 UTC
        ts_from = datetime.combine(date_from, datetime.min.time())
        ts_to = datetime.combine(date_to, datetime.max.time().replace(microsecond=0))
        result = await self._session.execute(
            select(ShiftLog)
            .where(
                ShiftLog.darkstore_id == darkstore_id,
                ShiftLog.created_at >= ts_from,
                ShiftLog.created_at <= ts_to,
            )
            .order_by(ShiftLog.created_at.desc())
        )
        return list(result.scalars().all())
