# Аудит архитектуры: Python Telegram AI Bot

**Статус:** снимок аудита; актуальная архитектура — [ARCHITECTURE.md](ARCHITECTURE.md) и [ARCHITECTURE_AI_LAYER.md](ARCHITECTURE_AI_LAYER.md). Режим: только анализ, без изменений кода.

---

## 1. Canonical runtime verdict

- **Является ли `src/` активным runtime?** — **Да.** Единственная точка входа в рантайм — `src/bot/main.py`. Её используют:
  - `pyproject.toml`: `[project.scripts] bot = "src.bot.main:run"`, `[tool.setuptools.packages.find] include = ["src*"]`;
  - `Dockerfile`: `CMD ["python", "-m", "src.bot.main"]`, копируются только `src/`, `scripts/`, `data/`, `migrations/`;
  - `docker-compose.yml`: сервис `bot`: `command: python -m src.bot.main`; воркер: `celery -A src.infra.queue.celery_app`.
- **Является ли `app/` legacy, активным или частично используемым?** — **Legacy / неиспользуемый.** В коде нет ни одного `from app.` или `import app`. Каталог `app/` не входит в пакеты (pyproject), не копируется в Docker, не подключается в main. В нём четыре модуля: `app/domain/analytics/mile/calculators.py`, `app/domain/analytics/mile/service.py`, `app/tools/delivery_tools.py`, `app/infrastructure/openai/responses.py` — ни один не импортируется из `src/` или тестов.
- **Используются ли оба (`src/` и `app/`)?** — **Нет.** В рантайме участвует только `src/`.

**Итог:** канонический рантайм — **только `src/`**. `app/` — неактивный код (прототип/альтернативная ветка аналитики и инструментов).

---

## 2. Runtime architecture map

| Слой | Расположение | Основные компоненты |
|------|--------------|---------------------|
| **Bot layer** | `src/bot/` | `main.py` (entrypoint), `handlers/` (start, ai_chat, verification), `admin/` (admin_handlers, ai_admin, ingest, incident, tmc_issue), `navigation.py`, `scenario_router.py`, `menu_renderer.py`, `keyboards/`, middlewares (InjectAIMiddleware, AdminOnlyMiddleware, LogUpdatesMiddleware) |
| **Application / service layer** | `src/core/` | AccessService, UserService, VerificationService, IngestService, notifications, EventBus; `proactive_layer.py` (подписки на события, уведомления о верификации, пересборка эмбеддингов FAQ) |
| **AI layer** | `src/core/services/ai/` | AIFacade (единая точка входа), AICourierService (пайплайн ответа), RAGService, IntentEngine, CaseEngine, CaseClassifier, AnalyticsAssistant, ProviderRouter, провайдеры (Groq, DeepSeek, OpenAI, OpenAICompatible), embedding_service / EmbeddingsService |
| **Risk / proactive (no LLM)** | `src/core/services/risk/` | RiskEngine, RecommendationEngine, rules, features; вызов из AICourierService.get_risk_recommendation и API automation (delivery_risk_eval) |
| **Infra layer** | `src/infra/` | db (session, models, repositories: faq_repo, verification_applications, ingest, notifications, shift_log, assets, darkstores), queue (Celery app, tasks: deliver_notification_task, parse_ingest_batch_task), storage (S3), notifications (TelegramChannel), n8n (verification_mirror) |
| **Queue / worker layer** | `src/infra/queue/` | Celery app; задачи: доставка уведомлений, парсинг ingest CSV (без вызова AI) |
| **Analytics layer** | В AI: `AnalyticsAssistant` | Метрики доставки → LLM-отчёт (`build_report`). Вызывается только через `AIFacade.analyze_csv()`; из бота/API/ингета вызова нет — только программный API. |
| **Verification / access layer** | `src/core/services/verification_service.py`, `access_service.py`, `src/bot/access_guards.py` | Верификация заявок, роли (ADMIN/LEAD/CURATOR/VIEWER/COURIER), проверки доступа в хендлерах и админке |

Поток запуска: `main()` создаёт Dispatcher, EventBus, AccessService, VerificationService, IngestService, UserService, инициализирует AI (`_init_ai`: ProviderRouter, AICourierService, AIFacade, FAQRepository), регистрирует proactive handlers, подключает роутеры (start, navigation, admin, verification, ai_chat), опционально поднимает HTTP для `POST /automation/event`.

---

## 3. AI entrypoints

Места, откуда может вызываться AI (LLM или пайплайн с возможным LLM):

| Место | Файл | Что вызывается | LLM? |
|-------|------|----------------|------|
| Обработчик входа в AI-чат (демо риска) | `src/bot/handlers/ai_chat.py` | `ai_facade.proactive_hint(_DEMO_RISK_INPUT)` | Нет (risk rule-based) |
| Ответ пользователю/админу по тексту | `src/bot/handlers/ai_chat.py` | `_ai_answer(ai_facade, user_id, text, role)` → `ai_facade.answer_user` / `answer_admin` | Да (каскад до LLM) |
| Админ: статус AI, провайдеры | `src/bot/admin/ai_admin.py` | `ai_facade.get_provider_names()`, вывод статуса | Нет |
| Админ: перезагрузка политики | `src/bot/admin/ai_admin.py` | `ai_facade.reload_policy()` | Нет |
| API automation: user_question / courier_question | `src/api/automation.py` | `ai_facade.answer_user(user_id, text)` | Да |
| API automation: delivery_risk_eval | `src/api/automation.py` | `ai_facade.proactive_hint(risk_input)` | Нет (risk) |

Внутренние точки, где реально вызывается LLM (ProviderRouter.complete / провайдеры):

| Компонент | Метод | Назначение |
|-----------|--------|------------|
| AICourierService | `_format_with_llm()` | Форматирование финального ответа по RAG-контексту (регламент-first). |
| IntentEngine | `_detect_with_llm()` | Определение интента по тексту, если правилов/ML недостаточно. |
| AnalyticsAssistant | `build_report()` | Генерация аналитического отчёта по метрикам (last-mile). |

**Важно:** `AIFacade.analyze_csv()` (и соответственно `AnalyticsAssistant.build_report`) из бота, админки или API **нигде не вызывается** — нет хендлера «загрузил CSV → получил LLM-отчёт». Функциональность доступна только программно.

---

## 4. AI layer separation status

| Слой | Наличие | Где реализован |
|------|---------|-----------------|
| **Decision layer** | Да | IntentEngine (rules + ML classifier + опционально LLM), определение интента и уверенности; выбор ветки пайплайна в AICourierService. |
| **Knowledge layer** | Да | core_policy.json, intent_tags.json, intents_catalog.json, must_match_cases; CaseEngine (регламент по интенту); FAQ в БД (faq_ai); промпты в data/ai/prompts/. |
| **Retrieval layer** | Да | RAGService (intent → FAQ semantic/hybrid → ML cases → regulations); FAQRepository (keyword + semantic по embedding_vector); CaseClassifier (лексика + опционально семантика по ml_cases_embeddings.json); semantic_search. |
| **Generation layer** | Да | ProviderRouter + провайдеры (Groq, DeepSeek, OpenAI, OpenAICompatible); AICourierService._format_with_llm; AnalyticsAssistant.build_report. |
| **Validation layer** | Частично | Пороги (faq_threshold, faq_strong_threshold, strict_intents), safety_blocker (расширяемо), high_risk_topics; нет отдельного модуля «валидации ответа». |
| **Explainability layer** | Да | AICourierResult (route, intent, confidence, evidence, source_ids, source); логирование _log_explainability; константы SOURCE_* в ai_courier_service. |
| **Proactive / risk layer** | Да (без LLM) | RiskEngine, RecommendationEngine в src/core/services/risk/; вызов из AICourierService.get_risk_recommendation и API delivery_risk_eval; проактивные события (EventBus): faq_added → rebuild embeddings, verification.pending → уведомления. |

---

## 5. Duplicate / overlapping / legacy modules

- **Дублирование админки:** в `src/` одна админка (admin_handlers, admin_menu, ai_admin, ingest, incident, tmc_issue). В `app/` админки/меню/верификации нет — дубликата нет.
- **Дублирование AI-сервисов:** в `src/` один контур (AIFacade → AICourierService, RAGService, IntentEngine и т.д.). В `app/` есть `app/infrastructure/openai/responses.py` и `app/domain/analytics/mile/` — не используются рантаймом; пересечение по смыслу с `src` только в «аналитика/миля», но код в `app/` не вызывается.
- **Эмбеддинги / retrieval:** два имени: `embedding_service` (модуль `embedding_service.py` — фасад с `get_embedding_service()`, `generate_embedding()`) и `EmbeddingsService` (реализация в `embeddings_service.py`). Дублирования логики нет: один фасад, одна реализация.
- **Верификация:** только в `src/` (handlers/verification, VerificationService, admin callback'и, proactive_layer уведомления). В `app/` верификации нет.
- **Меню / навигация:** только в `src/bot/` (menu_renderer, keyboards, navigation, scenario_router). В `app/` нет.
- **Старые AI-реализации:** класс `IntentMLEngine` в `src/core/services/ai/intent_ml_engine.py` нигде не импортируется; используется `IntentEngine` + `IntentMLClassifier` (joblib). IntentMLEngine можно считать мёртвым кодом.
- **Неиспользуемые хендлеры/сервисы:** все подключённые роутеры в main используются. Не подключён к UI аналитический сценарий: `analyze_csv` не вызывается из бота/API.

**Итог по дубликатам:** явных дубликатов внутри `src/` нет. `app/` целиком не используется. Пересечение: тематика «last-mile/аналитика» есть и в `app/domain/analytics/mile/`, и в `src` (AnalyticsAssistant, данные в data/ai), но рантайм использует только `src`.

---

## 6. Knowledge sources and loaders

Источники знаний и где загружаются в рантайме:

| Источник | Формат / расположение | Где загружается |
|----------|------------------------|------------------|
| FAQ (основной рантайм) | PostgreSQL, таблица faq_ai (в т.ч. embedding_vector) | FAQRepository — сессия передаётся из AICourierService/RAGService; список для эмбеддингов — list_embedding_sources, поиск — search_* |
| FAQ seed (начальное наполнение) | data/ai/faq_seed.jsonl | scripts/seed_faq.py (не рантайм бота); в рантайме читается только БД |
| Политика и маршрутизация | data/ai/core_policy.json | AICourierService._load_json, RAGService._load_json; must_match_cases, fallbacks, high_risk_topics, routing (faq_threshold и т.д.) |
| Интенты (каталог и теги) | data/ai/intents_catalog.json, data/ai/intent_tags.json | AICourierService, RAGService; IntentEngine.parse_intents_catalog_text, _build_keyword_rules |
| ML-кейсы | data/ai/ml_cases.jsonl | CaseClassifier._load() при создании (AICourierService, RAGService) |
| Эмбеддинги ML-кейсов | data/ai/ml_cases_embeddings.json | CaseClassifier._load() после загрузки кейсов |
| Регламенты (codex) | Нет отдельного «codex»; регламенты = must_match_cases из core_policy + CaseEngine (хардкод шагов по интенту) | CaseEngine._CASE_STEPS; RAGService._collect_regulations(intent) из core_policy |
| Промпты | data/ai/prompts/ (system_prompt.md, style_guide.md, clarify_questions.json, last_mile_analyst_*.md) | AICourierService, AnalyticsAssistant (_load_text / _load_json) |
| ML-модель интентов | data/ai/intent_classifier.joblib (ожидается по пути из IntentEngine) | IntentMLClassifier(model_path=...) в IntentEngine.__init__ |

SQL seed data для FAQ: миграции создают схему faq_ai; содержимое — через seed_faq.py из faq_seed.jsonl, не из SQL-файлов в репо. JSON-конфиги (core_policy, intent_tags, intents_catalog, clarify_questions) — загрузка с диска из `data_root` (по умолчанию `data/ai`).

---

## 7. Main architecture risks

1. **Два дерева кода (src и app):** непонятно, нужно ли сохранять `app/` для референса или переносить логику в `src/`. Риск путаницы и случайного импорта при доработках.
2. **Аналитический ассистент не доведён до UI:** `analyze_csv`/`build_report` нигде не вызываются из бота или API; нет сценария «загрузка CSV → отчёт». Риск неиспользуемого кода и расхождений ожиданий.
3. **IntentMLEngine не используется:** мёртвый код в `intent_ml_engine.py`; все вызовы идут через IntentEngine и IntentMLClassifier.
4. **Зависимость от пути к intent_classifier.joblib:** путь жёстко собирается относительно `IntentEngine` (`parents[3] / "data" / "ai" / "intent_classifier.joblib"`); при переносе или другой структуре возможен сбой.
5. **Дублирование загрузки политики/каталога:** AICourierService и RAGService по отдельности читают core_policy, intents_catalog, intent_tags; при смене формата или путей нужно править в нескольких местах.
6. **Очередь Celery не вызывает AI:** parse_ingest_batch_task только парсит CSV и пишет в БД; связки «ингет → AI-анализ» нет — это согласовано с текущим дизайном, но стоит явно зафиксировать.

---

## 8. Safe cleanup recommendations

1. **Зафиксировать статус `app/`:** в README или ARCHITECTURE указать, что рантайм — только `src/`, а `app/` — legacy/прототип; либо запланировать перенос нужных частей в `src/` и удаление остального.
2. **Удалить или пометить мёртвый код:** если IntentMLEngine не планируется использовать — удалить `intent_ml_engine.py` или явно пометить как deprecated/unused.
3. **Не трогать рабочие дубликаты имён (embedding_service vs EmbeddingsService):** это фасад и реализация; рефакторинг только при общей чистке нейминга.
4. **Проводка analyze_csv (по желанию):** если нужен сценарий «админ загрузил CSV → получил отчёт» — добавить вызов `ai_facade.analyze_csv(...)` из админ-хендлера или отдельного API после подготовки DeliveryMetrics из данных ингета; иначе явно задокументировать, что analyze_csv только для внешних/программных вызовов.
5. **Путь к intent_classifier.joblib:** вынести в конфиг (например data_root или отдельная переменная) или формировать от единого data_root из настроек, чтобы не зависеть от расположения файла IntentEngine.

---

## 9. Files that must be reviewed next

- `src/core/services/ai/intent_ml_engine.py` — решить: удалить или интегрировать.
- `src/core/services/ai/intent_engine.py` — использование LLM для интента, пороги и fallback на _detect_with_llm.
- `src/core/services/ai/ai_courier_service.py` — полный пайплайн и все SOURCE_*; пороги и загрузка политики.
- `src/core/services/ai/rag_service.py` — сбор контекста и _collect_regulations.
- `app/` целиком — решение о судьбе (удалить, перенести, оставить только как референс).
- `src/bot/admin/ingest.py` и `src/infra/queue/tasks.py` — при добавлении сценария «ингет → AI-отчёт» потребуется связка с AIFacade.analyze_csv и подготовкой метрик.
- `data/ai/core_policy.json` и `data/ai/intents_catalog.json` — форматы и консистентность с загрузчиками в AICourierService и RAGService.
- `src/core/proactive_layer.py` — список событий и подписчиков (faq_added, verification.pending и т.д.).
