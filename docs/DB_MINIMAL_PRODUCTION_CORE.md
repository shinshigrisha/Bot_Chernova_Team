# Минимальный production core — таблицы БД

Канонический список таблиц для минимального production-ядра. Остальные таблицы (territories, teams, darkstores, delivery_orders_raw, marts, ai_delivery и т.д.) считаются расширениями и могут быть отключены или развёрнуты отдельно.

## Список таблиц и статус

| Таблица | Статус | Примечание |
|--------|--------|------------|
| **users** | ✅ Есть | MVP 001, модель `User` |
| **verification_applications** | ✅ Есть | 008, модель `VerificationApplication` |
| **audit_logs** | ✅ Миграция 016 | Лог действий: actor, action, entity_type, entity_id, payload |
| **faq_ai** | ✅ Есть | 002–006, модель `FAQItem`; колонки embedding/embedding_vector |
| **faq_embeddings** | ✅ В faq_ai | Отдельной таблицы нет; эмбеддинги в `faq_ai.embedding` и `faq_ai.embedding_vector` |
| **ai_requests_log** | ✅ Миграция 016 | Лог запросов к AI: user, mode, latency, tokens, status |
| **ingest_batches** | ✅ Есть | MVP 001, модель `IngestBatch` |
| **uploaded_files** | ✅ Миграция 016 | Метаданные загруженных файлов, связь с batch/user |
| **analysis_jobs** | ✅ Миграция 016 | Задачи анализа (CSV, отчёты), статус, result/error |
| **notifications** | ✅ Есть | MVP 001, модель `Notification` |
| **notification_delivery_attempts** | ✅ Есть | MVP 001, модель `NotificationDeliveryAttempt` |
| **groups** | ✅ Миграция 016 | Telegram-группы (tg_chat_id, title) |
| **group_members** | ✅ Миграция 016 | Участники групп, связь user/group |
| **polls** | ✅ Миграция 016 | Опросы: вопрос, группа, создатель, closed_at |
| **poll_answers** | ✅ Миграция 016 | Ответы пользователей на опросы |
| **poll_schedules** | ✅ Миграция 016 | Расписание отправки/повтора опросов |
| **poll_slots** | ✅ Миграция 016 | Варианты ответов опроса (option_text, is_correct) |

## Зависимости

- **audit_logs**: опционально `users.id`.
- **ai_requests_log**: опционально `users.id`, tg_user_id.
- **uploaded_files**: опционально `ingest_batches.id`, `users.id`.
- **analysis_jobs**: опционально `uploaded_files.id`, `ingest_batches.id`, `users.id`.
- **group_members**: `groups.id`, опционально `users.id` или tg_user_id.
- **polls**: опционально `groups.id`, `users.id`.
- **poll_answers**: `polls.id`, опционально `users.id` или tg_user_id.
- **poll_schedules**: `polls.id`.
- **poll_slots**: `polls.id`.

## Миграции

- Таблицы из MVP/002–008 уже созданы существующими миграциями.
- Недостающие таблицы вводятся одной миграцией: **016_minimal_production_core_tables**.

## Использование

При развёртывании «минимального ядра» достаточно накатить миграции до 016 включительно. Остальные миграции (010_raw_orders, 011_mart_*, 012_mart_*, 013–015 ai_delivery) можно не применять, если не используются заказы и аналитика доставки.
