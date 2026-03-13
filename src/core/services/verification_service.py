"""Service layer for registration/verification applications."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from sqlalchemy.ext.asyncio import async_sessionmaker

from src.infra.db.enums import UserRole, UserStatus, coerce_user_role
from src.infra.db.models import User, VerificationApplication
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

    async def list_pending_with_applications(
        self,
    ) -> list[tuple[User, VerificationApplication]]:
        """Список пользователей в статусе PENDING и их последняя заявка."""
        async with self._session_factory() as session:
            user_repo = UserRepository(session)
            app_repo = VerificationApplicationRepository(session)
            pending_users = await user_repo.list_by_status(UserStatus.PENDING)
            if not pending_users:
                return []
            tg_ids = [u.tg_user_id for u in pending_users]
            applications = await app_repo.list_by_tg_user_ids(tg_ids)
            # Последняя заявка по каждому tg_user_id (уже order by created_at desc)
            by_tg: dict[int, VerificationApplication] = {}
            for app in applications:
                if app.tg_user_id not in by_tg:
                    by_tg[app.tg_user_id] = app
            result: list[tuple[User, VerificationApplication]] = []
            for u in pending_users:
                app = by_tg.get(u.tg_user_id)
                if app:
                    result.append((u, app))
            return result

    async def apply_admin_decision(
        self,
        *,
        tg_user_id: int,
        decision: str,
    ) -> UserStatus:
        """Apply admin decision to user status.

        decision: "approve" | "reject" | "block"
        Returns new UserStatus.
        Does not create users: only updates existing (avoids bypassing status model).
        """
        decision = decision.lower().strip()
        async with self._session_factory() as session:
            user_repo = UserRepository(session)
            app_repo = VerificationApplicationRepository(session)
            user = await user_repo.get_by_tg_id(tg_user_id)
            if user is None:
                raise ValueError(f"User not found: tg_user_id={tg_user_id}")

            if decision == "approve":
                user.status = UserStatus.APPROVED
            elif decision == "reject":
                user.status = UserStatus.REJECTED
            elif decision == "block":
                user.status = UserStatus.BLOCKED
            else:
                raise ValueError(f"Unknown decision: {decision}")

            await app_repo.set_resolution_for_latest(tg_user_id, decision)
            await session.commit()
            return user.status

