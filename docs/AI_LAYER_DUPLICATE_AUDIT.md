# Аудит дубликатов AI-слоя (focused duplicate-audit)

**Статус:** снимок аудита; актуальный AI-слой — [ARCHITECTURE_AI_LAYER.md](ARCHITECTURE_AI_LAYER.md). Режим: только анализ, без рефакторинга.

---

## 1. AI module inventory

### src/ (активный рантайм)

| Модуль | Путь | Назначение |
|--------|------|------------|
| ai_facade | src/core/services/ai/ai_facade.py | Единая точка входа: answer_user, answer_admin, proactive_hint, analyze_csv, reload_policy, get_provider_names |
| ai_courier_service | src/core/services/ai/ai_courier_service.py | Пайплайн ответа курьеру/админу: safety → must_match → case_engine → faq/semantic_faq → semantic_case → llm_reason → fallback; форматирование RAG; _log_explainability |
| ai_modes | src/core/services/ai/ai_modes.py | AIMode, AirRouteClass; маппинг route → класс (no_llm / reasoning / analytics) |
| ai_chat | src/bot/handlers/ai_chat.py | Хендлеры входа в AI-чат и обработки сообщений; вызов ai_facade.answer_user/answer_admin, proactive_hint |
| ai_admin | src/bot/admin/ai_admin.py | Админ: статус AI, список провайдеров, reload_policy |
| ai_inject | src/bot/middlewares/ai_inject.py | Middleware: прокидывает ai_service, ai_facade, ai_router, provider_router в handler data |
| ai_curator | src/bot/keyboards/ai_curator.py | Клавиатуры для сценария AI-куратора (callback-префиксы, кнопки) |
| rag_service | src/core/services/ai/rag_service.py | Retrieval: build_context (intent → FAQ → cases → regulations), _build_llm_context; загрузка core_policy, intents_catalog, intent_tags |
| semantic_search | src/core/services/ai/semantic_search.py | Тонкая обёртка: embed_text → generate_embedding; search_similar_faq (семантика + fallback на hybrid) |
| embedding_service | src/core/services/ai/embedding_service.py | Фасад: get_embedding_service(), generate_embedding(), batch_generate_embeddings(); возвращает EmbeddingsService |
| embeddings_service | src/core/services/ai/embeddings_service.py | Реализация: AsyncOpenAI для эмбеддингов (embed_text, embed_texts), serialize_embedding, build_faq_text |
| faq_embeddings_rebuild | src/core/services/ai/faq_embeddings_rebuild.py | Пересборка эмбеддингов FAQ в БД (pgvector); вызывается из proactive_layer и скриптов |
| provider_router | src/core/services/ai/provider_router.py | Маршрутизация complete() по ModelConfig (mode → provider+model); вызов provider.complete() |
| providers/base | src/core/services/ai/providers/base.py | BaseProvider, ProviderResponse |
| providers/openai_provider | src/core/services/ai/providers/openai_provider.py | OpenAI chat completion (AsyncOpenAI) |
| providers/openai_compatible_provider | src/core/services/ai/providers/openai_compatible_provider.py | OpenAI-compatible endpoint (base_url + api_key) |
| providers/groq_provider | src/core/services/ai/providers/groq_provider.py | Groq completion (AsyncGroq) |
| providers/deepseek_provider | src/core/services/ai/providers/deepseek_provider.py | DeepSeek (AsyncOpenAI + base_url) |
| case_engine | src/core/services/ai/case_engine.py | Правила по интенту (регламент): _CASE_STEPS, resolve() → CaseEngineResult (без LLM) |
| case_classifier | src/core/services/ai/case_classifier.py | Загрузка ml_cases.jsonl + ml_cases_embeddings.json; find_similar_case (lexical), find_similar_case_semantic |
| intent_engine | src/core/services/ai/intent_engine.py | Детекция интента: keyword rules, catalog, IntentMLClassifier (joblib), опционально _detect_with_llm; normalize_intent, faq_tag_for_intent |
| intent_ml_classifier | src/core/services/ai/intent_ml_classifier.py | Обёртка над intent_classifier.joblib (TF-IDF + LogisticRegression); используется в IntentEngine |
| intent_ml_engine | src/core/services/ai/intent_ml_engine.py | IntentMLEngine: nearest-neighbour по delivery_intents_90.json, IntentEngine._similarity — **нигде не импортируется** |
| analytics_assistant | src/core/services/ai/analytics_assistant.py | Отчёт по метрикам доставки: build_report() → ProviderRouter.complete(mode="analysis"); промпты last_mile_analyst_* |
| model_config | src/core/services/ai/model_config.py | ModelConfig, get_model_config(mode) → provider+model из настроек |

### app/ (вне рантайма)

| Модуль | Путь | Назначение |
|--------|------|------------|
| openai/responses | app/infrastructure/openai/responses.py | run_mile_agent(): **прямой вызов** OpenAI() и client.responses.create() (sync, model gpt-5.4, JSON schema); не импортируется из src |
| domain/analytics/mile/calculators | app/domain/analytics/mile/calculators.py | MileOrder, filter_successful_orders, calc_delay_rate и др. — только расчёты, без LLM |
| domain/analytics/mile/service | app/domain/analytics/mile/service.py | build_mile_analysis(orders) — агрегация метрик по ДС/ТТ, без вызова AI |
| tools/delivery_tools | app/tools/delivery_tools.py | Заглушки get_mile_orders, get_courier_stats и т.д. (NotImplementedError); без AI |

### Скрипты и тесты (влияют на дубликаты/контракты)

| Файл | Назначение |
|------|------------|
| scripts/rebuild_embeddings.py | Единый скрипт: --faq / --cases / --all; вызывает rebuild_faq_embeddings и rebuild_case_embeddings |
| scripts/rebuild_faq_embeddings.py | Только FAQ: rebuild_faq_embeddings_async() |
| scripts/rebuild_case_embeddings.py | Только ML-кейсы: перезапись ml_cases_embeddings.json через EmbeddingsService |
| scripts/smoke_ai.py | Дымовой тест пайплайна AICourierService + провайдеры |
| scripts/smoke_provider_router.py | Дымовой тест ProviderRouter.complete() |
| tests/test_semantic_retrieval_smoke.py | Тесты get_embedding_service, generate_embedding, RAGService.build_context |
| tests/test_faq_semantic_search.py | Тесты семантического поиска FAQ |
| example.py | Сниппет client.responses.create() — не часть приложения |

---

## 2. Responsibility groups

| Группа | Модули | Пояснение |
|--------|--------|-----------|
| **entrypoints** | ai_facade, ai_chat (handlers), ai_admin, api/automation | Точки входа в AI из бота/API; только фасад и хендлеры |
| **decision** | intent_engine, intent_ml_classifier, ai_modes | Определение интента, маршрут (no_llm / reasoning / analytics) |
| **retrieval** | rag_service, semantic_search, case_classifier, faq_repo (infra) | Поиск FAQ (keyword/semantic/hybrid), кейсы, регламенты; сбор контекста для LLM |
| **generation** | provider_router, providers/*, ai_courier_service._format_with_llm, analytics_assistant.build_report | Вызов LLM через router; форматирование ответа курьера и аналитического отчёта |
| **validation** | (нет отдельного модуля) | Пороги в ai_courier_service (faq_threshold, strict_intents), safety_blocker; проверка структуры ответа после LLM (_format_rag_answer если LLM не соблюдал формат) |
| **explainability** | ai_courier_service._log_explainability, AICourierResult (route, intent, evidence, source) | Единственное место логирования explainability — внутри AICourierService |
| **analyst-only** | analytics_assistant, ai_facade.analyze_csv, model_config (ANALYTICS) | Отчёт по метрикам; mode="analysis" в router; не участвует в пайплайне ответа курьеру |
| **curator-only** | ai_courier_service, case_engine, пайплайн must_match → faq → case → llm_reason → fallback | Ответ курьеру/админу по кейсам и регламентам |
| **mixed responsibility** | rag_service (retrieval + сбор контекста), intent_engine (decision + опционально LLM для интента), ai_courier_service (orchestration + formatting + explainability) | Не дублирование, а совмещение обязанностей в одном модуле по дизайну |

---

## 3. Confirmed overlaps / duplicates

### 3.1 Intent: IntentEngine vs IntentMLEngine

| Аспект | IntentEngine | IntentMLEngine |
|--------|--------------|----------------|
| Файл | intent_engine.py | intent_ml_engine.py |
| Роль | Детекция интента: keyword rules + catalog + **IntentMLClassifier** (joblib) + при необходимости _detect_with_llm | Nearest-neighbour по delivery_intents_90.json, использует IntentEngine._similarity |
| Использование | Используется в AICourierService, RAGService | **Нигде не импортируется** |
| Канонический | Да | Нет (мёртвый код) |
| Оба активны? | Да | Нет |
| Drift risk | Нет | Нет (код не в цепочке вызовов) |

**Вывод:** IntentMLEngine — дубликат/альтернативная реализация интента по данным delivery_intents_90.json; в рантайме используется только IntentEngine с IntentMLClassifier (joblib). Пересечение по ответственности: «определение интента по тексту». Один канонический, второй — legacy/unused.

---

### 3.2 Embeddings: embedding_service vs EmbeddingsService

| Аспект | embedding_service | EmbeddingsService |
|--------|-------------------|-------------------|
| Файл | embedding_service.py | embeddings_service.py |
| Роль | Фасад: get_embedding_service(), generate_embedding(), batch_generate_embeddings() | Реализация: AsyncOpenAI, embed_text(s), serialize_embedding, build_faq_text |
| Пересечение | Нет дублирования логики; фасад вызывает EmbeddingsService | Единственная реализация эмбеддингов для FAQ и кейсов |
| Канонический вход | get_embedding_service() / generate_embedding() | Используется через фасад или напрямую (faq_embeddings_rebuild, RAGService при передаче embeddings_service) |
| Оба активны? | Да | Да |
| Drift risk | Низкий: один фасад, одна реализация |

**Вывод:** Пересечение по названию (embedding vs embeddings), не по логике. Дублирования нет; фасад + реализация.

---

### 3.3 Загрузка политики и каталога: AICourierService vs RAGService

| Аспект | AICourierService | RAGService |
|--------|------------------|------------|
| Файлы | ai_courier_service.py | rag_service.py |
| Что загружают | core_policy.json, intent_tags.json, intents_catalog.json, clarify_questions.json, system_prompt.md, style_guide.md | core_policy.json, intent_tags.json, intents_catalog.json (или получает от вызывающего) |
| Пересечение | Оба читают одни и те же JSON и строят IntentEngine / policy-структуры | RAGService может получить core_policy/intents от снаружи (AICourierService передаёт при создании) |
| Канонический | AICourierService создаёт RAGService и передаёт ему policy и intents_catalog | RAGService — потребитель, при инициализации из фасада получает уже загруженное |
| Drift risk | Средний: при смене формата/путей править в двух местах (AICourierService и RAGService._load_json при отсутствии переданных данных) |

**Вывод:** Дублирование загрузки файлов (core_policy, intents_catalog, intent_tags): в AICourierService при инициализации и в RAGService при создании без передачи (self._load_json). В рантайме main создаёт только AICourierService, который передаёт policy в RAGService — то есть второй загрузчик в RAG используется только если RAGService создают отдельно. Риск — расхождение форматов или путей при изменении конфигов.

---

### 3.4 Семантический поиск FAQ: semantic_search vs faq_repo

| Аспект | semantic_search | faq_repo (FAQRepository) |
|--------|-----------------|---------------------------|
| Файлы | semantic_search.py | infra/db/repositories/faq_repo.py |
| Роль | search_similar_faq(): embed_text (через generate_embedding) → faq_repo.search_semantic; fallback на search_hybrid | search_semantic(), search_hybrid(), search_keyword() — работа с БД |
| Пересечение | semantic_search — тонкая оркестрация «эмбеддинг + поиск»; сама не хранит данные | Вся работа с таблицей faq_ai и embedding_vector |
| Кто вызывает semantic_search | Прямых вызовов в src не найдено; AICourierService и RAGService используют faq_repo + get_embedding_service напрямую | AICourierService, RAGService, faq_embeddings_rebuild |
| Drift risk | Низкий; модуль может быть неиспользуемым в рантайме (вызовы идут через faq_repo и embedding_service напрямую) | Канонический слой доступа к FAQ |

**Вывод:** semantic_search — возможный дубликат потока «embed + search_semantic + fallback hybrid»: тот же поток реализован внутри RAGService и AICourierService через faq_repo и embeddings_service. Нужно проверить импорты semantic_search в проекте; если нигде не используется — дубликат потока, а не кода.

---

### 3.5 Пересборка эмбеддингов: три скрипта

| Скрипт | Роль | Пересечение |
|--------|------|-------------|
| rebuild_embeddings.py | Единая точка: --faq / --cases / --all; вызывает subprocess или импорт rebuild_faq_embeddings + rebuild_case_embeddings | Обёртка над двумя другими |
| rebuild_faq_embeddings.py | Только FAQ: rebuild_faq_embeddings_async() | Логика пересборки FAQ в одном месте |
| rebuild_case_embeddings.py | Только ml_cases: запись в ml_cases_embeddings.json | Отдельная логика для кейсов |

**Вывод:** Дублирования нет; иерархия: один общий скрипт и два целевых. Риск только в расхождении контрактов (например, разный способ вызова async).

---

### 3.6 Ответ и форматирование (response formatting)

Вся логика форматирования ответа курьеру сосредоточена в **ai_courier_service.py**: _format_rag_answer, _build_rag_answer, _normalize_reply, _format_with_llm. Второго модуля с той же ответственностью нет. Аналитический отчёт формирует только **analytics_assistant.build_report** (один вызов router.complete). Дубликатов нет.

---

## 4. Direct provider bypasses

Под «bypass» имеется в виду вызов LLM/embeddings **напрямую** (OpenAI/Groq/DeepSeek или их клиенты), минуя **AIFacade** и **ProviderRouter** для completion-запросов.

| Расположение | Что делается | Обход фасада? |
|--------------|--------------|----------------|
| src/core/services/ai/providers/* | Провайдеры вызывают AsyncOpenAI / AsyncGroq в complete() | Нет: провайдеры — часть канонического пути; их вызывает только ProviderRouter |
| src/core/services/ai/embeddings_service.py | AsyncOpenAI для embeddings.create() | Нет: эмбеддинги выделены в конфиге (embedding_provider); единая точка — EmbeddingsService, используется через get_embedding_service() |
| src/core/services/ai/ai_courier_service.py | self._router.complete(...) | Нет: router = ProviderRouter |
| src/core/services/ai/intent_engine.py | self._router.complete(...) в _detect_with_llm | Нет |
| src/core/services/ai/analytics_assistant.py | self._router.complete(...) | Нет |
| **app/infrastructure/openai/responses.py** | **OpenAI() (sync), client.responses.create(model="gpt-5.4", ...)** | **Да: прямой вызов API, другой контракт (responses API), не через фасад/роутер. Модуль не в рантайме (app не подключается).** |
| example.py | client.responses.create(...) | Да по смыслу, но это пример/сниппет, не часть приложения |

**Итог:** В **src/** обхода фасада/роутера для completion нет. Прямой вызов провайдера — в **app/infrastructure/openai/responses.py** (run_mile_agent); в активном рантайме не используется.

---

## 5. AI curator vs AI analyst separation status

| Аспект | Статус |
|--------|--------|
| **Разделение по коду** | Чёткое: куратор — AICourierService + пайплайн (answer_user / answer_admin / proactive_hint); аналитик — AnalyticsAssistant.build_report, вызывается только через ai_facade.analyze_csv(). Общий только ProviderRouter и model_config (режимы chat vs analysis). |
| **Общие зависимости** | ProviderRouter, get_settings(), data_root/prompts. Режимы в provider_router: "chat"/"reasoning" для куратора, "analysis"/"analytics" для аналитика. |
| **Смешение логики** | Нет: в пайплайне ответа курьеру нет вызовов build_report или analyze_csv; analyze_csv нигде не вызывается из бота/API (нет сценария «загрузил CSV → отчёт»). |
| **app/** | app/infrastructure/openai/responses.py (run_mile_agent) — аналитический сценарий (mile + JSON schema); app/domain/analytics/mile — только расчёты, без LLM. В рантайме не используются. |

**Итог:** В **src** куратор и аналитик разделены; смешения нет. Аналитик в app — отдельный, неиспользуемый путь с прямым вызовом API.

---

## 6. Canonical candidates

| Ответственность | Канонический модуль/точка входа |
|-----------------|----------------------------------|
| Вход в AI из бота/API | AIFacade (answer_user, answer_admin, proactive_hint, analyze_csv) |
| Пайплайн ответа курьеру | AICourierService.get_answer |
| Детекция интента | IntentEngine (rules + catalog + IntentMLClassifier + опционально LLM) |
| Retrieval для RAG | RAGService.build_context; FAQRepository; CaseClassifier |
| Эмбеддинги | get_embedding_service() → EmbeddingsService; generate_embedding() для одного текста |
| Вызов LLM (completion) | ProviderRouter.complete(); провайдеры — только через роутер |
| Конфиг модели по режиму | model_config.get_model_config(mode) |
| Форматирование ответа курьеру | AICourierService._format_rag_answer, _build_rag_answer, _format_with_llm |
| Explainability | AICourierService._log_explainability; AICourierResult |
| Пересборка эмбеддингов FAQ | faq_embeddings_rebuild.rebuild_faq_embeddings_async (и скрипт rebuild_faq_embeddings / rebuild_embeddings) |
| Пересборка эмбеддингов кейсов | scripts/rebuild_case_embeddings.py |

---

## 7. Legacy/deprecated candidates

| Кандидат | Причина |
|----------|---------|
| **intent_ml_engine.py** (IntentMLEngine) | Нигде не импортируется; интент в рантайме идёт через IntentEngine + IntentMLClassifier (joblib). |
| **app/infrastructure/openai/responses.py** | Прямой вызов OpenAI, не в рантайме (app не подключается); альтернативный аналитический сценарий (mile + responses API). |
| **app/domain/analytics/mile/** | Нет вызовов из src; дублирует тематику last-mile с src (AnalyticsAssistant + data/ai), но без LLM. |
| **app/tools/delivery_tools.py** | Заглушки, не используются. |
| **semantic_search.py** | **Не используется:** в коде нет импортов `semantic_search` или вызовов `search_similar_faq`; поток идёт через faq_repo + embeddings_service в RAGService и AICourierService. Можно считать устаревшей обёрткой. |

---

## 8. Risk level by duplicate group

| Группа дубликатов/пересечений | Уровень риска | Пояснение |
|-------------------------------|---------------|------------|
| IntentMLEngine vs IntentEngine | Низкий | Мёртвый код; не влияет на поведение, только засоряет репо. |
| app/ openai/responses (run_mile_agent) | Низкий | Вне рантайма; при возможном переносе в src — риск двух путей вызова API (фасад vs прямой). |
| Загрузка policy/catalog в AICourierService и RAGService | Средний | При изменении формата/путей нужно править в двух местах; возможен drift. |
| semantic_search vs прямой faq_repo+embedding в RAG/AICourier | Низкий | Если semantic_search не вызывается — лишний модуль; если вызывается — один поток, дублирования логики нет. |
| Embedding facade vs EmbeddingsService | Минимальный | Нет дублирования, только два имени слоёв. |

---

## 9. Minimal cleanup order

Без изменения поведения, только анализ и при необходимости точечная очистка:

1. **Подтвердить использование semantic_search**  
   Поиск по репозиторию вызовов `search_similar_faq` или `from src.core.services.ai.semantic_search`. Если вызовов нет — пометить модуль как неиспользуемый или удалить.

2. **Удалить или пометить IntentMLEngine**  
   intent_ml_engine.py нигде не импортируется. Либо удалить, либо явно пометить в коде/доках как deprecated/unused.

3. **Зафиксировать статус app/**  
   В README или архитектурном документе указать: app/ не входит в рантайм; app/infrastructure/openai/responses.py — прямой вызов провайдера, при переносе функциональности вести вызовы через AIFacade/ProviderRouter.

4. **Загрузка policy/intents**  
   При следующем изменении формата core_policy или intents_catalog синхронно обновить оба места загрузки (AICourierService и RAGService) или вынести загрузку в один общий модуль и передавать в оба сервиса.

5. **example.py**  
   Оставить как есть или удалить, если не нужен как пример; на рантайм не влияет.

Дальнейшие шаги (уже с рефакторингом): при необходимости ввести единый загрузчик конфигов для AICourierService и RAGService; при переносе run_mile_agent в src — использовать только фасад/роутер.
