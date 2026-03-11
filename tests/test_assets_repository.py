"""Tests for AssetsRepository: one active assignment per asset."""
import uuid

import pytest
from sqlalchemy.exc import IntegrityError

from src.infra.db.enums import AssetCondition, AssetStatus, AssetType
from src.infra.db.models import Courier, Darkstore, Team, Territory
from src.infra.db.repositories.assets import AssetsRepository

pytestmark = pytest.mark.asyncio


def _unique_suffix() -> str:
    """Короткий уникальный суффикс для изоляции тестов (нет конфликтов при любом порядке прогона)."""
    return uuid.uuid4().hex[:8]


async def _create_darkstore_and_courier(session, suffix: str) -> tuple:
    """Create territory, team, darkstore, courier. Return (darkstore_id, courier_id)."""
    t = Territory(name=f"T1_{suffix}")
    session.add(t)
    await session.flush()
    team = Team(territory_id=t.id, name=f"Team1_{suffix}")
    session.add(team)
    await session.flush()
    ds = Darkstore(team_id=team.id, code=f"DS1_{suffix}", name=f"Dark 1 {suffix}", is_white=False)
    session.add(ds)
    await session.flush()
    courier = Courier(darkstore_id=ds.id, external_key=f"c1_{suffix}", name="Courier 1")
    session.add(courier)
    await session.flush()
    return ds.id, courier.id


async def test_issue_asset_one_active_assignment(async_session) -> None:
    """One asset can have only one active (returned_at IS NULL) assignment."""
    suffix = _unique_suffix()
    repo = AssetsRepository(async_session)
    darkstore_id, courier_id = await _create_darkstore_and_courier(async_session, suffix)
    await async_session.commit()

    asset = await repo.create_asset(
        darkstore_id=darkstore_id,
        asset_type=AssetType.BIKE,
        serial=f"S1_{suffix}",
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
    with pytest.raises(IntegrityError):
        await repo.create_assignment(asset.id, courier_id)
        await async_session.flush()
    await async_session.rollback()


async def test_close_assignment_then_second_allowed(async_session) -> None:
    """After closing assignment, another can be created on same asset."""
    suffix = _unique_suffix()
    repo = AssetsRepository(async_session)
    darkstore_id, courier_id = await _create_darkstore_and_courier(async_session, suffix)
    await async_session.commit()

    asset = await repo.create_asset(
        darkstore_id=darkstore_id,
        asset_type=AssetType.BATTERY,
        serial=f"B1_{suffix}",
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
