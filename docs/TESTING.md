# Тестирование

Маркеры (в `pyproject.toml`): **smoke** — быстрые проверки «система жива» (меню, эмбеддинги, риск, AI policy routes); **integration** — тесты с БД без внешних API; **external** — реальные LLM/API (по умолчанию **не запускаются**: `addopts = "-m 'not external'"`). Дефолтный прогон не зависит от сети, реальных LLM и локальных настроек.

## Команды (quality gates)

```bash
# Сборка: проверка синтаксиса
python -m compileall src

# Дефолтный suite (то же, что pytest по умолчанию: без external)
pytest -q
pytest -q
pytest -q
```

Рекомендуется прогонять все три перед коммитом/релизом.

## Дополнительные команды

```bash
# Только smoke
pytest -q -m smoke

# Только integration
pytest -q -m integration

# Все тесты (дефолтный addopts исключает external; для external снять addopts или запустить с -m external)
pytest tests/ -v

# Smoke AI по golden cases (вне pytest, опционально)
python scripts/smoke_ai.py
python scripts/smoke_provider_router.py
```

Тесты используют `DATABASE_URL` из окружения (при необходимости `TEST_DATABASE_URL`). При недоступности LLM-ключей AI переходит на FAQ/fallback — тесты не падают.

## Покрытие

Доступ (AccessService), верификация (VerificationService, уведомления), пользователи и роли, активы/ТМЦ, журнал смены, ingest, уведомления, AI (AICourierService, policy routes, RAG, case classifier, intent engine, FAQ/semantic search, AIFacade, ProviderRouter), меню и клавиатуры, риск (smoke), конфиг, витрины аналитики.

Подробнее — раздел «Тесты» в корневом [README.md](../README.md).
