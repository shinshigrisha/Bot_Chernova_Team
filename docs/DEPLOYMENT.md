# Развёртывание

Сервисы (docker-compose): **postgres** (БД), **redis** (брокер Celery), **minio** (S3), **bot** (aiogram, `python -m src.bot.main`), **worker** (Celery, `celery -A src.infra.queue.celery_app`). Postgres и Redis без публичных портов при необходимости.

## Обновление

1. `git pull`
2. `docker compose build`
3. `make migrate`
4. `docker compose up -d`
5. Проверить логи и health (см. [RUNBOOK.md](RUNBOOK.md)).

## Резервное копирование

- Ежедневный дамп PostgreSQL (`pg_dump`).
- Версионирование бакета S3 при необходимости.

## Откат

Восстановить БД из бэка, развернуть предыдущий образ и перезапустить контейнеры.

Подробнее — раздел «Развёртывание» в корневом [README.md](../README.md).
