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

См. также:
- docs/DEPLOYMENT.md
- docs/ADMIN_GUIDE.md

Дата: 2026-03-01
