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
    """Access / Role / Status Layer: единая точка решений по статусу и роли.

    Отвечает за:
    - что показать на /start (guest/pending/approved/rejected/blocked);
    - какое меню открыть (по роли при approved);
    - может ли пользователь использовать AI (can_use_ai);
    - кто может видеть admin panel (can_access_admin);
    - кому слать verification alerts (get_verification_alert_recipient_ids).

    См. docs/ACCESS_ROLE_STATUS_LAYER.md.
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

    async def can_use_ai(self, tg_user_id: int) -> bool:
        """Разрешён ли пользователю доступ к AI-куратору (answer_user / AI-меню).

        Только approved; guest, pending, rejected, blocked — нет.
        """
        principal = await self.get_principal(tg_user_id)
        if principal.status is None or principal.status != UserStatus.APPROVED:
            return False
        if principal.status == UserStatus.BLOCKED:
            return False
        return True

    def get_verification_alert_recipient_ids(self) -> list[int]:
        """Список tg_user_id, которым слать уведомления о новой заявке на верификацию.

        По умолчанию — ADMIN_IDS из конфига.
        """
        return list(self._settings.admin_ids)

