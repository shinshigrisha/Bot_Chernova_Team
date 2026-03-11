# Project Overview — Delivery Assistant

**Purpose:** System to help territory delivery supervisors manage:
- Shifts & sign-up (polls), reminders
- Asset / TMC (bikes, batteries, bags, etc.)
- Shift log & incidents
- Data ingest from Superset (CSV upload / API pull / direct DB read)
- Analytics engine (raw → calc → snapshots), alerts & daily reports
- AI Curator (RAG) for FAQ + generation of operational texts

**Core principle:** Telegram is *only a channel*. Business logic lives on the server.

**Source of truth:** Final spec **TZ v1.4** (docx). Any change requires ADR + migrations.

## Modules
- `core/services`: business use-cases
- `infra/db`: SQLAlchemy models + repositories + sessions
- `infra/queue`: Celery/RQ tasks for ingest/analytics/notifications
- `infra/notifications`: channel plugins (telegram/email/web)
- `infra/integrations`: superset api/db/csv parsers
- `bot/`: aiogram handlers, FSM, keyboards (thin adapter)
- **AI (куратор):** код — `src/core/services/ai/`, политика и промпты — `data/ai/` (RAG KB, policies, prompts)

## Non-negotiables
- Idempotent ingest with `ingest_batches.content_hash`
- Poll integrity with `ShiftPollOption` snapshot + `ShiftVote.option_index` + UPSERT
- ZiZ analytics only when `zone_code` coverage >= threshold; else Store-only
- Notifications via queue with rate-limit, retries, dedupe, delivery attempts
- Timestamp storage: `timestamptz` (UTC), reports in business TZ (Europe/Moscow)
