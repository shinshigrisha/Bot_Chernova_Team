"""Assets and assignments repository."""
from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.infra.db.enums import AssetCondition, AssetStatus, AssetType
from src.infra.db.models import Asset, AssetAssignment, AssetEvent, Courier


class AssetsRepository:
    """Repository for assets, assignments, and asset events."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create_asset(
        self,
        darkstore_id: UUID,
        asset_type: AssetType,
        serial: str,
        condition: AssetCondition,
        status: AssetStatus = AssetStatus.AVAILABLE,
    ) -> Asset:
        asset = Asset(
            darkstore_id=darkstore_id,
            asset_type=asset_type,
            serial=serial,
            status=status,
            condition=condition,
        )
        self._session.add(asset)
        await self._session.flush()
        return asset

    async def get_by_type_serial(
        self, darkstore_id: UUID, asset_type: AssetType, serial: str
    ) -> Asset | None:
        result = await self._session.execute(
            select(Asset).where(
                Asset.darkstore_id == darkstore_id,
                Asset.asset_type == asset_type,
                Asset.serial == serial,
            )
        )
        return result.scalars().one_or_none()

    async def get_active_assignment(self, asset_id: UUID) -> AssetAssignment | None:
        result = await self._session.execute(
            select(AssetAssignment).where(
                AssetAssignment.asset_id == asset_id,
                AssetAssignment.returned_at.is_(None),
            )
        )
        return result.scalars().one_or_none()

    async def create_assignment(self, asset_id: UUID, courier_id: UUID) -> AssetAssignment:
        assignment = AssetAssignment(
            asset_id=asset_id,
            courier_id=courier_id,
        )
        self._session.add(assignment)
        await self._session.flush()
        return assignment

    async def close_assignment(self, assignment_id: UUID) -> None:
        result = await self._session.execute(
            select(AssetAssignment).where(AssetAssignment.id == assignment_id)
        )
        assignment = result.scalars().one_or_none()
        if assignment:
            assignment.returned_at = datetime.utcnow()

    async def get_assignment(self, assignment_id: UUID) -> AssetAssignment | None:
        result = await self._session.execute(
            select(AssetAssignment).where(AssetAssignment.id == assignment_id)
        )
        return result.scalars().one_or_none()

    async def update_asset_status(self, asset_id: UUID, status: AssetStatus) -> None:
        result = await self._session.execute(select(Asset).where(Asset.id == asset_id))
        asset = result.scalars().one_or_none()
        if asset:
            asset.status = status

    async def create_asset_event(
        self,
        asset_id: UUID,
        event_type: str,
        assignment_id: UUID | None = None,
        payload: dict | None = None,
    ) -> AssetEvent:
        event = AssetEvent(
            asset_id=asset_id,
            assignment_id=assignment_id,
            event_type=event_type,
            payload=payload,
        )
        self._session.add(event)
        await self._session.flush()
        return event

    async def get_courier_by_external_key(
        self, darkstore_id: UUID, external_key: str
    ) -> Courier | None:
        result = await self._session.execute(
            select(Courier).where(
                Courier.darkstore_id == darkstore_id,
                Courier.external_key == external_key,
            )
        )
        return result.scalars().one_or_none()
