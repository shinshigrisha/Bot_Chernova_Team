"""Users repository."""
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.infra.db.enums import UserRole, UserStatus, coerce_user_role
from src.infra.db.models import User


class UserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_tg_id(self, tg_user_id: int) -> User | None:
        result = await self._session.execute(
            select(User).where(User.tg_user_id == tg_user_id)
        )
        return result.scalars().one_or_none()

    async def list_by_status(self, status: UserStatus) -> list[User]:
        result = await self._session.execute(
            select(User).where(User.status == status)
        )
        return list(result.scalars().unique().all())

    async def get_or_create(
        self,
        tg_user_id: int,
        role: UserRole = UserRole.COURIER,
        display_name: str | None = None,
        status: UserStatus | None = None,
    ) -> User:
        """Вернуть пользователя по tg_user_id или создать нового.

        Создание только при явном вызове (регистрация или bootstrap админа).
        Новый пользователь без переданного status получает GUEST (не approved).
        """
        role = coerce_user_role(role, default=UserRole.VIEWER)
        user = await self.get_by_tg_id(tg_user_id)
        if user:
            if display_name and user.display_name != display_name:
                user.display_name = display_name
            return user
        user = User(
            tg_user_id=tg_user_id,
            role=role,
            display_name=display_name,
            status=status if status is not None else UserStatus.GUEST,
        )
        self._session.add(user)
        await self._session.flush()
        return user
