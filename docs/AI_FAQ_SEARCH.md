# FAQ: гибридный и семантический поиск

## Обзор

Поиск по FAQ в AI-кураторе выполняется в несколько этапов (гибридный retrieval), чтобы сохранить must_match и keyword-логику и добавить семантический поиск по эмбеддингам.

## Цепочка retrieval

1. **must_match** — правила из `core_policy.json` (must_match_cases); при совпадении возвращается фиксированный ответ.
2. **case_engine** — типовые сценарии курьера по интенту; при достаточной уверенности — ответ из кейсов.
3. **Keyword search** — `FAQRepository.search_by_keywords()` по вопросу/ответу/тегам/ключевым словам.
4. **Semantic search** — при слабом keyword-результате вызывается `search_semantic(query_embedding)` по колонке `embedding_vector` (pgvector).
5. **Hybrid fallback** — если ни keyword, ни semantic не дали сильного совпадения, для контекста LLM используется `search_hybrid()` (text + keyword + semantic в одном запросе).
6. **LLM / fallback** — при отсутствии уверенного ответа из FAQ — LLM reason или политический fallback.

Семантический поиск **добавлен** к существующей логике; must_match и keyword не удаляются.

## Использование эмбеддингов

- **Модель:** OpenAI `text-embedding-3-small` (1536 измерений), сервис — `src/core/services/ai/embeddings_service.py`; фасад для скриптов — `embedding_service.py` (`generate_embedding`, `batch_generate_embeddings`).
- **Таблица `faq_ai`:**
  - `embedding` (TEXT, nullable) — legacy, сериализованный JSON-вектор.
  - `embedding_vector` (vector(1536), nullable) — нативный pgvector для индекса и быстрого similarity search.
- **Индекс:** HNSW по `embedding_vector` (при недоступности pgvector или ошибке создания — IVFFlat). Индекс создаётся миграцией `006_faq_embedding_vector`.
- **Репозиторий:** `FAQRepository.search_semantic(query_embedding, limit=5)` возвращает строки FAQ, отсортированные по косинусной близости; при отсутствии расширения pgvector возвращается `[]`.

## Пересборка эмбеддингов

Скрипт обновляет и `embedding`, и `embedding_vector` для всех активных FAQ.

**Запуск (в контейнере бота):**

```bash
docker compose exec bot python scripts/rebuild_faq_embeddings.py
```

**Требования:** настроенный `OPENAI_API_KEY`, применённые миграции (включая 005 и 006). Вывод: `FAQ_TOTAL`, `FAQ_EMBEDDINGS_UPDATED`, `FAQ_EMBEDDINGS_SKIPPED`.

При ошибке API (например 429) скрипт логирует и завершается с кодом 0, чтобы не ломать пайплайн.

## Наблюдаемость

В логах AI-куратора (structlog) доступны поля:

- **retrieval_stage** — этап, на котором выбран ответ: `keyword`, `semantic_faq`, `none` (далее hybrid/LLM/fallback).
- **semantic_score** — оценка совпадения по семантическому поиску (0–1).
- **semantic_hit** — был ли хотя бы один результат семантического поиска.

Пример: `route=semantic_faq`, `semantic_score=0.87`, `retrieval_stage=semantic_faq`.

## Регрессионные тесты

- `tests/test_faq_semantic_search.py` — пустой/невалидный embedding, fallback при отсутствии pgvector, сохранение поведения keyword search, порядок по score при наличии результатов.
