# Notifications Rules

## Channel-agnostic
All alerts/reports create `notifications` + `notification_targets` records.
Delivery is performed by worker(s) via channel plugins.

## Rate limits & retries
- Implement global and per-chat throttling.
- Handle Telegram 429 using `retry_after`.
- Exponential backoff for transient errors.
- Store every attempt in `notification_delivery_attempts`.

## Dedupe and digest
- For online alerts: max 1 message per scope (ds/ziz) per 15-minute bucket.
- Use `dedupe_key = type + scope + bucket_ts`.
- Prefer digest messages over multiple individual alerts.

## Observability
- Metrics: queued, delivered, failed, retries, time-to-deliver.
- Alerts if delivery failure rate exceeds threshold.
