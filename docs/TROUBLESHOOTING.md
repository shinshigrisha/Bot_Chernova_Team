## Troubleshooting

### `ADMIN_IDS`

В `.env` используйте `ADMIN_IDS` как список Telegram user id:

```env
ADMIN_IDS=123456789,987654321
```

Поддерживаются:

- одна цифра
- строка через запятую
- JSON-массив

Если админ-команды `/admin`, `/status`, `/ai_status` отвечают `Нет доступа.`, сначала проверьте `ADMIN_IDS`.

### `user_role` enum

В PostgreSQL enum `user_role` хранит lowercase-значения:

- `admin`
- `lead`
- `curator`
- `courier`

Если видите ошибку вида `invalid input value for enum user_role`, проверьте:

- что в БД создан актуальный enum через Alembic
- что роль не записывается в uppercase

### `alembic current`

Проверка текущей миграции:

```bash
alembic current
```

В Docker:

```bash
docker compose run --rm bot alembic current
```

Если revision не читается, проверьте:

- `DATABASE_URL`
- применены ли миграции: `alembic upgrade head`
- существует ли таблица `alembic_version`

### `TelegramNetworkError` / `api.telegram.org` недоступен

Если бот не стартует или long polling падает:

- проверьте доступность `api.telegram.org`
- проверьте исходящий интернет с хоста/контейнера
- проверьте правильность `BOT_TOKEN`
- если раньше был webhook, перезапустите бот и убедитесь, что webhook сброшен

### `AI disabled` / `no providers`

Если `/status` или `/ai_status` показывают, что AI не активен:

- проверьте `AI_ENABLED=true`
- проверьте, что задан хотя бы один ключ:
  - `GROQ_API_KEY`
  - `DEEPSEEK_API_KEY`
  - `OPENAI_API_KEY`

Если `AI_ENABLED=true`, но providers count = 0, значит AI включён конфигом, но ключи провайдеров не заданы.
