# Delivery Assistant

Telegram-бот и бэкенд-система для управления операциями доставки: смены, активы (ТМЦ), инциденты, журнал смены, загрузка данных и AI-куратор для курьеров.

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
10. [Тесты](#тесты)
11. [Полезные команды](#полезные-команды)

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
│   ├── test_ai_policy_routes.py       # Тесты AI-маршрутизации
│   ├── test_assets_repository.py
│   ├── test_ingest_repository.py
│   ├── test_notification_delivery.py
│   └── test_user_smoke.py
├── docs/                              # Полная документация
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

## Тесты

```bash
# Запустить все тесты
pytest tests/ -v

# Только AI-логика (без Telegram, без ключей LLM)
pytest tests/test_ai_policy_routes.py -v

# Smoke-тест AI-конвейера (golden cases)
python scripts/smoke_ai.py
```

Тесты используют `DATABASE_URL` из окружения. При недоступности LLM-ключей AI-логика автоматически переходит на FAQ/fallback — тесты не падают.

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

## Роли и доступы

| Роль | Описание |
|---|---|
| `ADMIN` | Полный доступ, управление пользователями и AI |
| `LEAD` | Управление сменами и инцидентами своего darkstore |
| `CURATOR` | Работа с FAQ, просмотр журналов |
| `VIEWER` | Только чтение отчётов |
| `COURIER` | Базовое взаимодействие, AI-куратор |

---

## Документация

Полная документация в `docs/`:

| Файл | Описание |
|------|----------|
| `docs/DOCS.md` | Единый справочник (запуск, развёртывание, архитектура, данные, AI, runbook) |
| `docs/ARCHITECTURE.md` | Слои, сервисы, потоки данных, AI (куратор), RBAC |
| `docs/DEPLOYMENT.md` | Развёртывание и обновление |
| `docs/AI_CURATOR.md` | AI-куратор: реализация (`src/core/services/ai/`, `data/ai/`), провайдеры, FAQ, policy |
| `docs/ADMIN_GUIDE.md` | Роли и пункты админ-меню |
| `docs/TROUBLESHOOTING.md` | ADMIN_IDS, enum user_role, миграции, сеть, AI disabled |
| `docs/SECURITY.md` | Безопасность и секреты |
| `docs/RUNBOOK.md` | Типовые проблемы и диагностика |
| `docs/DATA_DICTIONARY.md` | Словарь данных |
| `docs/CLEANUP_AUDIT_REPORT.md` | Отчёт аудита cleanup (мусор, legacy, импорты, docs) |
