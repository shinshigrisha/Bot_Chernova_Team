# Развёртывание

## Локальный запуск (MVP)

1. Скопировать `.env.example` в `.env`, задать `BOT_TOKEN` и при необходимости `ADMIN_IDS`.
2. Поднять стек: `make up` или `docker compose up -d`.
3. Применить миграции: `make migrate` (или `docker compose run --rm bot alembic upgrade head`).
4. Запустить бота: `make bot` или `docker compose up bot`.
5. Запустить воркер: `make worker` или `docker compose up worker`.

Проверка: в Telegram отправить боту `/start` и `/admin`; логи — `docker compose logs -f bot`.

**Важно:** если бот раньше работал по webhook, при старте он сбрасывает webhook (чтобы long polling получал обновления). Если бот не отвечает на команды — убедитесь, что миграции применены (`make migrate`) и в логах есть строка `Webhook cleared for polling`.

**Тесты:** требуют запущенный Postgres с применёнными миграциями. После `make up` и `make migrate`: `pytest tests/ -v` (используется `DATABASE_URL` из окружения).

**AI:** политика и промпты — каталог `data/ai/` (core_policy.json, intent_tags.json, prompts/). Опционально после миграций: пересборка эмбеддингов FAQ — `python scripts/rebuild_faq_embeddings.py`; проверка без Telegram — `python scripts/smoke_ai.py`, `python scripts/smoke_provider_router.py`.

## Службы (docker-compose)
- **postgres** (postgres:16-alpine): БД, без публичных портов (только внутренняя сеть).
- **redis** (redis:7-alpine): брокер/бэкенд Celery, без публичных портов.
- **minio**: S3-совместимое хранилище, порты 9000 (API) и 9001 (консоль) для отладки.
- **bot**: aiogram, команда `python -m src.bot.main`.
- **worker**: Celery worker, команда `celery -A src.infra.queue.celery_app worker --loglevel=info`.
- **scheduler**: опционально, отдельный процесс.

## Переменные окружения
Обязательные (см. `.env.example`):
- `BOT_TOKEN` — токен Telegram-бота.
- `ADMIN_IDS` — список ID через запятую для доступа в админку.
- `DATABASE_URL` — `postgresql+asyncpg://user:pass@postgres:5432/delivery_assistant`.
- `REDIS_URL` — `redis://redis:6379/0`.
- `CELERY_BROKER_URL` — `redis://redis:6379/1`.
- `S3_ENDPOINT`, `S3_ACCESS_KEY`, `S3_SECRET_KEY`, `S3_BUCKET` — для MinIO.

Опционально: `TIMEZONE`, `LOG_LEVEL`.

## Миграции
- При развёртывании выполнять: `make migrate` или `docker compose run --rm bot alembic upgrade head`.
- Перед миграциями — резервная копия БД.
- Откат миграции: `alembic downgrade -1` (по необходимости).

## Резервное копирование
- Ежедневный дамп PostgreSQL (pg_dump).
- Версионирование бакета S3/MinIO для ingest-файлов.

## Обновление
1. Получить код (git pull).
2. Собрать образы: `docker compose build`.
3. Выполнить миграции: `make migrate`.
4. Перезапустить службы: `docker compose up -d`.
5. Проверить логи и health.

## Откат
- Восстановить БД из резервной копии.
- Развернуть предыдущий образ (тег) и перезапустить контейнеры.
