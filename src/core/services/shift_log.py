"""Shift log service: incidents and notes."""
from uuid import UUID

from src.infra.db.enums import LogType, Severity
from src.infra.db.repositories.shift_log import ShiftLogRepository
from src.infra.db.session import async_session_factory


class ShiftLogService:
    """Service for shift log entries (incidents, notes)."""

    async def create_incident(
        self,
        darkstore_id: UUID,
        severity: Severity,
        title: str,
        details: str | None = None,
        attachments: list[str] | None = None,
        user_id: UUID | None = None,
    ) -> UUID:
        """Create incident entry in shift_log."""
        async with async_session_factory() as session:
            repo = ShiftLogRepository(session)
            entry = await repo.create_log(
                darkstore_id=darkstore_id,
                log_type=LogType.INCIDENT,
                severity=severity,
                title=title,
                details=details,
                created_by=user_id,
            )
            await session.commit()
            return entry.id
