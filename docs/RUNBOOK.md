# Runbook: Health и устранение неполадок

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
| FAQ не находит / устаревшие эмбеддинги | `python scripts/rebuild_faq_embeddings.py` или `python scripts/rebuild_embeddings.py` (нужны БД и миграции). |
| Лимиты Telegram (429) | Учитывать retry_after, снизить частоту, дедупликация, отправка через очередь. |
| Ошибки ingest (CSV) | Сверить колонки с Data Dictionary, проверить часовой пояс, повторить загрузку. |

Подробнее — разделы «Health / Ops чеклист» и «Устранение неполадок» в корневом [README.md](../README.md).
