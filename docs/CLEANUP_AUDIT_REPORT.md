# Аудит: Repository Cleanup и Legacy Removal

**Дата:** 2026-03-11  
**Задача:** полный cleanup и code review без внедрения новых фич.  
**Выполнено:** только аудит, без изменений кода.

---

## 1. Мусорные файлы и каталоги

### 1.1 В репозитории (git)

**Результат:** ни один из перечисленных типов в git **не отслеживается** (все перечислены в `.gitignore`). В репозитории лишних артефактов нет.

### 1.2 На диске (при наличии)

| Тип | Статус на диске | В .gitignore |
|-----|------------------|--------------|
| `venv/` | Не найден в workspace | Да |
| `node_modules/` | Не найден в workspace | Да |
| `.pytest_cache/` | Не найден | Да |
| `__pycache__/` | **Присутствует** (54 файла под `src/`, `tests/`, `migrations/`) | Да |
| `.DS_Store` | Не найдены | Да |
| `*.pyc` | **54 файла** (внутри `__pycache__/`) | Да (`*.py[cod]`) |
| `*.egg-info/` | **Каталог `delivery_assistant.egg-info/`** (6 файлов) | Да |

**Список лишних файлов/каталогов (для локальной очистки):**

- Все каталоги `__pycache__/` и файлы `*.pyc` (см. список ниже).
- `delivery_assistant.egg-info/` (целиком).

Примеры путей `__pycache__`:
- `src/__pycache__/`, `src/bot/__pycache__/`, `src/core/__pycache__/`, `src/core/services/__pycache__/`, `src/core/services/ai/__pycache__/`, `src/core/services/ai/providers/__pycache__/`, `src/core/domain/__pycache__/`, `src/infra/__pycache__/`, `src/infra/db/__pycache__/`, `src/infra/db/repositories/__pycache__/`, `src/infra/queue/__pycache__/`, `src/infra/notifications/__pycache__/`, `src/infra/storage/__pycache__/`, `src/infra/integrations/__pycache__/`, `src/bot/admin/__pycache__/`, `src/bot/handlers/__pycache__/`, `migrations/__pycache__/`, `tests/__pycache__/`.

---

## 2. Legacy / дублирующий AI-код

### 2.1 Указанные в задаче пути (проверка существования)

| Путь | Существует? | Комментарий |
|------|-------------|-------------|
| `src/services/ai/*` | **Нет** | Каталог отсутствует (миграция выполнена) |
| `src/core/services/ai_service.py` | **Нет** | Файл отсутствует |
| `src/core/services/ai/base.py` | **Нет** | Есть только `ai/providers/base.py` (канон) |
| `src/core/services/ai/router.py` | **Нет** | Есть только `ai/provider_router.py` (канон) |
| `src/core/services/ai/openai_provider.py` (в корне `ai/`) | **Нет** | Провайдеры только в `ai/providers/` |
| `src/core/services/ai/deepseek_provider.py` | **Нет** | Аналогично |
| `src/core/services/ai/groq_provider.py` | **Нет** | Аналогично |
| `src/ai_policy/core_policy.json` | **Нет** | Канон — `data/ai/core_policy.json` |

### 2.2 Текущий канонический AI-стек (не удалять)

- `src/core/services/ai/` — AICourierService, ProviderRouter, CaseEngine, IntentEngine, EmbeddingsService  
- `src/core/services/ai/providers/` — base.py, openai_provider.py, deepseek_provider.py, groq_provider.py  
- Политика и промпты: `data/ai/` (core_policy.json, intent_tags.json, prompts/)  
- FAQ: единственный репозиторий `src/infra/db/repositories/faq_repo.py`

**Вывод:** Legacy-файлов из списка в репозитории **нет**; дубликатов AI-кода для удаления не обнаружено.

---

## 3. Импорты, ссылающиеся на legacy или несуществующие пути

### 3.1 Импорты из несуществующих модулей

**Результат:** в текущем коде **нет** импортов из legacy-путей (`src.services.ai`, `ai_service`, `core.services.ai.base`/`router`, `ai_response_service`). Все импорты идут на канонические модули:

- `src.core.services.ai.ai_courier_service`
- `src.core.services.ai.provider_router`
- `src.core.services.ai.providers.base` / `openai_provider` / `deepseek_provider` / `groq_provider`
- `src.core.services.ai.case_engine`, `intent_engine`, `embeddings_service`
- `src.infra.db.repositories.faq_repo`

Используются в: `src/bot/main.py`, `src/bot/admin/ai_admin.py`, `src/bot/handlers/ai_chat.py`, `src/bot/middlewares/ai_inject.py`, `scripts/smoke_ai.py`, `scripts/smoke_provider_router.py`, `scripts/rebuild_faq_embeddings.py`, `tests/test_ai_policy_routes.py`.

**Примечание:** Ранее в отчёте указывался импорт `ai_response_service` в `ai_courier_service.py`. В текущей версии кода этот импорт удалён; `_resolve_rule_reply_fn` возвращает `None` и не использует внешний модуль.

### 3.2 Список неправильных импортов

**Пусто.** Неправильных или legacy-импортов не обнаружено.

---

## 4. Документация и cursor rules — рассинхрон с кодом

### 4.1 Cursor rules

| Файл | Статус |
|------|--------|
| **`.cursor/rules/01_architecture.md`** | **Актуален:** указано размещение AI в `src/core/services/ai/*` и проверка путей `src/core/services/ai/*`. Рассинхрона нет. |
| **`.cursor/rules/06_ai_alignment_guardrail.mdc`** | Общие принципы (один канон, без дублирования); путей не задаёт — рассинхрона нет. |
| **`.cursor/rules/02_ai_policy.md`** | Политика ответов и эскалации; путей к коду нет — рассинхрона нет. |
| **`.cursor/rules/00-project-overview.md`** | Упоминается «ai/: RAG KB, policies, prompts» без полного пути; при желании можно уточнить «data/ai/ и src/core/services/ai/». |

### 4.2 Документация (docs)

| Файл | Статус |
|------|--------|
| **docs/ARCHITECTURE.md** | Актуален: канон `src/core/services/ai/`, faq_repo, data/ai; legacy помечен как удалённый. |
| **docs/AI_CURATOR.md** | Актуален: реализация в `src/core/services/ai/` и `data/ai/`. |
| **docs/DOCS.md** | Актуален: реализация в `src/core/services/ai/` и `data/ai/`. |
| **docs/ai-architecture-audit.md** | Исторический аудит; в начале указано, что миграция выполнена. Таблицы ссылаются на удалённые модули — можно оставить как справку или добавить пометку «исторический документ». |
| **docs/CLEANUP_AUDIT_REPORT.md** | Этот отчёт; после обновления — актуален. |
| **docs/CLEANUP_DOCS_SYNC.md** | Описывает синхронизацию доков; актуален. |
| **docs/taskmaster-audit-and-cleanup-plan.md** | План миграции; при cleanup можно обновить статусы или пометить как выполненный. |
| **README.md** | Структура и AI-пути соответствуют коду. |

**Какие docs обновить (по желанию):**

- **docs/ai-architecture-audit.md** — добавить в начало пометку «Исторический документ; актуальная схема — ARCHITECTURE.md».
- **docs/taskmaster-audit-and-cleanup-plan.md** — обновить статусы задач или пометить документ как выполненный.
- **.cursor/rules/00-project-overview.md** — при желании явно указать «AI: src/core/services/ai/, data/ai/».

Обязательных правок документации под текущий код **не требуется**.

---

## 5. Разделение по действиям

### 5.1 Safe delete (без риска для кода в репо)

- **В репозитории** удалять нечего: мусор в git не попадает.
- **Локально** (вне коммитов) можно удалить:
  - все каталоги `__pycache__/` и файлы `*.pyc`;
  - каталог `delivery_assistant.egg-info/`;
  - при необходимости `venv/`, `node_modules/`, `.pytest_cache/` (после пересоздания окружения).

**Список safe delete кандидатов (локально):**

- `__pycache__/` (все вхождения)
- `*.pyc` (все вхождения)
- `delivery_assistant.egg-info/`
- при необходимости: `venv/`, `node_modules/`, `.pytest_cache/`

### 5.2 Needs migration

- **Нет.** Legacy-модулей и битых импортов не осталось. Миграция импортов не требуется.

### 5.3 Docs update

- **Обязательно:** нет.
- **По желанию:**
  - docs/ai-architecture-audit.md — пометка «исторический документ»;
  - docs/taskmaster-audit-and-cleanup-plan.md — обновить статусы;
  - .cursor/rules/00-project-overview.md — уточнить пути AI.

### 5.4 Import fixes

- **Нет.** Исправлять импорты не требуется.

---

## 6. Risky delete кандидаты

**Список risky delete кандидатов:** пусто.

Текущий канон `src/core/services/ai/` и `data/ai/` удалять не следует. Других претендентов на удаление с риском для работы приложения не выявлено.

---

## 7. Краткий итог

| Категория | Результат |
|-----------|------------|
| **Лишние файлы/каталоги в репо** | Нет (всё в .gitignore). На диске: __pycache__, .pyc, delivery_assistant.egg-info. |
| **Safe delete кандидаты** | В репо — нет. Локально — __pycache__, .pyc, .egg-info (и при необходимости venv/node_modules/.pytest_cache). |
| **Risky delete кандидаты** | Нет. |
| **Неправильные импорты** | Нет. |
| **Docs/rules для обновления** | Обязательных — нет. По желанию: ai-architecture-audit.md, taskmaster-audit-and-cleanup-plan.md, 00-project-overview.md. |

Код изменений не вносилось; отчёт можно использовать для планирования следующих шагов cleanup (локальная очистка и опциональное обновление документов).
