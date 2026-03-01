"""Tests for AssetsRepository: one active assignment per asset."""
import pytest
from sqlalchemy.exc import IntegrityError

from src.infra.db.enums import AssetCondition, AssetStatus, AssetType
from src.infra.db.models import Asset, AssetAssignment, Courier, Darkstore, Team, Territory
from src.infra.db.repositories.assets import AssetsRepository

pytestmark = pytest.mark.asyncio


async def _create_darkstore_and_courier(session) -> tuple:
    """Create territory, team, darkstore, courier. Return (darkstore_id, courier_id)."""
    t = Territory(name="T1")
    session.add(t)
    await session.flush()
    team = Team(territory_id=t.id, name="Team1")
    session.add(team)
    await session.flush()
    ds = Darkstore(team_id=team.id, code="DS1", name="Dark 1", is_white=False)
    session.add(ds)
    await session.flush()
    courier = Courier(darkstore_id=ds.id, external_key="c1", name="Courier 1")
    session.add(courier)
    await session.flush()
    return ds.id, courier.id


async def test_issue_asset_one_active_assignment(async_session) -> None:
    """One asset can have only one active (returned_at IS NULL) assignment."""
    repo = AssetsRepository(async_session)
    darkstore_id, courier_id = await _create_darkstore_and_courier(async_session)
    await async_session.commit()

    asset = await repo.create_asset(
        darkstore_id=darkstore_id,
        asset_type=AssetType.BIKE,
        serial="S1",
        condition=AssetCondition.GOOD,
        status=AssetStatus.ASSIGNED,
    )
    await async_session.flush()
    a1 = await repo.create_assignment(asset.id, courier_id)
    await async_session.commit()

    active = await repo.get_active_assignment(asset.id)
    assert active is not None
    assert active.id == a1.id

    # Second assignment on same asset while first is active must violate unique
    await repo.create_assignment(asset.id, courier_id)
    with pytest.raises(IntegrityError):
        await async_session.flush()
    await async_session.rollback()


async def test_close_assignment_then_second_allowed(async_session) -> None:
    """After closing assignment, another can be created on same asset."""
    repo = AssetsRepository(async_session)
    darkstore_id, courier_id = await _create_darkstore_and_courier(async_session)
    await async_session.commit()

    asset = await repo.create_asset(
        darkstore_id=darkstore_id,
        asset_type=AssetType.BATTERY,
        serial="B1",
        condition=AssetCondition.GOOD,
        status=AssetStatus.ASSIGNED,
    )
    await async_session.flush()
    a1 = await repo.create_assignment(asset.id, courier_id)
    await async_session.commit()

    await repo.close_assignment(a1.id)
    await async_session.commit()

    active = await repo.get_active_assignment(asset.id)
    assert active is None

    a2 = await repo.create_assignment(asset.id, courier_id)
    await async_session.commit()
    assert a2.id != a1.id
    active2 = await repo.get_active_assignment(asset.id)
    assert active2 is not None and active2.id == a2.id
