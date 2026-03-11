# Словарь данных

## MVP: справочники и пользователи
- **territories**: id, name, created_at.
- **teams**: id, territory_id, name, created_at.
- **darkstores**: id, team_id, code, name, is_white, created_at.
- **users**: id, tg_user_id (UNIQUE), role (enum), display_name, created_at, updated_at.
- **user_scopes**: id, user_id, team_id (nullable), darkstore_id (nullable), UNIQUE(user_id, team_id, darkstore_id).
- **couriers**: id, darkstore_id, external_key, name, created_at.
- **chat_bindings**: id, team_id, chat_id, category (alerts/daily/assets/incidents/general), topic_id (nullable), created_at.

## MVP: ТМЦ и журнал смены
- **assets**: id, darkstore_id, asset_type, serial, status, condition, created_at, updated_at; UNIQUE(darkstore_id, asset_type, serial).
- **asset_assignments**: id, asset_id, courier_id, assigned_at, returned_at (nullable); один активный на asset (partial unique по returned_at IS NULL).
- **asset_events**: id, asset_id, assignment_id (nullable), event_type, payload (jsonb), created_at.
- **shift_log**: id, darkstore_id, log_type, severity, title, details, created_at, created_by (nullable); индексы по darkstore_id, created_at.

## MVP: уведомления
- **notifications**: id, type, status, dedupe_key (nullable UNIQUE), payload (jsonb), created_at.
- **notification_targets**: id, notification_id, channel, chat_id, topic_id (nullable), created_at.
- **notification_delivery_attempts**: id, notification_id, attempted_at, status, error_code, retry_after (nullable), created_at.

## Ingest batches (пакеты загрузки)
- `source`: csv_upload | superset_api | db_direct
- `content_hash`: SHA256 файла/пакета
- `rules_version`: версия бизнес-правил, использованная при расчёте

## delivery_orders_raw (ключевые колонки)
- batch_id (FK ingest_batches)
- order_key, ds_code
- zone_code (nullable) — при отсутствии или низком покрытии возможен режим Store-only
- start_delivery_at, deadline_at, finish_at_raw (timestamptz)
- durations (jsonb): wait, assembly, delivery, total (минуты)
- raw (jsonb) — исходная строка/объект
- created_at

## delivery_orders_calc (производные поля)
- finish_at_effective
- remaining_pct
- timer_sign (pos/neg/unknown)
- Флаги ignore (<40% оставшегося времени или отрицательный таймер)
- is_violation_good_remaining (>50% и pos_timer и опоздание)
- hard-save (<20% и успех)
- save+ (20–40 и успех)
- assembly_share, is_assembly_blocker
- trip_id, trip_pool, L_pickup, is_dobor, is_negative_dobor

## Ограничение по зонам (Zone gating)
- `zone_coverage` считается по батчу/дню.
- Если ниже порога → отчётность только в режиме Store-only.

## FAQ (AI Curator, v2)
- **faq_ai**: id, question, answer, category (nullable), tag (nullable), keywords (jsonb), embedding (text, nullable), is_active (bool), created_at, updated_at. Репозиторий — `src/infra/db/repositories/faq_repo.py`. Эмбеддинги пересобираются скриптом `scripts/rebuild_faq_embeddings.py`.
