"""Тесты ShiftLogRepository: создание записей журнала смены и выборка по датам."""
import uuid

import pytest

from src.infra.db.enums import LogType, Severity
from src.infra.db.models import Darkstore, Team, Territory
from src.infra.db.repositories.shift_log import ShiftLogRepository

pytestmark = [pytest.mark.asyncio, pytest.mark.integration]


def _unique_suffix() -> str:
    return uuid.uuid4().hex[:8]


async def _create_darkstore(session, suffix: str):
    """Создать territory, team, darkstore. Вернуть darkstore_id."""
    t = Territory(name=f"T_{suffix}")
    session.add(t)
    await session.flush()
    team = Team(territory_id=t.id, name=f"Team_{suffix}")
    session.add(team)
    await session.flush()
    ds = Darkstore(team_id=team.id, code=f"DS_{suffix}", name=f"Dark {suffix}", is_white=False)
    session.add(ds)
    await session.flush()
    return ds.id


async def test_shift_log_create_and_list(async_session) -> None:
    """Создание инцидента и выборка по darkstore и диапазону дат."""
    suffix = _unique_suffix()
    darkstore_id = await _create_darkstore(async_session, suffix)
    repo = ShiftLogRepository(async_session)

    entry = await repo.create_log(
        darkstore_id=darkstore_id,
        log_type=LogType.INCIDENT,
        severity=Severity.HIGH,
        title="Тест инцидент",
        details="Описание",
    )
    await async_session.flush()
    assert entry.id is not None
    assert entry.title == "Тест инцидент"
    assert entry.severity == Severity.HIGH

    from datetime import date

    listed = await repo.list_by_darkstore_date(
        darkstore_id=darkstore_id,
        date_from=date(2000, 1, 1),
        date_to=date(2030, 12, 31),
    )
    assert len(listed) >= 1
    assert any(e.id == entry.id for e in listed)
