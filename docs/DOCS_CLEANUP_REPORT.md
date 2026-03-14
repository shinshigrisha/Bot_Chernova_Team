# Очистка документации и маркировка legacy — отчёт

Цель: сделать документацию достоверной; канонический рантайм — `src/`, `app/` — legacy.

---

## 1. Outdated or misleading docs

| Документ | Проблема | Исправление |
|----------|----------|-------------|
| **README.md** | Утверждение «Единственный источник документации» — вводило в заблуждение при наличии docs/. | Заменено на «Основной обзор; детали в docs/» и добавлена таблица канонического набора. |
| **README.md** | Структура проекта: указаны `admin/admin.py` (главное меню), `admin/menu.py` (навигация) — неточно. | Уточнено: admin_handlers.py (главное меню), admin_router.py, admin_menu.py, ai_admin.py, incident, ingest, tmc_issue, admin.py (хелперы). Добавлены скрипты rebuild_embeddings.py, rebuild_case_embeddings.py. |
| **README.md** | Не было явной ссылки на то, что меню/доступ/верификация не вызывают LLM. | В блоке «Поток AI-ответа» добавлено предложение. |
| **pyproject.toml** | `readme = "docs/README.md"` — файл docs/README.md отсутствовал в репозитории. | Заменено на `readme = "README.md"` (корневой README). |
| **docs/ARCHITECTURE_AUDIT_REPORT.md** | Использовался как источник архитектуры без пометки «снимок аудита». | В начало добавлен статус: снимок аудита; актуальная архитектура — ARCHITECTURE.md, ARCHITECTURE_AI_LAYER.md. |
| **docs/AI_LAYER_DUPLICATE_AUDIT.md** | Аналогично. | Добавлен статус и ссылка на ARCHITECTURE_AI_LAYER.md. |
| **docs/STABLE_AI_LAYER_REPORT.md** | Аналогично. | Добавлен статус и ссылка на ARCHITECTURE_AI_LAYER.md. |

Не менялись (уже актуальны или не вводят в заблуждение): ARCHITECTURE.md, ARCHITECTURE_AI_LAYER.md (уже синхронизированы с рантаймом), ACCESS_ROLE_STATUS_LAYER.md, SCENARIO_ROUTER_LAYER.md, PROACTIVE_RISK_EVENTS.md. app/README.md уже помечен как legacy.

---

## 2. Canonical docs set

| Документ | Назначение |
|----------|------------|
| **README.md** (корень) | Основной обзор: возможности, архитектура, стек, быстрый старт, переменные, структура, БД, AI-куратор, команды, роли, тесты, развёртывание, health, устранение неполадок, n8n, Task Master. |
| **docs/README.md** | Индекс документации: канонический набор + справочные аудиты. |
| **docs/ARCHITECTURE.md** | Слои приложения, сценарии (Admin / Courier / Curator / AI Analyst), куда класть новую логику, как подключить сценарий/AI. |
| **docs/ARCHITECTURE_AI_LAYER.md** | AI: пайплайн, route classes, explainability, Curator vs Analyst, legacy-модули. |
| **docs/ADMIN_PANEL.md** | Админ-панель: вход, пункты меню, роли, ссылки на ACCESS и SCENARIO. |
| **docs/TESTING.md** | Тесты: маркеры, команды pytest, smoke, покрытие. |
| **docs/DEPLOYMENT.md** | Развёртывание: сервисы, обновление, бэкапы, откат. |
| **docs/RUNBOOK.md** | Ops: health-чеклист, устранение неполадок. |

Дополнительные (слои и контракты): ACCESS_ROLE_STATUS_LAYER.md, SCENARIO_ROUTER_LAYER.md, PROACTIVE_RISK_EVENTS.md.

---

## 3. Minimal doc changes

- **README.md:** формулировка «единственный источник» заменена на обзор + ссылка на docs/; добавлен подраздел «Документация (docs/)» с таблицей канонических документов и пометкой аудит/legacy; уточнена структура admin/ и scripts/; в блоке AI добавлено предложение про отсутствие LLM в меню/доступе/верификации; в содержание добавлен пункт «Документация docs/».
- **pyproject.toml:** `readme = "docs/README.md"` → `readme = "README.md"`.
- **docs/README.md:** создан (индекс канонического набора и справочных аудитов).
- **docs/ADMIN_PANEL.md:** создан (вход, пункты меню, роли, ссылки).
- **docs/TESTING.md:** создан (маркеры, команды, покрытие).
- **docs/DEPLOYMENT.md:** создан (сервисы, обновление, бэкапы, откат).
- **docs/RUNBOOK.md:** создан (health-чеклист, таблица неполадок).
- **docs/ARCHITECTURE_AUDIT_REPORT.md:** в начало добавлен блок «Статус: снимок аудита; актуальная архитектура — …».
- **docs/AI_LAYER_DUPLICATE_AUDIT.md:** в начало добавлен блок «Статус: снимок аудита; актуальный AI — …».
- **docs/STABLE_AI_LAYER_REPORT.md:** в начало добавлен блок «Статус: отчёт о стабилизации; актуальное описание AI — …».

Функциональность в документации не придумывалась; описание приведено в соответствие с кодом (admin_handlers, admin_router, admin_menu, скрипты пересборки эмбеддингов).

---

## 4. Legacy/archive candidates

| Кандидат | Действие |
|----------|----------|
| **app/** | Уже помечен: app/README.md и корневой README (архитектура). В индекс docs/ добавлена пометка «Каталог app/ — legacy». Архивация каталога не выполнялась — только явная маркировка. |
| **docs/ARCHITECTURE_AUDIT_REPORT.md** | Оставлен как справочный аудит; в начало добавлен статус «снимок аудита». Не переносился в архив. |
| **docs/AI_LAYER_DUPLICATE_AUDIT.md** | Аналогично: справочный аудит, статус в начале. |
| **docs/STABLE_AI_LAYER_REPORT.md** | Отчёт о стабилизации, статус в начале. |
| **Deprecated AI-модули** (intent_ml_engine.py, semantic_search.py) | Уже помечены в коде (docstring); в ARCHITECTURE_AI_LAYER.md перечислены в разделе «Legacy / неиспользуемые». Дополнительная архивная папка не создавалась. |

Отдельная папка docs/archive/ не создавалась: все документы остаются в docs/ с явным статусом в начале аудит/отчётных файлов.

---

## 5. Final diff by files

**README.md**
- Замена формулировки «Единственный источник документации» на обзор + ссылку на docs/.
- Добавлен пункт «Документация docs/» в содержание.
- В раздел «Архитектура» добавлены подраздел «Документация (docs/)» (таблица канонических документов + справочно audit/legacy + app/ legacy) и уточнение в «Поток AI-ответа» (LLM только через AIFacade/ProviderRouter; меню/доступ/верификация не вызывают LLM).
- В «Структура проекта» уточнён блок admin/ (admin_handlers, admin_router, admin_menu, ai_admin, incident, ingest, tmc_issue, admin.py) и блок scripts/ (rebuild_embeddings, rebuild_faq_embeddings, rebuild_case_embeddings).

**pyproject.toml**
- `readme = "docs/README.md"` → `readme = "README.md"`.

**docs/README.md**
- Новый файл: индекс канонического набора (ARCHITECTURE, ARCHITECTURE_AI_LAYER, ADMIN_PANEL, TESTING, DEPLOYMENT, RUNBOOK), доп. слои (ACCESS, SCENARIO, PROACTIVE), справочные аудиты (ARCHITECTURE_AUDIT_REPORT, AI_LAYER_DUPLICATE_AUDIT, STABLE_AI_LAYER_REPORT).

**docs/ADMIN_PANEL.md**
- Новый файл: вход в админку, пункты меню, роли, ссылки на ACCESS_ROLE_STATUS_LAYER и SCENARIO_ROUTER_LAYER.

**docs/TESTING.md**
- Новый файл: маркеры, команды pytest и smoke, покрытие, ссылка на README.

**docs/DEPLOYMENT.md**
- Новый файл: сервисы, обновление, бэкапы, откат, ссылка на README.

**docs/RUNBOOK.md**
- Новый файл: health-чеклист, таблица устранения неполадок, ссылка на README.

**docs/ARCHITECTURE_AUDIT_REPORT.md**
- В начало добавлен абзац «Статус: снимок аудита; актуальная архитектура — ARCHITECTURE.md и ARCHITECTURE_AI_LAYER.md.»

**docs/AI_LAYER_DUPLICATE_AUDIT.md**
- В начало добавлен абзац «Статус: снимок аудита; актуальный AI-слой — ARCHITECTURE_AI_LAYER.md.»

**docs/STABLE_AI_LAYER_REPORT.md**
- В начало добавлен абзац «Статус: отчёт о выполненной стабилизации; актуальное описание AI — ARCHITECTURE_AI_LAYER.md.»

**docs/DOCS_CLEANUP_REPORT.md**
- Новый файл: данный отчёт (outdated, canonical set, minimal changes, legacy candidates, diff).
