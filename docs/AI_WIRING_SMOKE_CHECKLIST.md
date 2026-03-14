# Финальный smoke-чеклист AI-стека

## 1. Wiring checklist

| # | Проверка | Где смотреть |
|---|----------|---------------|
| 1 | **OpenAI-compatible endpoint** — `OPENAI_BASE_URL` и `OPENAI_API_KEY` читаются, провайдер `openai_compatible` в роутере | `src/config.py` (openai_base_url, openai_api_key), `OpenAICompatibleProvider`, `bot/main.py` (ProviderRouter с OpenAICompatibleProvider) |
| 2 | **fast / reasoning / analytics / fallback** — конфиг по режимам ведёт на нужные provider+model | `model_config.get_model_config(mode)`, `config`: ai_fast_*, ai_reasoning_*, ai_analytics_*, ai_fallback_* |
| 3 | **Local MiniLM embeddings** — модель грузится, вектор 384 размерности | `EmbeddingsService` (local), `scripts/smoke_embeddings.py` |
| 4 | **FAQ seed читается** — файл есть и парсится | `data/ai/faq_seed.jsonl`, `scripts/seed_faq.py` |
| 5 | **FAQ embeddings rebuild** — скрипт обновляет `faq_ai.embedding_vector` | `scripts/rebuild_faq_embeddings.py`, `faq_embeddings_rebuild.rebuild_faq_embeddings_async` |
| 6 | **ML case embeddings rebuild** — скрипт пишет `ml_cases_embeddings.json` | `scripts/rebuild_case_embeddings.py`, `data/ai/ml_cases_embeddings.json` |
| 7 | **Semantic search возвращает результаты** — pgvector + эмбеддинги, тесты проходят | `FAQRepository.search_semantic`, тесты `test_faq_semantic_search`, `test_semantic_retrieval_smoke` |
| 8 | **RAG path получает retrieval context** — `build_context` возвращает контекст с faq_hits и retrieval_stage | `RAGService.build_context` → `RAGKnowledgeContext` (faq_hits, retrieval_stage, context_text) |
| 9 | **Тесты проходят** | `pytest` с маркерами smoke / без external |

---

## 2. Команды

Выполнять из корня репозитория. Для скриптов с БД при запуске не в Docker подставьте `localhost` вместо `postgres` в `DATABASE_URL` (или задайте `SMOKE_DATABASE_URL` / `SEED_DATABASE_URL`).

```bash
# 1) Конфиг OpenAI-compatible и моделей (fast/reasoning/analytics/fallback)
python scripts/smoke_ai_config.py

# 2) Local MiniLM embeddings загружаются, вектор 384
python scripts/smoke_embeddings.py

# 3) FAQ seed читается (первая строка валидного JSON)
head -1 data/ai/faq_seed.jsonl | python -c "import sys,json; json.load(sys.stdin); print('OK')"

# 4) FAQ embeddings rebuild (требует БД + миграции + seed)
python scripts/rebuild_faq_embeddings.py

# 5) ML case embeddings rebuild (без БД)
python scripts/rebuild_case_embeddings.py

# 6) Provider router (LLM один запрос; нужен хотя бы один API key)
python scripts/smoke_provider_router.py

# 7) Полный smoke AI (golden_cases → get_answer; БД + FAQ не пусто)
python scripts/smoke_ai.py

# 8) Тесты (smoke + семантика + RAG), без external
pytest tests/ -m "smoke" -v
pytest tests/test_faq_semantic_search.py tests/test_semantic_retrieval_smoke.py tests/test_embedding.py tests/test_ai_facade.py tests/test_ai_policy_routes.py -v

# 9) Все тесты, кроме external
pytest tests/ -m "not external" -v
```

---

## 3. Ожидаемые выводы

| Команда | Ожидаемый вывод (ключевые строки) |
|---------|-----------------------------------|
| `python scripts/smoke_ai_config.py` | `OPENAI_BASE_URL=...`, `OPENAI_API_KEY_SET=true` или `false`, `AI_FAST_PROVIDER=openai_compatible`, `AI_FAST_MODEL=...`, то же для reasoning/analytics/fallback, `EMBEDDING_PROVIDER=local`, `EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2` |
| `python scripts/smoke_embeddings.py` | `EMBEDDING_PROVIDER=local`, `ENABLED=True`, `VECTOR_DIM=384`, `OK: model loaded, vector produced, length check passed`, exit 0 |
| `head -1 data/ai/faq_seed.jsonl \| python -c "..."` | `OK` (без ошибки JSON) |
| `python scripts/rebuild_faq_embeddings.py` | `FAQ_TOTAL=<N>`, `FAQ_EMBEDDINGS_UPDATED=...`, `FAQ_EMBEDDINGS_SKIPPED=...`, без `Error:` |
| `python scripts/rebuild_case_embeddings.py` | `total: 90, updated: 90, skipped: 0`, `output: .../data/ai/ml_cases_embeddings.json` |
| `python scripts/smoke_provider_router.py` | При наличии ключа: `SMOKE: provider_router OK`; без ключей: `SMOKE: skipped (no provider keys configured)` |
| `python scripts/smoke_ai.py` | `AI_ENABLED=...`, `ENABLED_PROVIDERS=...`, `FAQ_COUNT=>0`, `ANSWERED=>0`, `ROUTE_COUNTS=...`, без падения с RuntimeError |
| `pytest tests/ -m "smoke" -v` | Все отмеченные smoke-тесты passed |
| `pytest tests/test_faq_semantic_search.py tests/test_semantic_retrieval_smoke.py ... -v` | Все перечисленные тесты passed (часть может skip при отключённых эмбеддингах) |

---

## 4. Оставшиеся риски и слабые места

| Риск | Описание | Рекомендация |
|------|----------|--------------|
| **smoke_ai и openai_compatible** | `scripts/smoke_ai.py` собирает роутер из Groq/DeepSeek/OpenAI, **без** `OpenAICompatibleProvider`. Полный E2E с `OPENAI_BASE_URL` проверяется только при запуске бота. | Либо добавить `OpenAICompatibleProvider()` в `smoke_ai._build_router_or_none()` при наличии `OPENAI_API_KEY`, либо отдельный маленький скрипт: роутер только с OpenAICompatible + один `complete()`. |
| **БД и миграции** | Rebuild FAQ и smoke_ai требуют поднятую PostgreSQL и применённые миграции (в т.ч. pgvector). | В CI/доках явно указать: `alembic upgrade head`, затем seed_faq, затем rebuild_faq_embeddings. |
| **Тесты и pgvector** | Часть тестов FAQ/semantic зависит от расширения pgvector в тестовой БД. Без pgvector `search_semantic` возвращает `[]` — тесты рассчитаны на это (fallback). | Убедиться, что тестовая БД с pgvector при необходимости (например в CI). |
| **Флаги ENABLE_***_SEMANTIC / RAG** | Поведение может меняться от `AI_ENABLE_SEMANTIC_SEARCH`, `AI_ENABLE_RAG`, `ENABLE_FAQ_SEMANTIC_SEARCH`. | В чеклисте учитывать: при выключенном RAG/semantic smoke может не использовать соответствующий путь. |
| **Размер контекста** | RAG передаёт в LLM ограниченное число FAQ (ai_max_context_items). | Следить за лимитами и длиной промпта при росте базы. |

---

**Итог:** чеклист покрывает конфиг (1–2), эмбеддинги (3), данные и пересборку (4–6), семантический поиск и RAG (7–8) и прогон тестов (9). Для полной проверки цепочки с **openai_compatible** endpoint после всех команд можно один раз запустить бота и отправить тестовое сообщение в чат AI-куратора.
