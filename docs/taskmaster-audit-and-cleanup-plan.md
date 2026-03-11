# Аудит Task Master и план cleanup

**Дата:** 2026-03-11  
**Правила:** project rules, task-master rules; без изменений кода — только аудит и план.

---

## 1. Анализ задач 1–10: соответствие коду

| ID | Задача | Фактическое состояние в коде | Рекомендация по статусу |
|----|--------|------------------------------|-------------------------|
| **1** | Setup Docker Compose and Makefile | `docker-compose.yml`: postgres, redis, minio, bot, worker; `Makefile`: up, down, migrate, bot, worker, logs, test. Сервисы и команды есть. | **done** (после верификации). Подзадачи 1.6–1.10 — дубликаты 1.1–1.5; их можно очистить (clear_subtasks с оставлением 1.1–1.5 и помечанием их done) или пометить cancelled. |
| **2** | Async SQLAlchemy session and ORM models | `src/infra/db/session.py`: async_session_factory, get_session(); `src/infra/db/models.py`, Base. Репозитории в `src/infra/db/repositories/`. | **done** |
| **3** | Alembic migration and repository layer | Миграции: 001_initial_mvp — 005_add_faq_embeddings. Репозитории: assets, notifications, users, shift_log, darkstores, faq_repo, ingest. | **done** |
| **4** | AssetsService, IncidentService, NotificationService, IngestService | В коде: AssetsService, NotificationService, IngestService, ShiftLogService. Отдельного класса IncidentService нет; инциденты — FSM (IncidentStates) и админ-хендлеры. ARCHITECTURE.md перечисляет Assets, ShiftLog, Notification, Ingest. | **done** (инциденты реализованы через FSM/admin, не отдельным сервисом) |
| **5** | Celery worker and notification delivery task | `src/infra/queue/celery_app.py`, `tasks.py`; в docker-compose сервис worker с командой celery. | **done** |
| **6** | /start handler and admin menu | `src/bot/handlers/start.py` (CommandStart); `src/bot/admin/menu.py` — админ-меню (ТМЦ, Журнал, Импорт CSV, Настройки, Мониторинг). | **done** |
| **7** | Standardize FAQ repository and FAQ search service | Один репозиторий `src/infra/db/repositories/faq_repo.py`; AICourierService в core использует его. Подтверждено в docs/ai-architecture-audit.md. | **done** |
| **8** | Structured logging and correlation IDs | В коде не найдены correlation_id, request_id, task_id в логах. | **pending** или **deferred** (не выполнено) |
| **9** | pytest and test repositories/service layer | `tests/conftest.py`, test_assets_repository, test_ingest_repository, test_notification_delivery, test_user_smoke, test_ai_policy_routes. `make test` → pytest. | **done** |
| **10** | Update documentation and ARCHITECTURE.md | `docs/ARCHITECTURE.md` и ряд docs/*.md есть и отражают слои, сервисы, потоки. | **done** |

**Итог по 1–10:**  
Задачи 1–7, 9, 10 фактически выполнены кодом. Задача 8 (structured logging и correlation IDs) — не реализована.

---

## 2. Задача 11: можно ли перевести в done

**Задача 11:** "Audit AI Architecture and Identify Redundancies"  
**DoD из tasks.json:** документ с каноническими модулями, дубликатами и legacy; рекомендации сформулированы.

**docs/ai-architecture-audit.md** содержит:
- Текущую карту AI (модули, провайдеры, точки входа, FAQ).
- Выявленные дубликаты: два роутера провайдеров, три реализации AICourierService, две иерархии base/provider, legacy policy.
- Предложение канонического пути (core/services/ai/, faq_repo, data/ai/).
- Кандидаты на упразднение (legacy wrappers, мёртвая ветка base/router/flat providers).
- Минимальный безопасный план миграции и список затронутых файлов.

**Вывод:** Да, задачу **11** можно перевести в **done** на основе docs/ai-architecture-audit.md. DoD выполнен.

---

## 3. Активная задача: рекомендация

**Рекомендация:** сделать активной задачу **12** — "Consolidate AI Repository and Service Contracts".

- Зависимости 12: 7, 11, 10. После перевода 7, 10, 11 в done все зависимости будут удовлетворены.
- Задача 12 — логичное продолжение аудита (11): выбор канонического FAQ/retrieval, контракты, документирование deprecated без поломки поведения. Соответствует плану из ai-architecture-audit.md.

---

## 4. Какие статусы Task Master нужно обновить

| Действие | Задачи/подзадачи |
|----------|-------------------|
| **set-status done** | 1, 2, 3, 4, 5, 6, 7, 9, 10, 11 |
| **set-status pending или deferred** | 8 (оставить как есть или явно deferred, т.к. не реализовано) |
| **Подзадачи задачи 1** | Пометить подзадачи 1.1–1.5 как done (если верификация пройдена). Подзадачи 1.6–1.10 — дубликаты; **clear_subtasks** для 1.6–1.10 или пометить их cancelled. |
| **Без изменений** | 12 (оставить pending до перевода 7, 11, 10 в done), 13–15, 16–20 (уже cancelled), 21–25 (21–25 уже done). |

Кратко:
- **done:** 1, 2, 3, 4, 5, 6, 7, 9, 10, 11  
- **pending/deferred:** 8  
- **Активная:** 12 после обновления зависимостей.

---

## 5. Новая задача: "Repository Cleanup and Legacy Removal"

Ниже — формулировка новой задачи и пяти подзадач для добавления в Task Master (add_task + add_subtask или expand).

---

### Задача (родительская)

**Title:** Repository Cleanup and Legacy Removal  

**Description:** Привести репозиторий в соответствие с результатами аудита AI-архитектуры: удалить runtime-дубликаты AI, мусор и кэши, исправить импорты на канонические пути, убрать устаревшие политики и обёртки, обновить документацию после очистки.

**Details:**  
Задача опирается на docs/ai-architecture-audit.md и план миграции из него. Цель — один канонический стек AI (core/services/ai/ + providers/ + faq_repo), без мёртвого кода и дублирующих обёрток. Без изменения наблюдаемого поведения бота и smoke-скриптов. После изменений — обновить документацию и правила.

**Scope:**  
- Удаление/пометка legacy в src/core/services/ai/, src/services/ai/, src/ai_policy/.  
- Очистка junk/cache из репозитория.  
- Импорты только на канонические пути.  
- Обновление docs и .cursor/rules при необходимости.

**DoD:**  
Дубли и мёртвые модули удалены или помечены deprecated; импорты ведут в канонические модули; smoke_ai и при необходимости smoke_provider_router проходят; документация актуальна.

**Priority:** high  
**Dependencies:** 11, 12 (или 11 — по выбору, т.к. cleanup опирается на аудит и консолидацию).

**Test strategy:**  
Запуск pytest, scripts/smoke_ai.py; проверка отсутствия импортов из удалённых модулей; ручная проверка бота и админ-меню.

---

### Подзадача 1

**Title:** Remove runtime AI duplicates  

**Description:** Удалить или пометить deprecated дубликаты AI в рантайме: мёртвая ветка base/router/flat providers в core/services/ai/, legacy src/services/ai/ после перевода smoke_provider_router на core, при необходимости — core ai_service.py.

**Details:**  
По аудиту: удалить core/services/ai/base.py, router.py, openai_provider.py, deepseek_provider.py, groq_provider.py (в корне ai/); перевести scripts/smoke_provider_router.py на core ProviderRouter; затем удалить или пометить deprecated src/services/ai/, src/core/services/ai_service.py. Проверить, что тесты и скрипты не импортируют удалённые модули.

---

### Подзадача 2

**Title:** Remove junk files and caches from repo  

**Description:** Удалить из репозитория мусорные файлы и кэши (например __pycache__, .pyc, лишние артефакты сборки/IDE), не трогая .gitignore-игнорируемые директории, если они не закоммичены.

**Details:**  
Проверить корень и ключевые каталоги на наличие закоммиченных кэшей, временных файлов, бэкапов. При необходимости обновить .gitignore. Не удалять нужные конфиги и данные (data/ai/, .env.example и т.д.).

---

### Подзадача 3

**Title:** Fix imports to canonical paths  

**Description:** Привести все импорты AI и FAQ к каноническим путям: src.core.services.ai (provider_router, providers, ai_courier_service), src.infra.db.repositories.faq_repo. Убрать импорты из src.services.ai и устаревших модулей core.

**Details:**  
Grep по проекту на импорты src.services.ai, core.services.ai_service, core.services.ai.base/router и т.п. Заменить на импорты из core.services.ai и providers. Убедиться, что бот, админ, скрипты и тесты используют только канонические пути.

---

### Подзадача 4

**Title:** Remove obsolete policies / wrappers  

**Description:** Удалить или пометить устаревшие политики и обёртки: src/ai_policy/ (если используется только legacy), неиспользуемые обёртки в core; при наличии — заглушка или правка для ai_response_service / build_courier_quick_reply.

**Details:**  
Канон политики — data/ai/. После удаления зависимости от src/services/ai/ удалить или оставить с пометкой deprecated src/ai_policy/. Проверить упоминание ai_response_service в ai_courier_service и убрать ImportError (заглушка или удаление вызова).

---

### Подзадача 5

**Title:** Update docs after cleanup  

**Description:** Обновить документацию после очистки: ARCHITECTURE.md, docs/ai-architecture-audit.md (статус миграции), при необходимости README и .cursor/rules; отразить удалённые модули и актуальные пути.

**Details:**  
В ARCHITECTURE.md и аудите указать, что legacy-модули удалены или deprecated. В .cursor/rules убедиться, что ссылки на канонический AI-стек и FAQ соответствуют коду. Кратко зафиксировать в docs, какие шаги cleanup выполнены.

---

## 6. Итоговый вывод (без изменений кода)

- **Active task recommendation:** сделать активной задачу **12** (Consolidate AI Repository and Service Contracts) после перевода 7, 10, 11 в done.
- **Статусы для обновления:**  
  - **done:** 1, 2, 3, 4, 5, 6, 7, 9, 10, 11.  
  - **pending/deferred:** 8.  
  - Задача 1: подзадачи 1.1–1.5 — done; 1.6–1.10 — очистить или cancelled.
- **Задача 11:** может быть переведена в **done** на основе docs/ai-architecture-audit.md.
- **Новая задача:** "Repository Cleanup and Legacy Removal" с пятью подзадачами (текст выше) — добавить в Task Master вручную или через MCP (add_task + add_subtask/expand). Зависимость: 11 (и при желании 12).
- **Код не менялся** — только аудит и план.
