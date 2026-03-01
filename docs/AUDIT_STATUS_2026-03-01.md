# Аудит статуса реализации (2026-03-01)

## Методика
- Сверка требований из `docs/*` и `.cursor/plans/*` с фактическим кодом.
- Проверка модулей `src/bot`, `src/core`, `src/infra`, `migrations`, `tests`, инфраструктурных конфигов.
- Фиксация статуса по шкале: `Реализовано` / `Частично` / `Не реализовано`.

## 1) Сверка требований и факта

| Область | Требование | Факт в коде | Статус |
|---|---|---|---|
| Bot/handlers | Тонкий слой handlers, без долгих операций | В `src/bot/*` долгие операции вынесены в сервисы/очередь | Реализовано |
| RBAC | `/admin` доступ по role или `ADMIN_IDS` | Проверка есть в `src/bot/admin/menu.py` | Реализовано |
| ТМЦ FSM | Выдача ТМЦ с подтверждением и записью в БД | Поток реализован в `src/bot/admin/tmc_issue.py` + `AssetsService` | Реализовано |
| Инциденты FSM | Создание записи в shift_log | Реализовано в `src/bot/admin/incident.py` + `ShiftLogService` | Реализовано |
| Ingest idempotency | `UNIQUE(source, content_hash)`, дубликаты не создаются | Есть в модели/миграции + `IngestService.accept_csv_upload` | Реализовано |
| Ingest parse | Парсинг CSV -> `delivery_orders_raw` | `parse_ingest_batch_task` пока заглушка, данных не пишет | Не реализовано |
| Notifications queue | Отправка через Celery + attempts | `deliver_notification_task` + `notification_delivery_attempts` | Частично |
| Retry 429 | Учёт `retry_after` | В worker есть обработка `429` и retry | Реализовано |
| Дедуп уведомлений | `dedupe_key` unique | Ограничение в БД есть, но обработка конфликтов в сервисе отсутствует | Частично |
| Scheduler | Отдельный scheduler/блокировка дублей | Scheduler не включен, логики блокировок нет | Не реализовано |
| Integrations | `infra/integrations` (Superset API/DB) | Только каркас пакета | Не реализовано |
| Analytics calc/snapshots/alerts pipeline | Этапы raw -> calc -> snapshots | Реализована только raw-часть и база под уведомления | Частично |
| Security secrets | Не хранить секреты в репо | Были реальные ключи в `.env.example` и `.cursor/mcp.json`, исправлено | Частично |

## 2) Детализация по модулям

### `src/bot`
- `main.py`: запуск polling, подключение router'ов — `Реализовано`.
- `handlers/start.py`: регистрация/обновление пользователя, роль по `ADMIN_IDS` — `Реализовано`.
- `admin/menu.py`: меню и доступы, но пункты «Настройки/Мониторинг» как заглушка — `Частично`.
- `admin/tmc_issue.py`: FSM выдачи ТМЦ с confirm и записью в сервис — `Реализовано`.
- `admin/incident.py`: FSM инцидента с записью в журнал — `Реализовано`.
- `admin/ingest.py`: приём CSV, передача в сервис ingest — `Реализовано`.

### `src/core/services`
- `assets.py`: выдача/возврат ТМЦ, event log — `Реализовано`.
- `shift_log.py`: запись инцидента — `Реализовано`.
- `notifications.py`: enqueue уведомлений через Celery — `Реализовано`.
- `ingest.py`: хеш, дедуп, создание batch, upload в S3, enqueue parse — `Частично` (парсинг фактически отсутствует в worker).

### `src/infra/db`
- `models.py`, `enums.py`, миграция `001_initial_mvp.py` соответствуют MVP-схеме — `Реализовано`.
- Репозитории покрывают базовые CRUD-сценарии — `Реализовано`.

### `src/infra/queue` и `src/infra/notifications`
- `deliver_notification_task`: есть попытки/429/retry/status update — `Частично` (нет явной логики итогового `PARTIAL/FAILED` по mixed результатам).
- `parse_ingest_batch_task`: только смена статуса batch, без реального parsing — `Не реализовано`.
- `telegram_channel.py`: отправка в Bot API и разбор `429` — `Реализовано`.

### `src/infra/storage`
- `s3.py`: put/get объектов в MinIO/S3 — `Реализовано`.

### `src/infra/integrations`
- Только `__init__.py` — `Не реализовано`.

### `tests`
- Есть минимальные тесты для репозиториев/attempts — `Реализовано`.
- Нет e2e-тестов и тестов FSM/worker интеграции — `Частично`.

## 3) Критичные пробелы (приоритет P0/P1)

1. **P0**: Нет реального ingest parser (`parse_ingest_batch_task` заглушка).
2. **P0**: Секреты были в репозитории (исправлено в текущем проходе, но нужна ротация ключей).
3. **P1**: Неполная итоговая стратегия статусов уведомлений (`DELIVERED/PARTIAL/FAILED`).
4. **P1**: `infra/integrations` не реализован.
5. **P1**: Отсутствует scheduler с защитой от дублей.
6. **P1**: `Настройки` и `Мониторинг` в админ-меню пока заглушки.

## 4) Что уже исправлено в этом цикле
- Удалён API-ключ Context7 из `.cursor/mcp.json`, перевод на env (`CONTEXT7_API_KEY`).
- Добавлен fallback-чеклист в `.cursorrules` при недоступности MCP.
- Удалены реальные секреты из `.env.example` (заменены плейсхолдерами).
- Исправлен `readme` путь в `pyproject.toml` на `docs/README.md`.

## 5) Рекомендации следующего шага
- Реализовать parse в `parse_ingest_batch_task` (CSV -> `delivery_orders_raw` + `FAILED` с причинами при ошибках).
- Добавить в worker агрегирование результатов по target и корректную финализацию статуса notification.
- Ввести хотя бы базовый scheduler-lock (одиночный инстанс или redis-lock).
- Доработать тесты до интеграционных сценариев bot -> service -> queue -> db.
