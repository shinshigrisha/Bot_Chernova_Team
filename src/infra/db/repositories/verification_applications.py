"""Repository for verification applications."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.infra.db.models import VerificationApplication


class VerificationApplicationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, app_id: UUID) -> VerificationApplication | None:
        result = await self._session.execute(
            select(VerificationApplication).where(VerificationApplication.id == app_id)
        )
        return result.scalars().one_or_none()

    async def list_for_user(self, tg_user_id: int) -> list[VerificationApplication]:
        result = await self._session.execute(
            select(VerificationApplication)
            .where(VerificationApplication.tg_user_id == tg_user_id)
            .order_by(VerificationApplication.created_at.desc())
        )
        return list(result.scalars().all())

    async def list_by_tg_user_ids(
        self, tg_user_ids: list[int]
    ) -> list[VerificationApplication]:
        if not tg_user_ids:
            return []
        result = await self._session.execute(
            select(VerificationApplication)
            .where(VerificationApplication.tg_user_id.in_(tg_user_ids))
            .order_by(VerificationApplication.created_at.desc())
        )
        return list(result.scalars().unique().all())

    async def create(
        self,
        tg_user_id: int,
        role: str,
        first_name: str,
        last_name: str,
        tt_number: str,
        ds_code: str,
        phone: str,
    ) -> VerificationApplication:
        app = VerificationApplication(
            tg_user_id=tg_user_id,
            role=role,
            first_name=first_name,
            last_name=last_name,
            tt_number=tt_number,
            ds_code=ds_code,
            phone=phone,
        )
        self._session.add(app)
        await self._session.flush()
        return app

