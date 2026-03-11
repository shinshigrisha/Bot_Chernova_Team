# Аудит AI-архитектуры (Task Master)

**Задача:** Audit current AI architecture — canonical modules, duplicate FAQ repos, duplicate provider routing, legacy entrypoints.  
**Правила:** без новой функциональности, без слепого рефакторинга; инспекция → карта → дубликаты → канон → план миграции.

---

## 1. Current AI map (текущая карта AI)

### 1.1 Деревья модулей

| Путь | Назначение | Используется |
|------|------------|--------------|
| **src/core/services/ai/** | Канонический стек AI-куратора | main.py, ai_admin, ai_chat, tests, scripts/smoke_ai |
| **src/core/services/ai/providers/** | Провайдеры (config-based, ProviderResponse) | ProviderRouter в core |
| **src/core/services/ai_service.py** | Legacy wrapper (FAQ + LLM, AIResponse) | **Никем не импортируется** |
| **src/services/ai/** | Legacy wrapper (policy + FAQ + chat, str) | Только scripts/smoke_provider_router.py |
| **src/infra/db/repositories/faq_repo.py** | Единственный репозиторий FAQ | Все слои (core AI, admin, scripts) |

### 1.2 Внутри `src/core/services/ai/`

| Модуль | Роль |
|--------|------|
| **provider_router.py** | Роутинг по провайдерам (config: `get_settings()`, порядок chat/reason), возвращает `ProviderResponse`. |
| **providers/base.py** | `BaseProvider`, `ProviderResponse` (text, provider, model, usage_tokens). |
| **providers/openai_provider.py**, **deepseek_provider.py**, **groq_provider.py** | Реализации провайдеров (enabled по config). |
| **ai_courier_service.py** | Основной сервис куратора: CaseEngine, IntentEngine, EmbeddingsService, FAQRepository, policy из `data/ai/`, возвращает `AICourierResult`. |
| **case_engine.py** | Rule-based кейсы (damaged_goods, contact_customer, …). |
| **intent_engine.py** | Детекция интента (FAQ + ключевые слова), использует `ProviderRouter` и `FAQRepository`. |
| **embeddings_service.py** | OpenAI embeddings для FAQ/скриптов. |

**Параллельная (мёртвая) ветка в том же каталоге:**

| Модуль | Роль | Кто импортирует |
|--------|------|-----------------|
| **base.py** | `BaseProvider`, `LLMResponse` (другая сигнатура ответа). | Только router.py и flat-провайдеры |
| **router.py** | Роутер с `LLMResponse`, порядок из списка провайдеров. | Никто |
| **openai_provider.py**, **deepseek_provider.py**, **groq_provider.py** (корень ai/) | Провайдеры на `base.LLMResponse`. | Никто |

### 1.3 Точки входа (entrypoints)

| Entrypoint | Источник AI |
|------------|-------------|
| **bot/main.py** | `ProviderRouter(providers[])`, `AICourierService(session_factory, router)`, `FAQRepository()` на dp. |
| **bot/handlers/ai_chat.py** | `ai_service` из middleware → `get_answer()` → ожидает `AICourierResult` (text, route, debug). |
| **bot/middlewares/ai_inject.py** | Пробрасывает `ai_service`, `faq_repo`, `ai_router`, `provider_router`. |
| **bot/admin/ai_admin.py** | `AICourierService` (core), `FAQRepository` для админ-команд. |
| **scripts/smoke_ai.py** | core `AICourierService` + core `ProviderRouter` + providers. |
| **scripts/smoke_provider_router.py** | **Только** `src.services.ai.provider_router.ProviderRouter` (legacy). |

### 1.4 FAQ

- **Один репозиторий:** `src/infra/db/repositories/faq_repo.py` (FAQRepository). Дубликатов репозитория FAQ нет.
- Используется: core ai_courier_service, intent_engine, ai_admin, main (на dp), legacy ai_service.py и legacy services/ai (но они не в production-пути).

---

## 2. Duplicates found (дубликаты)

### 2.1 Provider routing (два роутера + два набора провайдеров)

| Копия | Расположение | API | Конфиг |
|-------|--------------|-----|--------|
| **Канон** | `core/services/ai/provider_router.py` + `core/services/ai/providers/*` | `complete() -> ProviderResponse`, порядок из config (chat/reason) | get_settings() |
| **Legacy** | `src/services/ai/provider_router.py` | `chat() -> str`, fallback chain | env (AI_PROVIDER_DEFAULT, ключи) |

### 2.2 AICourierService (три реализации)

| Реализация | Путь | Возврат | Policy | Используется |
|------------|------|---------|--------|--------------|
| **Канон** | `core/services/ai/ai_courier_service.py` | `AICourierResult` | data/ai/ | main, admin, handlers, smoke_ai |
| Legacy wrapper | `core/services/ai_service.py` | `AIResponse(text, source, provider)` | хардкод SYSTEM_PROMPT | **Никем** |
| Legacy policy-куратор | `src/services/ai/ai_courier_service.py` | `str` | src/ai_policy/core_policy.json | **Никем** (только smoke_provider_router — роутер, не сервис) |

### 2.3 Base + провайдеры (две иерархии)

| Иерархия | Base | Response | Провайдеры | Используется в рантайме |
|----------|------|----------|------------|-------------------------|
| **Активная** | `core/services/ai/providers/base.py` | ProviderResponse | providers/openai, deepseek, groq | Да (main, smoke_ai) |
| **Мёртвая** | `core/services/ai/base.py` | LLMResponse | openai_provider, deepseek_provider, groq_provider (в корне ai/) + router.py | Нет |

### 2.4 Policy

- **Канон:** `data/ai/core_policy.json` (и остальные файлы в data/ai/).
- **Legacy:** `src/ai_policy/core_policy.json` — используется только в `src/services/ai/ai_courier_service.py` (legacy).

---

## 3. Canonical path proposal (канонический путь)

- **Единый источник правды для AI:**
  - **Сервис куратора:** `src/core/services/ai/ai_courier_service.py` (AICourierResult, data/ai/, CaseEngine, IntentEngine, FAQRepository).
  - **Роутинг провайдеров:** `src/core/services/ai/provider_router.py` + `src/core/services/ai/providers/*` (BaseProvider, ProviderResponse, config через get_settings()).
  - **Репозиторий FAQ:** `src/infra/db/repositories/faq_repo.py` (один контракт для поиска/хранения).
  - **Политика и промпты:** `data/ai/` (core_policy.json, intent_tags.json, prompts/).

- **Публичный API для бота:**
  - Внедрять в handlers только `ai_service` типа `core.services.ai.AICourierService` (get_answer → AICourierResult).
  - Провайдеры создавать в main через ProviderRouter( [GroqProvider(), DeepSeekProvider(), OpenAIProvider()] ).

---

## 4. Legacy / deprecated candidates (кандидаты на упразднение)

| Кандидат | Причина |
|----------|--------|
| **src/core/services/ai_service.py** | Не импортируется; дублирует упрощённую логику FAQ+LLM с другим контрактом (AIResponse). |
| **src/services/ai/** (каталог целиком) | Помечен как "Legacy compatibility wrapper"; единственный потребитель — smoke_provider_router.py. |
| **src/core/services/ai/base.py** | Вторая база провайдеров (LLMResponse), не используется в приложении. |
| **src/core/services/ai/router.py** | Роутер под base.LLMResponse, нигде не подключается. |
| **src/core/services/ai/openai_provider.py**, **deepseek_provider.py**, **groq_provider.py** (в корне ai/) | Провайдеры под base.LLMResponse, не используются. |
| **src/ai_policy/core_policy.json** | Policy только для legacy services/ai; канон — data/ai/. |
| **Опциональный импорт** `src.core.services.ai_response_service.build_courier_quick_reply` в ai_courier_service | Модуль не существует; при вызове ветки — ImportError. Оставить заглушку или удалить вызов. |

---

## 5. Minimal safe migration plan (минимальный безопасный план)

1. **Не удалять код сразу** — ввести адаптеры/редиректы и пометки deprecation, затем переключить единственного потребителя legacy (smoke_provider_router), затем удалить.

2. **Адаптер для scripts/smoke_provider_router.py**
   - Перевести скрипт на использование `src.core.services.ai.provider_router.ProviderRouter` и провайдеров из `core/services/ai/providers/` (как в main.py / smoke_ai.py).
   - После этого удалить зависимость от `src.services.ai`.

3. **Пометить legacy, не трогать логику**
   - В `src/core/services/ai_service.py`: в начале файла добавить deprecation warning (и комментарий "Legacy compatibility wrapper; not used. Prefer core.services.ai.ai_courier_service.").
   - В `src/services/ai/provider_router.py` и `src/services/ai/ai_courier_service.py`: оставить пометку "Legacy; canonical stack in src/core/services/ai/".

4. **Удалить мёртвую ветку base.py / router.py / flat providers (после шага 2)**
   - Удалить: `core/services/ai/base.py`, `router.py`, `openai_provider.py`, `deepseek_provider.py`, `groq_provider.py` (в корне ai/).
   - Проверить, что ни тесты, ни скрипты не импортируют их (уже проверено — не импортируют).

5. **Опционально: удалить legacy wrappers**
   - После перевода smoke_provider_router на core: удалить каталог `src/services/ai/`.
   - Удалить или оставить с deprecation до следующего цикла: `src/core/services/ai_service.py`.

6. **ai_response_service**
   - Либо завести заглушку `src/core/services/ai_response_service.py` с `build_courier_quick_reply = None` или no-op, либо убрать использование в ai_courier_service (ветку с quick_reply), чтобы не было ImportError при достижении этой ветки.

7. **Policy**
   - Оставить `data/ai/` единственным источником политики. При желании удалить `src/ai_policy/` после удаления `src/services/ai/`.

---

## 6. Files likely affected (файлы, которые затронет план)

| Действие | Файлы |
|----------|--------|
| Перевести smoke на core | `scripts/smoke_provider_router.py` |
| Deprecation-комментарии | `src/core/services/ai_service.py`, `src/services/ai/provider_router.py`, `src/services/ai/ai_courier_service.py` |
| Удаление мёртвой ветки | `src/core/services/ai/base.py`, `router.py`, `openai_provider.py`, `deepseek_provider.py`, `groq_provider.py` |
| Удаление legacy (после адаптера) | Вся папка `src/services/ai/` |
| Опционально удаление / заглушка | `src/core/services/ai_service.py`, добавление/изменение `src/core/services/ai_response_service.py` или правка `ai_courier_service._resolve_rule_reply_fn` |
| Опционально удаление policy | `src/ai_policy/core_policy.json` (после удаления services/ai) |

---

**Итог:** Один канонический стек — `core/services/ai/` (provider_router + providers/ + ai_courier_service + case_engine + intent_engine + embeddings_service) и один FAQRepository. Дубликаты: два роутера провайдеров, три варианта AICourierService, две иерархии base/provider. Миграция: переключить smoke_provider_router на core, пометить legacy, удалить мёртвые модули (base, router, flat providers), затем при желании — legacy wrappers и лишний policy.
