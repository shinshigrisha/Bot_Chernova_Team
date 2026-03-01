"""Assets (TMC) service: issue and return."""
from uuid import UUID

from src.core.domain.exceptions import AssetAlreadyAssignedError
from src.infra.db.enums import AssetCondition, AssetStatus, AssetType
from src.infra.db.repositories.assets import AssetsRepository
from src.infra.db.session import async_session_factory


class AssetsService:
    """Service for asset issuance and return."""

    async def issue_asset(
        self,
        darkstore_id: UUID,
        courier_id: UUID,
        asset_type: AssetType,
        serial: str,
        condition: AssetCondition,
        photo_file_id: str | None = None,
    ) -> UUID:
        """Issue asset to courier. Creates asset if not exists, then assignment. Raises if already assigned."""
        async with async_session_factory() as session:
            repo = AssetsRepository(session)
            asset = await repo.get_by_type_serial(darkstore_id, asset_type, serial)
            if not asset:
                asset = await repo.create_asset(
                    darkstore_id=darkstore_id,
                    asset_type=asset_type,
                    serial=serial,
                    condition=condition,
                    status=AssetStatus.ASSIGNED,
                )
            else:
                active = await repo.get_active_assignment(asset.id)
                if active:
                    raise AssetAlreadyAssignedError(
                        f"Asset {asset_type.value}/{serial} already assigned"
                    )
                await repo.update_asset_status(asset.id, AssetStatus.ASSIGNED)

            assignment = await repo.create_assignment(asset.id, courier_id)
            await repo.create_asset_event(
                asset_id=asset.id,
                assignment_id=assignment.id,
                event_type="issued",
                payload={"photo_file_id": photo_file_id} if photo_file_id else None,
            )
            await session.commit()
            return assignment.id

    async def return_asset(self, assignment_id: UUID) -> None:
        """Close assignment and record event."""
        from datetime import datetime, timezone

        async with async_session_factory() as session:
            repo = AssetsRepository(session)
            assignment = await repo.get_assignment(assignment_id)
            if not assignment:
                return
            await repo.close_assignment(assignment_id)
            await repo.update_asset_status(assignment.asset_id, AssetStatus.AVAILABLE)
            await repo.create_asset_event(
                asset_id=assignment.asset_id,
                assignment_id=assignment_id,
                event_type="returned",
            )
            await session.commit()
