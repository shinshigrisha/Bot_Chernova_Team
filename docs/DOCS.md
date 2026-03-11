# Документация Delivery Assistant

Единый справочник по проекту: запуск, развёртывание, архитектура, данные, администрирование и устранение неполадок.

---

## Оглавление

1. [Обзор и быстрый старт](#1-обзор-и-быстрый-старт)
2. [Развёртывание](#2-развёртывание)
3. [Архитектура](#3-архитектура)
4. [Словарь данных](#4-словарь-данных)
5. [Runbook / Устранение неполадок](#5-runbook--устранение-неполадок)
6. [Руководство администратора](#6-руководство-администратора)
7. [Безопасность](#7-безопасность)
8. [AI-куратор](#8-ai-куратор)
9. [Прочие артефакты](#9-прочие-артефакты)

---

## 1. Обзор и быстрый старт

В репозитории — система **Delivery Assistant** (Telegram-бот и бэкенд-сервисы) для управления операциями доставки:

- Смены и опросы
- ТМЦ (активы)
- Журнал смены и инциденты
- Загрузка данных из Superset (CSV/API/DB)
- Аналитика, алерты, ежедневная отчётность
- AI Curator (RAG)

### Быстрый старт (разработка)

1. Скопировать `.env.example` в `.env` и заполнить значения.
2. `docker compose up -d --build`
3. Применить миграции: `make migrate`
4. Запустить бота: `make bot` (или `docker compose up bot`)

### Подъём через docker-compose (полный цикл)

1. **Подготовить `.env`:**
   - `BOT_TOKEN`
   - `DATABASE_URL` (по умолчанию подходит compose-сеть)
   - `REDIS_URL`, `CELERY_BROKER_URL`
   - для AI: `AI_ENABLED=true` и минимум один ключ: `GROQ_API_KEY` и/или `OPENAI_API_KEY` и/или `DEEPSEEK_API_KEY` (+ `DEEPSEEK_BASE_URL`)

2. **Поднять сервисы:** `docker compose up -d --build`

3. **Миграции:** `make migrate` или `python -m alembic upgrade head`

4. **Проверка AI:** в Telegram у админа выполнить `/ai_status`

5. **(Опционально) FAQ:** `python scripts/seed_faq.py` или через `/ai_add_faq`

6. **Smoke-проверка AI без Telegram:** `python scripts/smoke_ai.py`

7. **Полезные команды:**
   - логи бота: `docker compose logs -f bot`
   - логи воркера: `docker compose logs -f worker`
   - остановка: `docker compose down`; с удалением данных: `docker compose down -v`

---

## 2. Развёртывание

### Локальный запуск (MVP)

1. Скопировать `.env.example` в `.env`, задать `BOT_TOKEN` и при необходимости `ADMIN_IDS`.
2. Поднять стек: `make up` или `docker compose up -d`.
3. Применить миграции: `make migrate` (или `docker compose run --rm bot alembic upgrade head`).
4. Запустить бота: `make bot` или `docker compose up bot`.
5. Запустить воркер: `make worker` или `docker compose up worker`.

**Проверка:** в Telegram отправить боту `/start` и `/admin`; логи — `docker compose logs -f bot`.

**Важно:** если бот раньше работал по webhook, при старте он сбрасывает webhook (чтобы long polling получал обновления). Если бот не отвечает на команды — убедитесь, что миграции применены (`make migrate`) и в логах есть строка `Webhook cleared for polling`.

**Тесты:** после `make up` и `make migrate`: `pytest tests/ -v` (используется `DATABASE_URL` из окружения).

### Службы (docker-compose)

- **postgres** (postgres:16-alpine): БД.
- **redis** (redis:7-alpine): брокер/бэкенд Celery.
- **minio**: S3-совместимое хранилище, порты 9000 (API) и 9001 (консоль).
- **bot**: aiogram, команда `python -m src.bot.main`.
- **worker**: Celery worker, команда `celery -A src.infra.queue.celery_app worker --loglevel=info`.
- **scheduler**: опционально.

### Переменные окружения

Обязательные (см. `.env.example`):

- `BOT_TOKEN` — токен Telegram-бота
- `ADMIN_IDS` — список ID через запятую для доступа в админку
- `DATABASE_URL` — `postgresql+asyncpg://user:pass@postgres:5432/delivery_assistant`
- `REDIS_URL` — `redis://redis:6379/0`
- `CELERY_BROKER_URL` — `redis://redis:6379/1`
- `S3_ENDPOINT`, `S3_ACCESS_KEY`, `S3_SECRET_KEY`, `S3_BUCKET` — для MinIO

Опционально: `TIMEZONE`, `LOG_LEVEL`, `AI_ENABLED`, ключи провайдеров AI.

### Миграции

- При развёртывании: `make migrate` или `docker compose run --rm bot alembic upgrade head`.
- Перед миграциями — резервная копия БД.
- Откат: `alembic downgrade -1` (по необходимости).

### Резервное копирование и обновление

- Ежедневный дамп PostgreSQL (pg_dump); версионирование бакета S3/MinIO.
- **Обновление:** git pull → `docker compose build` → `make migrate` → `docker compose up -d` → проверить логи и health.
- **Откат:** восстановить БД из бэка; развернуть предыдущий образ и перезапустить контейнеры.

---

## 3. Архитектура

### Цели

- Telegram — только канал уведомлений и UI.
- Бизнес-логика в сервисах, тестируемая отдельно.
- Идемпотентный ingest и надёжная доставка уведомлений.

### Схема модулей и поток данных

- **Handlers** (aiogram): валидация ввода, вызов сервисов, ответ пользователю. Долгие операции и рассылки — только через очередь.
- **Core Services**: бизнес-сценарии (ТМЦ, инцидент, уведомление, ingest). Работают с репозиториями и ставят задачи в Celery.
- **Repositories**: доступ к БД (PostgreSQL, async SQLAlchemy 2).
- **Celery**: задачи `deliver_notification`, `parse_ingest_batch` и др. Доставка уведомлений через TelegramChannel с учётом 429 и retry.
- **MinIO/S3**: хранение загруженных CSV и артефактов.

### Компоненты верхнего уровня

- **src/bot**: Telegram-адаптер (aiogram 3), handlers, admin menu, FSM (ТМЦ, журнал, импорт CSV).
- **src/core/services**: AssetsService, ShiftLogService, NotificationService, IngestService.
- **src/infra/db**: сессия, модели, репозитории.
- **src/infra/queue**: Celery app, задачи доставки и парсинга.
- **src/infra/notifications**: каналы (TelegramChannel), интерфейс DeliveryResult.
- **src/infra/storage**: S3/MinIO клиент для ingest-файлов.
- **src/infra/integrations**: зарезервировано (Superset API/DB, парсеры).

### Поток данных: ingest → calc → snapshots → alerts

1. Строки CSV/API/DB → `ingest_batches` (UNIQUE source + content_hash).
2. Парсинг (очередь) → `delivery_orders_raw` (zone_code nullable).
3. Расчёт → `delivery_orders_calc`.
4. Агрегация → `metrics_snapshot`.
5. Алерты → `notifications` → `notification_targets` → worker → `notification_delivery_attempts` (Telegram и др.).

### Уведомления

- `NotificationService.enqueue_notification()` создаёт записи в БД и ставит задачу в Celery. Из handlers рассылки не отправляются.
- Worker выполняет `deliver_notification(notification_id)`: при 429 — запись attempt и retry с countdown. Дедуп по `dedupe_key` (UNIQUE в БД).

### Планировщик и RBAC

- Scheduler (опционально): один экземпляр или распределённая блокировка.
- Роли: ADMIN, LEAD, CURATOR, VIEWER, COURIER. Доступ к /admin: роль из (ADMIN, LEAD, CURATOR) или ID в ADMIN_IDS. Область видимости: user_scopes (team_id, darkstore_id).

---

## 4. Словарь данных

### MVP: справочники и пользователи

- **territories**, **teams**, **darkstores**, **users** (tg_user_id UNIQUE, role, display_name), **user_scopes**, **couriers**, **chat_bindings** (team_id, chat_id, category, topic_id).

### MVP: ТМЦ и журнал смены

- **assets** (darkstore_id, asset_type, serial, status, condition); **asset_assignments**; **asset_events**.
- **shift_log** (darkstore_id, log_type, severity, title, details, created_by).

### MVP: уведомления

- **notifications** (type, status, dedupe_key, payload); **notification_targets**; **notification_delivery_attempts**.

### Ingest и заказы

- **ingest_batches**: source (csv_upload | superset_api | db_direct), content_hash, rules_version.
- **delivery_orders_raw**: batch_id, order_key, ds_code, zone_code (nullable), start_delivery_at, deadline_at, finish_at_raw, durations (jsonb), raw (jsonb).
- **delivery_orders_calc**: finish_at_effective, remaining_pct, timer_sign, флаги ignore, is_violation_*, assembly_share, trip_id и др.

### Zone gating

- zone_coverage по батчу/дню; ниже порога → отчётность только Store-only.

---

## 5. Runbook / Устранение неполадок

### Бот не отвечает

- Проверить, что контейнер bot запущен: `docker compose ps`.
- Логи: `docker compose logs -f bot`. Убедиться, что BOT_TOKEN задан и нет ошибок при старте.
- Проверить доступность postgres и redis из контейнера bot.
- Убедиться, что в логах есть `Webhook cleared for polling` и при отправке сообщений боту появляютcя записи о входящих обновлениях (см. логирование в коде). Если обновлений нет — возможны сетевые ограничения доступа контейнера к api.telegram.org.

### Миграция не применяется

- Проверить DATABASE_URL (async: postgresql+asyncpg://...). Убедиться, что postgres здоров: `docker compose up -d postgres`, затем `make migrate`. При ошибках enum/таблиц — порядок миграций и downgrade.

### Лимиты Telegram (429)

- Учитывать retry_after, снизить частоту, включить дайджест, дедупликация. Убедиться, что отправка идёт через очередь, а не из handlers.

### Привязки чата/топика, алерты

- Проверить привязки в админ-интерфейсе и права бота в топиках форума.

### Ошибки ingest (CSV/API)

- Сверить колонки CSV с Data Dictionary, часовой пояс; повторить загрузку с исправленным файлом.

### Аналитика ZiZ отключена

- Обеспечить стабильную передачу zone_code из источника; иначе режим Store-only.

### Дублирование запланированных задач

- Один экземпляр scheduler или распределённая блокировка.

### Перерасчёт

- При изменении rules_version: /admin → Аналитика → Перерасчёт за период (через очередь).

---

## 6. Руководство администратора

### Вход в админку

- Команда `/admin` в боте. Доступ: роль ADMIN, LEAD или CURATOR либо Telegram ID в списке ADMIN_IDS.

### Пункты админ-меню (MVP)

- **ТМЦ** — выдача ТМЦ: выбор ДС, курьер, тип ТМЦ, серийный номер, состояние, опционально фото. Запись в assets/asset_assignments/asset_events.
- **Журнал смены** — создание инцидента: ДС, серьёзность, заголовок, описание.
- **Импорт CSV** — загрузка файла (документом). Batch по content_hash, файл в MinIO, задача парсинга в очередь.
- **Настройки** / **Мониторинг** — в разработке.

### Роли

- **ADMIN**: территории/команды, привязки чатов, топики, расписания, интеграции, база знаний и политики AI, мониторинг.
- **LEAD**: дашборды, отчёты, подтверждение рекомендаций, аудит.
- **CURATOR**: ТМЦ, инциденты, журнал смены, дашборды по ДС, отметка «применено вручную».
- **VIEWER / AUDITOR**: только чтение, экспорт отчётов.
- **COURIER**: свои назначения, ТМЦ, вопросы к AI (FAQ).

---

## 7. Безопасность

- **Секреты:** не коммитить токены и пароли; в проде — secret manager.
- **Сеть:** Postgres и Redis в compose без публичных портов; ограничить входящий доступ к эндпоинтам в проде.
- **RBAC:** проверка роли при каждом админ-действии; область видимости по user_scopes.
- **Аудит:** фиксировать, кто что и когда сделал; неизменяемые логи по критичным действиям.
- **Доступ к данным:** учётные данные к Superset — только на чтение.

---

## 8. AI-куратор

### Назначение

Сервис отвечает по многоуровневой схеме: rule-based → FAQ (RAG) → LLM-провайдеры → эскалация к человеку. Реализация: код — `src/core/services/ai/`, политика и промпты — `data/ai/` (core_policy.json, intent_tags.json, prompts/*).

### Формат ответа

Суть ситуации; кто отвечает; почему (правило/логика); что делать сейчас; при необходимости — тег, регламент, эскалация.

### Провайдеры и переменные

- OpenAI, DeepSeek (OpenAI SDK), Groq. Переменные: `AI_ENABLED`, `*_API_KEY`, `*_MODEL`, `AI_PROVIDER_ORDER_CHAT`, `AI_PROVIDER_ORDER_REASON`. Пример в `.env.example`.

### FAQ и policy

- Добавление FAQ: `/ai_add_faq` (FSM). Поиск: `/ai_search_faq <текст>`. Перезагрузка policy без рестарта: `/ai_policy_reload`.

### Типовые проблемы

- Нет ответа / эскалация: низкая уверенность по FAQ, рискованный кейс по policy. Пустая база FAQ — чаще fallback/эскалация. Нет ключей API — только FAQ/fallback, без LLM. Таймауты — роутер переключается на следующий провайдер.

### Smoke-тест

- `python scripts/smoke_ai.py` (golden_cases.jsonl). Локально без Telegram.

---

## 9. Прочие артефакты

- **ADR** (Architecture Decision Records): шаблон и записи в `docs/ADR/`.
- **AUDIT_STATUS_2026-03-01.md** — отчёт аудита на дату.

---

*Дата сводки: 2026-03-02*
