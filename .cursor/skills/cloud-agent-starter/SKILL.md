---
name: cloud-agent-starter
description: Минимальный run/test skill для Cloud-агентов Delivery Assistant.
---

# Cloud Agent Starter Skill (Delivery Assistant)

Минимальный практический гайд, который нужен Cloud-агенту в первые минуты работы.

## 0) Быстрый старт за 10 минут

1. Подготовь окружение:
   - `cp .env.example .env`
   - заполни минимум: `BOT_TOKEN`, `ADMIN_IDS`, `DATABASE_URL`, `REDIS_URL`, `CELERY_BROKER_URL`
2. Подними стек:
   - `make up`
   - `docker compose ps`
3. Прогони миграции:
   - `make migrate`
4. Проверь, что бот и воркер живы:
   - `docker compose logs -f bot`
   - `docker compose logs -f worker`

Ожидаемый сигнал успеха: контейнеры `postgres`, `redis`, `minio`, `bot`, `worker` в статусе `running`/`healthy`, миграции применяются без ошибок.

## 1) Логин и доступы (что обычно ломается первым)

### Telegram / админ-доступ

- Админ-функции зависят от `ADMIN_IDS`.
- Поддерживаются форматы:
  - `ADMIN_IDS=123456789`
  - `ADMIN_IDS=123456789,987654321`
  - `ADMIN_IDS=[123456789,987654321]`
- Если `/admin` или `/ai_status` отвечает «Нет доступа», сначала проверь `ADMIN_IDS` в `.env`.

### MinIO / S3

- Локальная консоль MinIO: `http://localhost:9001`
- Логин по умолчанию: `minioadmin / minioadmin` (если не переопределено в `.env`).

## 2) Фича-флаги и моки (для Cloud-диагностики)

### AI-режим

- Выключенный AI (без внешних ключей, детерминированный режим):
  - `AI_ENABLED=false`
  - тестируем rule-based/FAQ/fallback без сетевых зависимостей.
- Включенный AI:
  - `AI_ENABLED=true`
  - минимум один ключ: `GROQ_API_KEY` или `DEEPSEEK_API_KEY` или `OPENAI_API_KEY`.

### Быстрый мок «без LLM»

Если нужно проверить только конвейер и fallback, оставь `AI_ENABLED=false` и запусти:
- `python scripts/smoke_ai.py`

## 3) Запуск и тесты по зонам кодовой базы

## A. Telegram-адаптер (`src/bot/*`)

Когда использовать: проверка команд, FSM, middleware, админ-роутинга.

Run:
- `make up`
- `make migrate`
- `docker compose logs -f bot`

Manual smoke:
- в Telegram отправить `/start`
- отправить `/admin` (с admin ID)
- отправить `/ai_status`

Terminal checks:
- `pytest tests/test_user_smoke.py -v`

## B. Core AI (`src/core/services/ai/*`, `data/ai/*`)

Когда использовать: маршрутизация ответов, fallback, policy reload.

Run:
- `python scripts/smoke_ai.py`
- `python scripts/smoke_provider_router.py`

Targeted tests:
- `pytest tests/test_ai_policy_routes.py -v`
- `pytest tests/test_case_classifier.py -v`
- `pytest tests/test_intent_engine_catalog.py -v`

Полезный сценарий:
1. Выставить `AI_ENABLED=false` и проверить fallback.
2. Включить `AI_ENABLED=true` + 1 провайдерный ключ и повторить smoke.

## C. БД и репозитории (`src/infra/db/*`, `migrations/*`)

Когда использовать: проблемы с enum, миграциями, репозиториями.

Run:
- `make migrate`
- `docker compose run --rm bot alembic current`

Targeted tests:
- `pytest tests/test_assets_repository.py -v`
- `pytest tests/test_ingest_repository.py -v`
- `pytest tests/test_faq_semantic_search.py -v`

Если ошибка `invalid input value for enum user_role`, проверь lowercase-значения enum и актуальность миграций.

## D. Очередь и уведомления (`src/infra/queue/*`, `src/infra/notifications/*`)

Когда использовать: не уходят уведомления, retries, дедупликация.

Run:
- `docker compose logs -f worker`
- `docker compose exec worker celery -A src.infra.queue.celery_app inspect active`

Targeted tests:
- `pytest tests/test_notification_delivery.py -v`

## E. Ingest и данные (`src/core/services/ingest.py`, `scripts/*`, `src/infra/storage/*`)

Когда использовать: падения batch ingest, проблемы с CSV/API, устаревшие эмбеддинги FAQ.

Run / scripts:
- `python scripts/seed_faq.py`
- `python scripts/rebuild_faq_embeddings.py`
- `python scripts/rebuild_case_embeddings.py`

Targeted tests:
- `pytest tests/test_case_memory_integration.py -v`
- `pytest tests/test_ingest_repository.py -v`

## 4) Базовый Cloud workflow (повторяемый)

1. `cp .env.example .env`
2. Проставь критичные env (`BOT_TOKEN`, `ADMIN_IDS`, DB/Redis/Celery URLs).
3. `make up && make migrate`
4. Прогони точечные тесты только по затронутой зоне.
5. Если зона UI/бот-команд — добей manual smoke через Telegram.
6. Собери evidence в ответе: команды + ключевые логи + что именно проверено.

## 5) Как обновлять этот skill при новых находках

Когда появляется новый «рабочий трюк» из реальной диагностики:

1. Добавь его в соответствующую зону (A–E), не в общий раздел.
2. Формат записи:
   - **Симптом**
   - **Команда(ы)**
   - **Ожидаемый сигнал успеха**
   - **Rollback/безопасный откат** (если применимо)
3. Предпочитай точечные команды вместо «запусти всё».
4. Если найден repeatable баг/фикс — добавь рядом минимальный targeted test.
5. Держи файл минимальным: только то, что агенту нужно в первые 5–15 минут.

Критерий качества обновления: новый инженер/агент может воспроизвести диагностику и получить такой же результат без устных пояснений.
