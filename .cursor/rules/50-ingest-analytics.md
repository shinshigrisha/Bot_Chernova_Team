# Ingest & Analytics Rules

## Ingest
- Accept file → store in S3/MinIO → create `ingest_batch` with `content_hash`
- Parse rows into `delivery_orders_raw` (append-only), keep `raw` jsonb
- Idempotency: same content_hash must not duplicate raw data

## Calc
- Compute `delivery_orders_calc` with `calc_version` and `calc_at`
- Never overwrite calc without version bump or explicit "recalc" command
- Keep rules_version in batch; calc_version = rules_version + algorithm version

## ZiZ gating
- Compute `zone_coverage` (share of rows with non-null zone_code)
- If below threshold (default 0.95): disable ZiZ analytics, use Store-only, show warning

## Snapshots
- Aggregate into `metrics_snapshot` by ts_bucket (5/15 min)
- Use consistent bucketing function

## Heavy tasks
- Parsing, calc, snapshots, alert generation: all in queue tasks
