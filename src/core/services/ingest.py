"""Ingest service: accept CSV upload, store in MinIO, create batch, enqueue parse."""
import hashlib
from uuid import UUID

from src.infra.db.enums import IngestSource, IngestStatus
from src.infra.db.repositories.ingest import IngestRepository
from src.infra.db.session import async_session_factory
from src.infra.storage.s3 import put_ingest_file


class IngestService:
    """Service for accepting ingest files (idempotent by content_hash)."""

    async def accept_csv_upload(
        self,
        file_bytes: bytes,
        filename: str,
        source: IngestSource = IngestSource.CSV_UPLOAD,
    ) -> tuple[UUID, bool]:
        """
        Compute content_hash, check duplicate. If new: save to MinIO, create batch, enqueue parse.
        Returns (batch_id, is_new).
        """
        content_hash = hashlib.sha256(file_bytes).hexdigest()

        async with async_session_factory() as session:
            repo = IngestRepository(session)
            existing = await repo.get_batch_by_source_hash(source, content_hash)
            if existing:
                await session.commit()
                return existing.id, False

            batch = await repo.create_batch(
                source=source,
                content_hash=content_hash,
                status=IngestStatus.PENDING,
            )
            await session.commit()
            batch_id = batch.id

        # Store file after commit
        put_ingest_file(batch_id, file_bytes, filename)

        # Enqueue parse task (worker will parse and insert raw rows, update status)
        from src.infra.queue.tasks import parse_ingest_batch_task

        parse_ingest_batch_task.delay(str(batch_id))
        return batch_id, True
