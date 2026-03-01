# Delivery Assistant

В этом репозитории — система Delivery Assistant (Telegram-бот и бэкенд-сервисы) для управления операциями доставки:
- Смены и опросы
- ТМЦ (активы)
- Журнал смены и инциденты
- Загрузка данных из Superset (CSV/API/DB)
- Аналитика, алерты, ежедневная отчётность
- AI Curator (RAG)

## Быстрый старт (разработка)
1. Скопировать `.env.example` в `.env` и заполнить значения
2. `docker compose up -d --build`
3. Применить миграции: `make migrate`
4. Запустить бота локально (опционально): `make bot`

## Подъем через docker-compose (полный цикл)

1. Подготовить `.env`:
   - `BOT_TOKEN`
   - `DATABASE_URL` (по умолчанию подходит compose-сеть)
   - `REDIS_URL`, `CELERY_BROKER_URL`
   - для AI: `AI_ENABLED=true` и минимум один ключ:
     - `GROQ_API_KEY` и/или
     - `OPENAI_API_KEY` и/или
     - `DEEPSEEK_API_KEY` (+ `DEEPSEEK_BASE_URL`)

2. Поднять сервисы:
   - `docker compose up -d --build`

3. Применить миграции:
   - `python -m alembic upgrade head`

4. Проверить состояние AI:
   - в Telegram у админа выполнить `/ai_status`

5. (Опционально) заполнить FAQ:
   - `python scripts/seed_faq.py`
   - или через админ-команду `/ai_add_faq` (FSM-диалог)

6. Локальная smoke-проверка AI без Telegram:
   - `python scripts/smoke_ai.py`

7. Полезные команды:
   - логи бота: `docker compose logs -f bot`
   - логи воркера: `docker compose logs -f worker`
   - остановка: `docker compose down`
   - остановка с удалением данных: `docker compose down -v`

См. также:
- docs/DEPLOYMENT.md
- docs/ADMIN_GUIDE.md

Дата: 2026-03-01
