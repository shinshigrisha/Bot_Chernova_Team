# Аудит AI-архитектуры (исторический документ)

> **Исторический документ.** Отражает состояние до и после миграции 2026-03-11. Актуальная схема AI — в [ARCHITECTURE.md](ARCHITECTURE.md) (раздел «AI (куратор)»).

**Статус:** миграция выполнена (2026-03-11). Удалены: `src/services/ai/`, `src/core/services/ai_service.py`, мёртвая ветка base/router/плоские провайдеры в `core/services/ai/`, `src/ai_policy/`. Скрипт `scripts/smoke_provider_router.py` переведён на core.

---

## Текущий канон (кратко)

- **Код:** `src/core/services/ai/` — AICourierService, ProviderRouter, providers (base, openai, deepseek, groq), CaseEngine, IntentEngine, EmbeddingsService.
- **Политика и промпты:** `data/ai/` (core_policy.json, intent_tags.json, prompts/).
- **FAQ:** единственный репозиторий `src/infra/db/repositories/faq_repo.py`.
- **Точки входа:** bot/main.py, handlers/ai_chat.py, admin/ai_admin.py, middlewares/ai_inject.py, scripts/smoke_ai.py, scripts/smoke_provider_router.py — все используют core.
