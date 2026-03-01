# DB & Migrations Rules

- Use Alembic for all schema changes.
- No manual SQL changes on prod DB.
- Every table must have:
  - primary key
  - `created_at` and `updated_at` if mutable entity
  - reasonable indexes
- Every “event/attempt” table must have:
  - foreign key to parent entity
  - timestamp
  - status enum
- Add uniqueness constraints that enforce invariants:
  - `shift_votes`: UNIQUE(shift_poll_id, user_id)
  - `ingest_batches`: UNIQUE(source, content_hash)
  - `notifications`: UNIQUE(dedupe_key) where appropriate (or enforce in code)

## Timestamp policy
- Store as timestamptz (UTC).
- Convert at boundaries.

## Seed & config tables
- Thresholds and schedules live in DB config tables, not hard-coded.
