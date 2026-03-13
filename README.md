# Delivery Assistant

Telegram-бот и бэкенд-система для управления операциями доставки: смены, активы (ТМЦ), инциденты, журнал смены, загрузка данных и AI-куратор для курьеров.

**Единственный источник документации по проекту — этот файл (README.md).** Здесь: описание проекта, структура, зависимости, стек, логика и процессы, руководство по развёртыванию и решению проблем, команды действий.

---

## Содержание

1. [Возможности](#возможности)
2. [Архитектура](#архитектура)
3. [Стек технологий](#стек-технологий)
4. [Быстрый старт](#быстрый-старт)
5. [Переменные окружения](#переменные-окружения)
6. [Структура проекта](#структура-проекта)
7. [База данных и миграции](#база-данных-и-миграции)
8. [AI-куратор](#ai-куратор)
9. [Команды бота](#команды-бота)
10. [Роли и админ-панель](#роли-и-админ-панель)
11. [Тесты](#тесты)
12. [Полезные команды](#полезные-команды)
13. [Развёртывание](#развёртывание)
14. [Health / Ops чеклист](#health--ops-чеклист)
15. [Устранение неполадок](#устранение-неполадок)
16. [Граница Python vs n8n](#граница-python-vs-n8n)
17. [Интеграция с n8n](#интеграция-с-n8n)
18. [Задачи и команды (Task Master)](#задачи-и-команды-task-master)

---

## Возможности

- **Управление сменами** — журнал смены, опросы, фиксация инцидентов
- **ТМЦ (активы)** — учёт инвентаря, выдача и возврат
- **Импорт данных** — загрузка CSV/API из Superset, идемпотентный ingest
- **Уведомления** — очередь на Celery, Telegram-канал, дедупликация
- **AI-куратор** — многоуровневый RAG: правила → FAQ-база → LLM → эскалация
- **Ролевой доступ** — ADMIN / LEAD / CURATOR / VIEWER / COURIER
- **Хранилище файлов** — MinIO/S3 для ingest-документов

---

## Архитектура

Система построена по трёхуровневой архитектуре:

```
┌─────────────────────────────────────────────┐
│              Telegram (aiogram 3)            │
│  Handlers · Admin FSM · Middlewares          │
└─────────────────┬───────────────────────────┘
                  │
┌─────────────────▼───────────────────────────┐
│              Core / Business Logic           │
│  AssetsService · ShiftLogService             │
│  NotificationService · IngestService         │
│  AICourierService (RAG + LLM)               │
└─────────────────┬───────────────────────────┘
                  │
┌─────────────────▼───────────────────────────┐
│              Infrastructure                  │
│  PostgreSQL · Redis · Celery · MinIO/S3     │
│  Repositories · TelegramChannel             │
└─────────────────────────────────────────────┘
```

**Поток данных ingest:**
CSV/API → IngestService → Repositories + MinIO → Celery Queue → уведомления в Telegram

**Поток AI-ответа:**
Сообщение → rule-based → FAQ (PostgreSQL ILIKE) → LLM (Groq / DeepSeek / OpenAI) → ответ или эскалация куратору

Реализация AI: код — `src/core/services/ai/` (AICourierService, ProviderRouter, providers), политика и промпты — `data/ai/`, FAQ — `src/infra/db/repositories/faq_repo.py`.

---

## Стек технологий

| Компонент | Технология |
|---|---|
| Telegram-адаптер | aiogram 3, FSM |
| База данных | PostgreSQL 16, SQLAlchemy 2 (async), Alembic |
| Очередь задач | Celery 5 + Redis |
| Хранилище файлов | MinIO / S3 (boto3) |
| AI-провайдеры | Groq (llama-3.1-70b), DeepSeek, OpenAI (gpt-4o-mini) |
| HTTP-клиент | httpx, openai SDK, groq SDK |
| Конфигурация | pydantic-settings, .env |
| Логирование | structlog |
| Тесты | pytest, pytest-asyncio |
| Линтинг | ruff, black |
| Контейнеризация | Docker, docker-compose |

---

## Быстрый старт

### Требования

- Docker и Docker Compose
- Python 3.11+ (для локального запуска скриптов)

### 1. Клонировать и настроить окружение

```bash
git clone <repo-url>
cd Bot_Chernova_Team

cp .env.example .env
# Отредактируй .env — минимум BOT_TOKEN и ADMIN_IDS
```

### 2. Поднять сервисы (Docker Compose + Makefile)

```bash
# Запуск всех сервисов в фоне
docker compose up -d --build
# или эквивалент через Makefile
make up
```

Это запустит: `postgres`, `redis`, `minio`, `bot`, `worker`.

Посмотреть статусы контейнеров:

```bash
docker compose ps
```

### 3. Применить миграции

```bash
# через Makefile
make migrate

# или вручную через docker compose:
docker compose run --rm bot alembic upgrade head
```

### 4. Проверить работу

Открой Telegram, напиши боту `/start` — должно прийти приветствие.
Напиши `/admin` — откроется меню администратора (если ваш ID в `ADMIN_IDS`).

### 5. (Опционально) Загрузить начальные FAQ для AI

```bash
python scripts/seed_faq.py
```

### 6. Smoke-тест AI без Telegram

```bash
python scripts/smoke_ai.py
```

---

## Переменные окружения

Скопируй `.env.example` в `.env` и заполни:

### Обязательные

| Переменная | Описание | Пример |
|---|---|---|
| `BOT_TOKEN` | Токен от BotFather | `123456:ABC-DEF...` |
| `ADMIN_IDS` | Telegram ID администраторов | `[123456789]` |
| `DATABASE_URL` | Строка подключения к PostgreSQL | `postgresql+asyncpg://user:pass@postgres:5432/delivery_assistant` |
| `REDIS_URL` | Строка подключения к Redis | `redis://redis:6379/0` |
| `CELERY_BROKER_URL` | Брокер для Celery | `redis://redis:6379/1` |

### MinIO / S3

| Переменная | По умолчанию | Описание |
|---|---|---|
| `S3_ENDPOINT` | `http://minio:9000` | Эндпоинт MinIO |
| `S3_ACCESS_KEY` | `minioadmin` | Ключ доступа |
| `S3_SECRET_KEY` | `minioadmin` | Секретный ключ |
| `S3_BUCKET` | `delivery-assistant` | Название бакета |

### AI-куратор (опционально)

| Переменная | Описание |
|---|---|
| `AI_ENABLED` | Включить AI (`true` / `false`, по умолчанию `false`) |
| `GROQ_API_KEY` | API ключ Groq (llama-3.1-70b-versatile) |
| `DEEPSEEK_API_KEY` | API ключ DeepSeek |
| `DEEPSEEK_BASE_URL` | Базовый URL DeepSeek (`https://api.deepseek.com`) |
| `OPENAI_API_KEY` | API ключ OpenAI |
| `OPENAI_MODEL` | Модель OpenAI (по умолчанию `gpt-4o-mini`) |
| `AI_PROVIDER_ORDER_CHAT` | Порядок провайдеров для диалога (`groq,deepseek,openai`) |
| `AI_PROVIDER_ORDER_REASON` | Порядок провайдеров для рассуждений (`openai,deepseek,groq`) |

---

## Структура проекта

```
.
├── src/
│   ├── config.py                      # Pydantic-settings конфигурация
│   ├── bot/
│   │   ├── main.py                    # Точка входа, инициализация бота
│   │   ├── states.py                  # FSM-состояния (aiogram)
│   │   ├── handlers/
│   │   │   ├── start.py               # /start
│   │   │   └── ai_chat.py             # AI-режим (/ai, /ai_off, свободный текст)
│   │   ├── admin/
│   │   │   ├── admin.py               # Главное меню /admin
│   │   │   ├── ai_admin.py            # AI команды (/ai_status и др.)
│   │   │   ├── incident.py            # Работа с инцидентами
│   │   │   ├── ingest.py              # Импорт данных
│   │   │   ├── menu.py                # Навигация
│   │   │   └── tmc_issue.py           # Выдача ТМЦ
│   │   └── middlewares/
│   │       ├── ai_inject.py           # DI: пробрасывает ai_service в хендлеры
│   │       └── log_updates.py         # Структурированное логирование обновлений
│   ├── core/
│   │   ├── domain/
│   │   │   └── exceptions.py          # Доменные исключения
│   │   └── services/
│   │       ├── assets.py              # Сервис активов
│   │       ├── ingest.py              # Сервис импорта
│   │       ├── notifications.py       # Сервис уведомлений
│   │       ├── shift_log.py           # Сервис журнала смены
│   │       └── ai/
│   │           ├── ai_courier_service.py   # Главный AI-конвейер
│   │           ├── provider_router.py      # Роутер LLM-провайдеров с fallback
│   │           └── providers/
│   │               ├── base.py             # Абстрактный провайдер
│   │               ├── groq_provider.py    # Groq
│   │               ├── deepseek_provider.py # DeepSeek
│   │               └── openai_provider.py  # OpenAI
│   └── infra/
│       ├── db/
│       │   ├── models.py              # SQLAlchemy ORM модели
│       │   ├── session.py             # Фабрика AsyncSession
│       │   └── repositories/         # Репозитории (assets, faq_ai, users...)
│       ├── notifications/
│       │   ├── channels.py            # Абстракция канала уведомлений
│       │   └── telegram_channel.py    # Telegram-реализация
│       ├── queue/
│       │   ├── celery_app.py          # Celery application
│       │   └── tasks.py               # Celery tasks
│       └── storage/
│           └── s3.py                  # MinIO/S3 клиент
├── migrations/
│   └── versions/                      # Alembic миграции
├── data/
│   └── ai/
│       ├── core_policy.json           # Политика поведения AI
│       ├── intent_tags.json           # Теги намерений
│       ├── faq_seed.jsonl             # Начальные FAQ
│       ├── golden_cases.jsonl         # Тест-кейсы для smoke-теста
│       └── prompts/
│           ├── system_prompt.md       # Системный промпт LLM
│           ├── style_guide.md         # Гайд по стилю ответов
│           └── clarify_questions.json # Уточняющие вопросы
├── scripts/
│   ├── seed_faq.py                    # Загрузка начальных FAQ в БД
│   ├── smoke_ai.py                    # Smoke-тест AI-конвейера (golden cases)
│   ├── smoke_provider_router.py       # Smoke роутера LLM-провайдеров
│   └── rebuild_faq_embeddings.py       # Пересборка эмбеддингов FAQ
├── tests/
│   ├── conftest.py                    # Фикстуры (async_session, миграции)
│   ├── test_access_service.py         # AccessService
│   ├── test_ai_facade.py              # AIFacade (делегирование)
│   ├── test_ai_policy_routes.py       # AI-маршрутизация, RAG, провайдеры
│   ├── test_assets_repository.py     # ТМЦ, выдача/возврат
│   ├── test_case_classifier.py       # CaseClassifier
│   ├── test_case_memory_integration.py
│   ├── test_config.py                 # get_settings
│   ├── test_faq_semantic_search.py    # FAQ, semantic/hybrid
│   ├── test_ingest_repository.py     # Ingest batch idempotent
│   ├── test_intent_engine_catalog.py
│   ├── test_last_mile_marts.py        # Витрины raw_orders, mart_*
│   ├── test_menu_renderer_entrypoints.py # Меню по ролям, админ-клавиатура
│   ├── test_notification_delivery.py
│   ├── test_risk_smoke.py             # Risk pipeline smoke
│   ├── test_semantic_retrieval_smoke.py
│   ├── test_shift_log.py              # ShiftLogRepository
│   ├── test_user_smoke.py             # UserRepository, coerce_user_role
│   ├── test_verification_notify.py    # Тексты уведомлений верификации
│   └── test_verification_service.py   # VerificationService
├── .taskmaster/
│   └── tasks/
│       └── tasks.json                 # Задачи проекта (Task Master)
├── Dockerfile
├── docker-compose.yml
├── pyproject.toml
├── Makefile
└── .env.example
```

---

## База данных и миграции

Используется PostgreSQL + SQLAlchemy 2 (async) + Alembic.

### Основные таблицы

| Таблица | Описание |
|---|---|
| `users` | Пользователи бота, роли, darkstore |
| `assets` | Активы (ТМЦ) |
| `shift_log` | Записи журнала смены |
| `notifications` | Очередь и история уведомлений |
| `ingest_records` | Загруженные CSV/API данные |
| `faq_ai` | FAQ-база для AI-куратора |

### Команды

```bash
# Применить все миграции
make migrate

# Создать новую миграцию
python -m alembic revision --autogenerate -m "описание"

# Откатить одну миграцию
python -m alembic downgrade -1
```

---

## AI-куратор

AI-куратор — многоуровневая система ответов на вопросы курьеров, построенная на принципе RAG (Retrieval-Augmented Generation).

### Как работает

```
Вопрос пользователя
       │
       ▼
1. Rule-based (ключевые слова / must-match из core_policy.json)
       │ нет совпадения
       ▼
2. FAQ-поиск (PostgreSQL ILIKE по таблице faq_ai)
       │ нет совпадения или низкий score
       ▼
3. LLM-генерация (Groq → DeepSeek → OpenAI, по приоритету)
       │ нет ключей / ошибка
       ▼
4. Эскалация куратору или fallback-ответ
```

Бот **всегда отвечает** — даже при недоступности LLM или БД.

### Структура ответа

Каждый ответ содержит четыре блока:
1. **Суть ситуации** — краткое резюме
2. **Кто отвечает** — зона ответственности
3. **Почему** — обоснование из регламента
4. **Что делать сейчас** — конкретные шаги

### Включение

В `.env` установить:
```env
AI_ENABLED=true
GROQ_API_KEY=ваш_ключ   # достаточно одного провайдера
```

Перезапустить бота: `docker compose restart bot`

### Управление

Команды доступны только администраторам (`ADMIN_IDS`):

| Команда | Описание |
|---|---|
| `/ai` | Включить AI-режим для себя |
| `/ai_off` | Выключить AI-режим |
| `/ai_status` | Статус: БД, FAQ count, активные провайдеры |
| `/ai_add_faq` | Добавить FAQ пошагово (FSM-диалог) |
| `/ai_search_faq <текст>` | Найти FAQ по тексту (топ-5) |
| `/ai_policy_reload` | Перезагрузить `core_policy.json` без рестарта |

---

## Команды бота

### Пользовательские

| Команда | Описание |
|---|---|
| `/start` | Приветствие и главное меню |
| `/ai` | Включить режим AI-куратора |
| `/ai_off` | Выключить режим AI-куратора |

### Администраторские (`ADMIN_IDS`)

| Команда | Описание |
|---|---|
| `/admin` | Главное меню администратора |
| `/ai_status` | Статус AI-системы |
| `/ai_add_faq` | Добавить запись FAQ (пошаговый диалог) |
| `/ai_search_faq <текст>` | Поиск по FAQ |
| `/ai_policy_reload` | Перезагрузить политику AI |

---

## Роли и админ-панель

**Вход в админку:** команда `/admin` в боте. Доступ: роль ADMIN, LEAD или CURATOR либо Telegram ID в списке `ADMIN_IDS`.

**Пункты админ-меню:** ТМЦ (выдача), Журнал смены (инциденты), Импорт CSV, Настройки, Мониторинг. Разделы: Верификация (одобрение/отклонение заявок), AI-куратор, FAQ/база знаний, Анализ CSV, Рассылка.

**Роли:** ADMIN — полный доступ и управление AI; LEAD — смены и инциденты своего darkstore; CURATOR — ТМЦ, инциденты, дашборды; VIEWER — только чтение; COURIER — базовое взаимодействие и AI-куратор.

---

## Тесты

**Маркеры** (в `pyproject.toml`): `smoke` — быстрые проверки «система жива»; `integration` — тесты с БД без внешних API; `external` — реальные LLM/API (не входят в дефолтный прогон).

**Покрытие:** доступ (AccessService), верификация (VerificationService, уведомления), пользователи и роли (UserRepository, coerce_user_role), активы/ТМЦ (AssetsRepository), журнал смены (ShiftLogRepository), ingest (IngestRepository), уведомления (notification delivery), AI (AICourierService, policy routes, RAG, case classifier, intent engine, FAQ/semantic search, AIFacade, ProviderRouter), меню и клавиатуры (menu_renderer, admin keyboard), риск (risk smoke), конфиг (get_settings), витрины аналитики (raw_orders, mart_*).

```bash
# Дефолтный suite (без внешних зависимостей)
pytest -q -m "not external"

# Только smoke
pytest -q -m smoke

# Только integration
pytest -q -m integration

# Все тесты
pytest tests/ -v

# Smoke AI по golden cases
python scripts/smoke_ai.py
python scripts/smoke_provider_router.py
```

Тесты используют `DATABASE_URL` из окружения (и при необходимости `TEST_DATABASE_URL`). При недоступности LLM-ключей AI переходит на FAQ/fallback — тесты не падают.

---

## Полезные команды

```bash
# Поднять весь стек
make up

# Остановить
make down

# Остановить и удалить данные
docker compose down -v

# Применить миграции
make migrate

# Логи бота (realtime)
docker compose logs -f bot

# Логи воркера Celery
docker compose logs -f worker

# Войти в контейнер бота
docker compose exec bot bash

# Посмотреть очередь Celery
docker compose exec worker celery -A src.infra.queue.celery_app inspect active

# Пересобрать и перезапустить только бота
docker compose up bot --build
```

---

## Развёртывание

**Сервисы (docker-compose):** postgres (БД), redis (брокер Celery), minio (S3), bot (aiogram), worker (Celery). Postgres и Redis без публичных портов.

**Обновление:** `git pull` → `docker compose build` → `make migrate` → `docker compose up -d`. Проверить логи и health.

**Резервное копирование:** ежедневный дамп PostgreSQL (pg_dump), версионирование бакета S3 при необходимости.

**Откат:** восстановить БД из бэка, развернуть предыдущий образ и перезапустить контейнеры.

---

## Health / Ops чеклист

Перед релизом и при проверке окружения:

1. **Сервисы:** `docker compose ps` — bot, postgres, redis (и при необходимости worker, minio) в Up.
2. **Миграции:** `make migrate` без ошибок; откат: `alembic downgrade -1`.
3. **Тесты:** `pytest -q -m "not external"` — зелёный.
4. **Бот:** ответ на `/start` в Telegram; для админа — вход в админ-меню (`/admin`).
5. **AI:** при включённом AI — ответ в AI-кураторе; при выключенном — заглушка без падения.
6. **Верификация:** регистрация → pending; уведомление админам; одобрение/отклонение обновляет статус и уведомляет пользователя.
7. **Очередь:** воркеры подняты, при ошибках — логи и retry.
8. **Логи:** LOG_LEVEL=INFO или WARNING; при сбоях — stack trace и контекст.

---

## Устранение неполадок

| Проблема | Действие |
|----------|----------|
| Бот не отвечает | `docker compose ps`, `docker compose logs -f bot`. Проверить BOT_TOKEN, доступность postgres/redis из контейнера. |
| Нет доступа в админку | В `.env` задать `ADMIN_IDS=123456789,987654321` (Telegram user id через запятую или JSON-массив). |
| Миграция не применяется | Проверить DATABASE_URL (postgresql+asyncpg://...). Поднять postgres: `docker compose up -d postgres`, затем `make migrate`. |
| Ошибка enum `user_role` | В БД enum в lowercase (admin, lead, curator, courier). Проверить миграции и что роль не записывается в uppercase. |
| Текущая ревизия Alembic | `docker compose run --rm bot alembic current`. Проверить DATABASE_URL и таблицу alembic_version. |
| TelegramNetworkError / api.telegram.org | Доступность api.telegram.org, исходящий интернет, правильность BOT_TOKEN. Если был webhook — перезапустить бота (webhook сбросится). |
| AI не активен (/ai_status) | `AI_ENABLED=true` и хотя бы один ключ: GROQ_API_KEY, DEEPSEEK_API_KEY или OPENAI_API_KEY. |
| Политика AI не подхватывается | `/ai_policy_reload` (админ). Файлы: `data/ai/core_policy.json`, `intent_tags.json`, `prompts/`. |
| FAQ не находит / устаревшие эмбеддинги | `python scripts/rebuild_faq_embeddings.py` (нужны БД и миграции). |
| Лимиты Telegram (429) | Учитывать retry_after, снизить частоту, дедупликация, отправка через очередь. |
| Ошибки ingest (CSV) | Сверить колонки с Data Dictionary, проверить часовой пояс, повторить загрузку. |

---

## Граница Python vs n8n

**Python-ядро (бот + backend)** — источник правды: пользователи, верификация, доступ, AI-ответы. Регистрация и верификация (заявки, статусы, уведомления) — в боте и БД. Доступ (ADMIN_IDS, роли) проверяется только в коде. AI-куратор — через `AIFacade` и `src/core/services/ai/`.

**n8n** — опциональная оркестрация: дашборды, нотификации в сторонние каналы. Не принимает решений по одобрению/отклонению пользователей; при отказе n8n бот и верификация работают, уведомления админам идут через проактивный слой (EventBus).

---

## Интеграция с n8n

n8n используется как **оркестратор вокруг бэкенда**, а не вместо него: для уведомлений администраторам, ночных отчётов, экспортов. Источник правды по пользователям и заявкам — Python + Postgres.

**Локальный запуск n8n:** `infra/n8n/docker-compose.yml`, пример переменных `infra/n8n/.env.n8n.example`:

```bash
cd infra/n8n
cp .env.n8n.example .env.n8n
# отредактируй N8N_ENCRYPTION_KEY, WEBHOOK_URL и креды
docker compose up -d
```

После этого можно включить фичу зеркалирования заявок из бота через переменные:

```env
N8N_VERIFICATION_MIRROR_ENABLED=true
N8N_VERIFICATION_WEBHOOK_URL=https://your-n8n-host/webhook/verification-pending
```

n8n остаётся **необязательной** интеграцией: при его недоступности логика верификации и работы бота не ломается.

---

## Роли и доступы

| Роль | Описание |
|---|---|
| `ADMIN` | Полный доступ, управление пользователями и AI |
| `LEAD` | Управление сменами и инцидентами своего darkstore |
| `CURATOR` | Работа с FAQ, просмотр журналов |
| `VIEWER` | Только чтение отчётов |
| `COURIER` | Базовое взаимодействие, AI-куратор |

---

## Задачи и команды (Task Master)

Задачи проекта хранятся в **`.taskmaster/tasks/tasks.json`**. В Cursor доступны команды для работы с задачами (префикс `/taskmaster:`):

| Действие | Команда |
|----------|---------|
| Список задач | `/taskmaster:list-tasks` [фильтр: pending, in-progress, done и т.д.] |
| Следующая задача | `/taskmaster:next-task` |
| Показать задачу | `/taskmaster:show-task` \<id\> |
| Добавить задачу | `/taskmaster:add-task` |
| Обновить задачу | `/taskmaster:update-task` |
| Сменить статус | `/taskmaster:to-pending`, `/taskmaster:to-in-progress`, `/taskmaster:to-done` и др. |
| Подзадачи | `/taskmaster:add-subtask`, `/taskmaster:expand-task` |
| Зависимости | `/taskmaster:add-dependency`, `/taskmaster:validate-dependencies` |
| Справка | `/taskmaster:help` |

Полный перечень и описание — в этом README; дублирующая документация в других файлах не ведётся.
