# Delivery Assistant

This repository contains the Delivery Assistant system (Telegram bot + backend services) for managing delivery operations:
- Shifts & polls
- Assets (TMC)
- Shift log & incidents
- Superset data ingest (CSV/API/DB)
- Analytics, alerts, daily reporting
- AI Curator (RAG)

## Quickstart (dev)
1. Copy `.env.example` to `.env` and fill values
2. `docker compose up -d --build`
3. Apply migrations: `make migrate`
4. Run bot locally (optional): `make bot`

See:
- docs/DEPLOYMENT.md
- docs/ADMIN_GUIDE.md

Generated: 2026-03-01
