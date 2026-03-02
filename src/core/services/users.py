"""User domain service — upsert user on /start."""
from __future__ import annotations

import logging
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import async_sessionmaker

from src.infra.db.enums import UserRole, coerce_user_role
from src.infra.db.repositories.users import UserRepository

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class UserProfile:
    tg_user_id: int
    role: UserRole
    display_name: str | None


class UserService:
    """Thin facade over UserRepository.

    Accepts a session factory via constructor (DI) so the service
    carries no direct dependency on the global ``async_session_factory``
    singleton and can be tested with any factory stub.
    """

    def __init__(self, session_factory: async_sessionmaker) -> None:
        self._session_factory = session_factory

    async def get_or_create(
        self,
        tg_user_id: int,
        role: UserRole,
        display_name: str | None = None,
    ) -> UserProfile:
        """Return existing user or create a new one.

        Scalars are extracted inside the session context to prevent
        ``DetachedInstanceError`` after the session closes.
        """
        role = coerce_user_role(role, default=UserRole.COURIER)
        async with self._session_factory() as session:
            repo = UserRepository(session)
            user = await repo.get_or_create(
                tg_user_id, role=role, display_name=display_name
            )
            await session.commit()
            return UserProfile(
                tg_user_id=user.tg_user_id,
                role=user.role,
                display_name=user.display_name,
            )
