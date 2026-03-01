"""Users repository."""
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.infra.db.enums import UserRole
from src.infra.db.models import User


class UserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_tg_id(self, tg_user_id: int) -> User | None:
        result = await self._session.execute(
            select(User).where(User.tg_user_id == tg_user_id)
        )
        return result.scalars().one_or_none()

    async def get_or_create(
        self,
        tg_user_id: int,
        role: UserRole = UserRole.VIEWER,
        display_name: str | None = None,
    ) -> User:
        user = await self.get_by_tg_id(tg_user_id)
        if user:
            if display_name and user.display_name != display_name:
                user.display_name = display_name
            return user
        user = User(
            tg_user_id=tg_user_id,
            role=role,
            display_name=display_name,
        )
        self._session.add(user)
        await self._session.flush()
        return user
