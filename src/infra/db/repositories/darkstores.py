"""Darkstores repository for lookups."""
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.infra.db.models import Darkstore


class DarkstoreRepository:
    """Repository for darkstore lookups."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_code(self, code: str) -> Darkstore | None:
        result = await self._session.execute(
            select(Darkstore).where(Darkstore.code == code)
        )
        return result.scalars().one_or_none()

    async def get_by_id(self, id_: UUID) -> Darkstore | None:
        result = await self._session.execute(select(Darkstore).where(Darkstore.id == id_))
        return result.scalars().one_or_none()
