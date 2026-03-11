# Delivery Assistant — Backlog v2 (for Taskmaster)

## Epic: Infrastructure / Bootstrap

Goal: reliable local and containerized dev environment.

* Setup Docker Compose (postgres, redis, minio, bot, worker)
* Create Makefile commands (up, down, logs, migrate, bot, worker)
* Validate env config loading (DATABASE_URL, REDIS_URL, BOT_TOKEN)
* Add structured logging setup

Definition of Done:

* docker compose up works
* bot container starts
* worker container starts

---

## Epic: Database / Persistence

Goal: stable DB schema and repositories.

* Implement async SQLAlchemy session
* Define ORM models (users, assets, asset_assignments, events)
* Create initial Alembic migration
* Implement repository layer
* Add DB indexes and constraints

Definition of Done:

* alembic upgrade head works
* repositories used by services

---

## Epic: Core Services

Goal: move business logic out of handlers.

* Implement AssetsService
* Implement IncidentService
* Implement NotificationService
* Implement IngestService

Definition of Done:

* handlers call services only
* services interact with repositories

---

## Epic: Queue / Async Workers

Goal: background processing.

* Setup Celery worker
* Implement notification delivery task
* Implement CSV ingestion task
* Add retry logic and error logging

Definition of Done:

* worker processes tasks from queue

---

## Epic: Bot / Admin / FSM

Goal: user interface for operators.

* Implement /start handler
* Implement admin menu
* Implement asset issue/return FSM
* Implement incident creation flow
* Implement CSV upload flow

Definition of Done:

* admin flows work end-to-end

---

## Epic: AI Curator / Knowledge

Goal: intelligent assistant for delivery operations.

* Standardize FAQ repository
* Implement FAQ search service
* Implement routing logic (must-match → FAQ → LLM → escalate)
* Add Redis chat history
* Add explainability logging

Definition of Done:

* curator answers based on FAQ or escalates

---

## Epic: Architecture Alignment

Goal: remove duplicate AI modules.

* Audit current AI module layout
* Choose canonical AI package
* Mark legacy modules
* Add compatibility adapters

Definition of Done:

* one canonical AI service layer

---

## Epic: Observability

Goal: reliable debugging.

* Add structured logs
* Add correlation IDs
* Add health checks
* Add retry metrics

Definition of Done:

* logs contain task_id and request context

---

## Epic: Tests

Goal: ensure system reliability.

* Setup pytest + pytest-asyncio
* Test repositories
* Test service layer
* Add AI routing regression tests

Definition of Done:

* tests run with `pytest`

---

## Epic: Documentation

Goal: maintainable project knowledge.

* Update ARCHITECTURE.md
* Update DEPLOYMENT.md
* Update RUNBOOK.md
* Document AI curator logic

Definition of Done:

* docs reflect actual architecture
