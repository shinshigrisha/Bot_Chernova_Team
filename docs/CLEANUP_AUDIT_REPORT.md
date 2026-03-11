# Аудит: Repository Cleanup и Legacy Removal

**Дата:** 2026-03-11  
**Задача:** полный cleanup и code review без внедрения новых фич.  
**Выполнено:** только аудит, без изменений кода.

---

## 1. Мусорные файлы и каталоги

### 1.1 В репозитории (git ls-files)

**Результат:** ни один из перечисленных ниже типов в git **не отслеживается** (все перечислены в `.gitignore`). В репозитории их нет.

### 1.2 На диске (при наличии)

| Тип | Статус на диске | В .gitignore |
|-----|------------------|--------------|
| `venv/` | Присутствует (используется под Python) | Да |
| `node_modules/` | Присутствует | Да |
| `.pytest_cache/` | Не найден в корне | Да |
| `__pycache__/` | **54 каталога/файла** (в т.ч. под `src/`, `tests/`, `migrations/`) | Да |
| `.DS_Store` | Не найдены в репо (на диске могут быть) | Да |
| `*.pyc` | **54 файла** (внутри `__pycache__/`) | Да (`*.py[cod]`) |
| `*.egg-info/` | **Каталог `delivery_assistant.egg-info/`** (6 файлов) | Да (`*.egg-info/`) |

**Вывод:** Лишних артефактов **в репозитории** нет. Для локальной очистки можно удалить: `__pycache__`, `*.pyc`, `delivery_assistant.egg-info`, при необходимости `venv` и `node_modules` (пересоздаются через `pip install` / `npm install`).

---

## 2. Legacy / дублирующий AI-код

### 2.1 Указанные в задаче пути (проверка существования)

| Путь | Существует? | Комментарий |
|------|-------------|-------------|
| `src/services/ai/*` | **Нет** | Каталог удалён (миграция выполнена, см. docs/ai-architecture-audit.md) |
| `src/core/services/ai_service.py` | **Нет** | Удалён |
| `src/core/services/ai/base.py` | **Нет** | Удалён; есть только `ai/providers/base.py` (канон) |
| `src/core/services/ai/router.py` | **Нет** | Удалён; есть только `ai/provider_router.py` (канон) |
| `src/core/services/ai/openai_provider.py` (в корне `ai/`) | **Нет** | Удалён; провайдеры только в `ai/providers/` |
| `src/core/services/ai/deepseek_provider.py` | **Нет** | Аналогично |
| `src/core/services/ai/groq_provider.py` | **Нет** | Аналогично |
| `src/ai_policy/core_policy.json` | **Нет** | Удалён; канон — `data/ai/core_policy.json` |

### 2.2 Текущий канонический AI-стек (оставлять как есть)

- `src/core/services/ai/` — AICourierService, ProviderRouter, CaseEngine, IntentEngine, EmbeddingsService  
- `src/core/services/ai/providers/` — base.py, openai_provider.py, deepseek_provider.py, groq_provider.py  
- Политика и промпты: `data/ai/` (core_policy.json, intent_tags.json, prompts/)  
- FAQ: единственный репозиторий `src/infra/db/repositories/faq_repo.py`

**Вывод:** Legacy-файлов из списка в репозитории **нет**; дубликатов AI-кода для удаления не обнаружено.

---

## 3. Импорты, ссылающиеся на legacy или несуществующие пути

### 3.1 Импорты из несуществующих модулей

| Файл | Импорт | Проблема |
|------|--------|----------|
| `src/core/services/ai/ai_courier_service.py` (стр. 116) | `from src.core.services.ai_response_service import build_courier_quick_reply` | Модуль **ai_response_service** не существует. Вызов обёрнут в `try/except`, при ошибке возвращается `None` — явного падения нет, но при срабатывании ветки с quick_reply будет ImportError. |

### 3.2 Импорты из текущего канона (корректные)

Все остальные импорты идут на:

- `src.core.services.ai.ai_courier_service`
- `src.core.services.ai.provider_router`
- `src.core.services.ai.providers.base` / `openai_provider` / `deepseek_provider` / `groq_provider`
- `src.core.services.ai.case_engine`, `intent_engine`, `embeddings_service`
- `src.infra.db.repositories.faq_repo`

Используются в: `src/bot/main.py`, `src/bot/admin/ai_admin.py`, `scripts/smoke_ai.py`, `scripts/smoke_provider_router.py`, `scripts/rebuild_faq_embeddings.py`, `tests/test_ai_policy_routes.py`. Legacy-путей (`src.services.ai`, `ai_service`, `core.services.ai.base`/`router`) в коде **нет**.

**Вывод:** Единственный проблемный импорт — **ai_response_service** (needs migration / import fix).

---

## 4. Документация и cursor rules — рассинхрон с кодом

### 4.1 Cursor rules — требуется правка

| Файл | Проблема |
|------|----------|
| **`.cursor/rules/01_architecture.md`** | Указано: «Новые AI-сервисы размещать в `src/services/ai/*`» и «Все новые/измененные пути соответствуют … `src/services/ai/*`». Канон в коде — **`src/core/services/ai/`**. Правило устарело и вводит в заблуждение. |

### 4.2 Документация — в целом синхронна, есть уточнения

| Файл | Статус |
|------|--------|
| **docs/ARCHITECTURE.md** | Актуален: канон `src/core/services/ai/`, faq_repo, data/ai; legacy помечен как удалённый. |
| **docs/AI_CURATOR.md** | Упоминает core_policy.json и команды; пути к модулям не детализированы — обновление по желанию. |
| **docs/DOCS.md** | Актуален; при желании можно явно указать реализацию AI в `src/core/services/ai/` и `data/ai/`. |
| **docs/ai-architecture-audit.md** | Исторический аудит; в начале указано, что миграция выполнена и актуальная схема — в ARCHITECTURE.md. Таблицы внутри всё ещё ссылаются на удалённые модули (src/services/ai, ai_service.py и т.д.) — можно оставить как справку или добавить пометку «исторический документ». |
| **docs/taskmaster-audit-and-cleanup-plan.md** | План миграции; часть задач уже выполнена; при cleanup можно обновить статусы или пометить документ как выполненный. |
| **docs/CLEANUP_DOCS_SYNC.md** | Описывает проведённую синхронизацию; актуален. |
| **README.md** | Структура и описание AI соответствуют коду (data/ai/, core_policy.json, faq_ai, команды). |
| **docs/TROUBLESHOOTING.md**, **docs/ADMIN_GUIDE.md** | Содержание не зависит от путей AI-модулей — рассинхрона нет. |

**Вывод:** Обязательное обновление — **только** `.cursor/rules/01_architecture.md`. Остальные правки — по желанию (уточнение путей, пометки «исторический»).

---

## 5. Разделение по действиям

### 5.1 Safe delete (без риска для кода в репо)

- В **репозитории** удалять нечего: перечисленный мусор в git не попадает.
- **Локально** (вне коммитов) можно удалить:
  - все каталоги `__pycache__/` и файлы `*.pyc`;
  - каталог `delivery_assistant.egg-info/`;
  - при необходимости `venv/`, `node_modules/`, `.pytest_cache/` (после пересоздания окружения).

### 5.2 Needs migration / import fixes

- **Импорт `ai_response_service`** в `src/core/services/ai/ai_courier_service.py`:
  - либо завести заглушку `src/core/services/ai_response_service.py` с `build_courier_quick_reply = None` или no-op;
  - либо убрать использование этой ветки в `_resolve_rule_reply_fn` (и при необходимости саму функцию), чтобы не было ImportError при срабатывании quick_reply.

### 5.3 Docs update

- **Обязательно:** `.cursor/rules/01_architecture.md` — заменить `src/services/ai/*` на `src/core/services/ai/*` и привести проверку путей в соответствие с текущей архитектурой.
- **По желанию:**
  - в DOCS.md / AI_CURATOR.md явно указать, что реализация AI — в `src/core/services/ai/` и `data/ai/`;
  - в docs/ai-architecture-audit.md добавить пометку «исторический документ»;
  - в docs/taskmaster-audit-and-cleanup-plan.md обновить статусы задач.

---

## 6. Краткий итог

| Категория | Результат |
|-----------|-----------|
| **Лишние файлы/каталоги в репо** | Нет (всё в .gitignore). На диске: __pycache__, .pyc, delivery_assistant.egg-info, venv, node_modules. |
| **Safe delete кандидаты** | В репо — нет. Локально — __pycache__, .pyc, .egg-info (и при необходимости venv/node_modules). |
| **Risky delete кандидаты** | Нет; текущий `src/core/services/ai/` — канон, удалять не следует. |
| **Неправильные импорты** | Один: `src.core.services.ai_response_service` (модуль отсутствует); требуется миграция/заглушка или удаление использования. |
| **Docs/rules для обновления** | Обязательно: `.cursor/rules/01_architecture.md`. Остальное — по желанию (см. п. 5.3). |

Код изменений не вносилось; отчёт можно использовать для планирования следующих шагов cleanup.
