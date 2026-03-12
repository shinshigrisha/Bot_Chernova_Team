from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.ext.asyncio import async_sessionmaker

from src.config import Settings
from src.infra.db.enums import UserRole, UserStatus
from src.infra.db.repositories.users import UserRepository


@dataclass(frozen=True, slots=True)
class Principal:
    tg_user_id: int
    role: UserRole | None
    status: UserStatus | None


class AccessService:
    """Centralized access-control decisions based on role, status and feature flags.

    For now intentionally conservative and backwards-compatible:
    - When ENABLE_NEW_AUTH_FLOW is false, behavior matches legacy checks.
    - When ENABLE_NEW_AUTH_FLOW is true, blocked/rejected users are denied,
      other roles behave as before (future tasks can tighten policy).
    """

    def __init__(
        self,
        *,
        session_factory: async_sessionmaker,
        settings: Settings,
    ) -> None:
        self._session_factory = session_factory
        self._settings = settings

    async def get_principal(self, tg_user_id: int) -> Principal:
        """Load principal from database; missing user is treated as guest."""
        async with self._session_factory() as session:
            repo = UserRepository(session)
            user = await repo.get_by_tg_id(tg_user_id)
        if not user:
            return Principal(tg_user_id=tg_user_id, role=None, status=None)
        status = getattr(user, "status", None)
        if isinstance(status, str):
            # Defensive: if DB returns raw string for some reason.
            try:
                status = UserStatus(status)
            except ValueError:
                status = None
        return Principal(
            tg_user_id=tg_user_id,
            role=getattr(user, "role", None),
            status=status,
        )

    async def can_access_admin(self, tg_user_id: int) -> bool:
        """Check if user can access admin menu / admin commands."""
        # 0) Always respect static ADMIN_IDS allowlist.
        if tg_user_id in self._settings.admin_ids:
            return True

        principal = await self.get_principal(tg_user_id)

        # 1) Legacy behavior when new auth flow is disabled.
        if not self._settings.enable_new_auth_flow:
            return principal.role in (
                UserRole.ADMIN,
                UserRole.LEAD,
                UserRole.CURATOR,
            )

        # 2) New auth flow (expand-only for now): deny blocked/rejected,
        #    otherwise behave like legacy roles. Future tasks can refine.
        if principal.status in (UserStatus.BLOCKED, UserStatus.REJECTED):
            return False

        return principal.role in (
            UserRole.ADMIN,
            UserRole.LEAD,
            UserRole.CURATOR,
        )

