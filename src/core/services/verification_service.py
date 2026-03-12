"""Service layer for registration/verification applications."""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.ext.asyncio import async_sessionmaker

from src.infra.db.enums import UserRole, UserStatus, coerce_user_role
from src.infra.db.repositories.users import UserRepository
from src.infra.db.repositories.verification_applications import (
    VerificationApplicationRepository,
)


@dataclass(slots=True, frozen=True)
class VerificationApplicationPayload:
    tg_user_id: int
    role: UserRole
    first_name: str
    last_name: str
    tt_number: str
    ds_code: str
    phone: str


class VerificationService:
    """Orchestrates creation of verification applications and user status changes."""

    def __init__(self, session_factory: async_sessionmaker) -> None:
        self._session_factory = session_factory

    async def create_application_and_mark_pending(
        self,
        payload: VerificationApplicationPayload,
    ) -> None:
        """Create verification application and set user status to pending.

        Expand-only behavior:
        - Always upserts user using existing UserRepository pattern.
        - Always sets status to PENDING (no role/status gating here yet).
        """
        async with self._session_factory() as session:
            user_repo = UserRepository(session)
            app_repo = VerificationApplicationRepository(session)

            role = coerce_user_role(payload.role, default=UserRole.COURIER)
            user = await user_repo.get_or_create(
                tg_user_id=payload.tg_user_id,
                role=role,
                display_name=None,
            )

            await app_repo.create(
                tg_user_id=payload.tg_user_id,
                role=role.value,
                first_name=payload.first_name,
                last_name=payload.last_name,
                tt_number=payload.tt_number,
                ds_code=payload.ds_code,
                phone=payload.phone,
            )

            user.status = UserStatus.PENDING
            await session.commit()

