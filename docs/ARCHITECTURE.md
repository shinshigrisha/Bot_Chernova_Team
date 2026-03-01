# Architecture

## Goals
- Telegram is only a notification/UI channel
- Core logic is service-based and testable
- Idempotent ingest and reliable notifications

## High-level components
- Telegram Adapter (aiogram)
- Core Services
- Repositories (PostgreSQL)
- Queue Workers (Celery/RQ)
- Storage (S3/MinIO)
- Integrations (Superset CSV/API/DB)
- AI Curator (RAG)

## Data flow: ingest → calc → snapshots → alerts
1) CSV/API/DB rows -> `ingest_batches`
2) Parse -> `delivery_orders_raw`
3) Calc -> `delivery_orders_calc`
4) Aggregate -> `metrics_snapshot`
5) Alerting -> `notifications` -> delivery attempts

## Notifications
- `NotificationService` creates records
- `TelegramChannel` (plugin) delivers with rate limiting and retries
- Optional `EmailChannel` / `WebInbox`

## Scheduling
- Scheduler triggers queue tasks; avoid duplicate execution with single leader or distributed locks.

## RBAC
- Roles: ADMIN, LEAD, CURATOR, VIEWER, (optional) COURIER
- Scope: territory/team + ds_id
