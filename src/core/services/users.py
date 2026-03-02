"""User domain service — upsert user on /start."""
from __future__ import annotations

import logging
from dataclasses import dataclass

from src.infra.db.enums import UserRole, coerce_user_role
from src.infra.db.repositories.users import UserRepository
from src.infra.db.session import async_session_factory

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class UserProfile:
    tg_user_id: int
    role: UserRole
    display_name: str | None


class UserService:
    """Thin facade over UserRepository.

    Manages its own DB session so callers (handlers) stay free of
    SQLAlchemy imports and session lifecycle boilerplate.
    """

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
        role = coerce_user_role(role, default=UserRole.VIEWER)
        async with async_session_factory() as session:
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
