"""Tests for IngestRepository: idempotent batch by source+content_hash."""
import uuid

import pytest

from src.infra.db.enums import IngestSource, IngestStatus
from src.infra.db.repositories.ingest import IngestRepository

pytestmark = pytest.mark.asyncio


async def test_ingest_batch_idempotent_by_content_hash(async_session) -> None:
    """Two create_batch with same source+content_hash: second does not create duplicate."""
    repo = IngestRepository(async_session)
    source = IngestSource.CSV_UPLOAD
    content_hash = ("a" * 32 + uuid.uuid4().hex)[:64]  # уникальный хэш на прогон, изоляция от других прогонов

    existing = await repo.get_batch_by_source_hash(source, content_hash)
    assert existing is None

    batch1 = await repo.create_batch(
        source=source,
        content_hash=content_hash,
        status=IngestStatus.PENDING,
    )
    await async_session.commit()
    assert batch1.id is not None

    # Second call with same source+content_hash: get_batch returns existing
    existing2 = await repo.get_batch_by_source_hash(source, content_hash)
    assert existing2 is not None
    assert existing2.id == batch1.id

    # Idempotent use case: caller checks get_batch_by_source_hash first and returns existing id.
