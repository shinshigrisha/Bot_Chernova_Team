# Канонические слои проекта

Референсная структура каталогов. Все новые модули размещаются в соответствии с этим деревом. См. также [ARCHITECTURE.md](ARCHITECTURE.md) и [.cursor/rules/01_architecture.md](../.cursor/rules/01_architecture.md).

## Дерево канонических слоёв

```
src/
  bot/
    handlers/
    admin/
    keyboards/
    middlewares/
    navigation.py
    menu_renderer.py

  core/
    domain/
    services/
      access_service.py
      users.py
      verification_service.py
      notifications.py
      ingest.py
      assets.py
      shift_log.py
      ai/
        ai_facade.py
        ai_courier_service.py
        intent_engine.py
        intent_ml_engine.py
        semantic_search.py
        rag_service.py
        analytics_assistant.py
        provider_router.py
        providers/
      risk/
        proactive_assistant.py
        risk_engine.py
        recommendation_engine.py

  infra/
    db/
      models.py
      enums.py
      session.py
      repositories/
    queue/
    notifications/
    storage/
    integrations/

  data/
    ai/
      faq_seed.jsonl
      intents_catalog.json
      ml_cases.jsonl
      datasets/
      prompts/

  scripts/
  migrations/
  tests/
```

Примечание: каталог `data/` в репозитории лежит в корне проекта (рядом с `src/`), а не внутри `src/`. `scripts/`, `migrations/`, `tests/` — также в корне.

## Назначение слоёв

| Слой | Назначение |
|------|------------|
| **bot/** | Telegram-адаптер: роутинг, хендлеры, админка, клавиатуры, middlewares, навигация и рендер меню. Без бизнес-логики. |
| **core/domain/** | Доменные сущности, value objects, исключения. |
| **core/services/** | Прикладные и доменные сервисы: доступ, пользователи, верификация, уведомления, ingest, активы, смены. |
| **core/services/ai/** | **AIFacade** — единственная точка входа в AI. Три режима: Courier assistant (answer_user, proactive_hint), Admin copilot (answer_admin), Analytics assistant (analyze_csv). Внутри: AICourierService, RAG, интенты, AnalyticsAssistant, роутер провайдеров. Вызовы LLM извне — только через фасад. См. docs/AI_MODES.md. |
| **core/services/risk/** | Риск-движок, проактивный ассистент, рекомендации. |
| **infra/db/** | Модели, enum'ы, сессия, репозитории. |
| **infra/queue/** | Celery/очереди, задачи. |
| **infra/notifications/** | Каналы доставки (Telegram и др.). |
| **infra/storage/** | S3/MinIO, объектное хранилище. |
| **infra/integrations/** | Внешние API (Superset, n8n и т.д.). |
| **data/ai/** | Данные для AI: FAQ, интенты, ML-кейсы, датасеты, промпты. |

## Соответствие текущему репозиторию

- **bot/**: есть `handlers/`, `admin/`, `keyboards/`, `middlewares/`, `navigation.py`, `menu_renderer.py`. Дополнительно: `states.py`, `states_verification.py`, `main.py`.
- **core/domain/**: есть `exceptions.py`; при необходимости расширять сущностями.
- **core/services/**: перечисленные файлы присутствуют; дополнительно есть `darkstores.py`. В **ai/** также: `intent_ml_classifier.py`, `case_engine.py`, `case_classifier.py`, `embedding_service.py`, `embeddings_service.py`, `providers/` (base, groq, deepseek, openai).
- **core/services/risk/**: есть `proactive_assistant.py`, `risk_engine.py`, `recommendation_engine.py`; дополнительно: `rules.py`, `features.py`, `smoke_risk_engine.py`.
- **infra/**: структура совпадает; под интеграциями есть `n8n/` (verification_mirror). Репозитории: users, verification_applications, faq_repo, notifications, ingest, assets, shift_log, darkstores.
- **data/ai/**: есть `faq_seed.jsonl`, `intents_catalog.json`, `ml_cases.jsonl`, `datasets/`, `prompts/`; плюс `intent_tags.json`, `core_policy.json`, `golden_cases.jsonl` и др.
- В корне **src/** дополнительно: `config.py`, `api/` (automation) — считаются допустимыми верхнеуровневыми модулями.

Новые модули размещать по этой схеме; дублирование слоёв или создание параллельных деревьев не допускается.
