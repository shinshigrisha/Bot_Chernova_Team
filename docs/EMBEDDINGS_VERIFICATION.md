# Проверка эмбеддингов end-to-end (MiniLM)

## 1. Точки верификации

| # | Проверка | Где |
|---|----------|-----|
| 1 | **Модель загружается** | `get_embedding_service()` создаёт `EmbeddingsService` с `_LocalBackend`; при первом `embed_text()` загружается SentenceTransformer (MiniLM-L6-v2). |
| 2 | **Вектор эмбеддинга получается** | `embed_text("...")` возвращает `list[float]` длины 384. |
| 3 | **Семантический поиск использует канонический сервис** | RAGService и FAQRepository получают эмбеддинг через `get_embedding_service().embed_text()`; путь: `embedding_service` → `faq_repo.search_semantic(query_embedding=...)`. |
| 4 | **RAG/retrieval получает результаты по эмбеддингам** | `RAGService._retrieve_faq()` вызывает `embed_text` → `search_semantic`; `retrieval_stage` может быть `semantic` или `hybrid`. |
| 5 | **В логах рантайма виден активный бэкенд** | При старте бота в лог пишется строка `active_embedding_backend: provider=local model=sentence-transformers/all-MiniLM-L6-v2 enabled=True`. |

## 2. Что добавлено

- **Скрипт дыма эмбеддингов**  
  `scripts/smoke_embeddings.py` — загрузка сервиса, один вызов `embed_text`, проверка длины вектора 384 и вывод `EMBEDDING_PROVIDER`, `EMBEDDING_MODEL`, `VECTOR_DIM`.

- **Smoke-тест семантического поиска**  
  В `tests/test_semantic_retrieval_smoke.py`: `test_semantic_retrieval_canonical_path` — получение эмбеддинга через `get_embedding_service().embed_text()`, вызов `FAQRepository.search_semantic()` с этим вектором, проверка что результат — список с полями `id`, `question`, `answer`, `score`.

- **Рантайм-лог активного бэкенда**  
  В `src/bot/main.py` при инициализации AI после `get_embedding_service()` добавлен вызов:
  `logger.info("active_embedding_backend: provider=%s model=%s enabled=%s", ...)`.

- **Свойство `provider` у EmbeddingsService**  
  В `src/core/services/ai/embeddings_service.py` добавлено свойство `provider` для вывода в лог.

- **Исправление теста**  
  В `tests/test_faq_semantic_search.py` для `test_search_semantic_accepts_list_embedding` допущен `NaN` в `score` (pgvector для нулевого вектора может вернуть NaN).

## 3. Изменённые файлы (краткий diff)

- **src/core/services/ai/embeddings_service.py** — свойство `provider`.
- **src/bot/main.py** — лог `active_embedding_backend` при старте.
- **scripts/smoke_embeddings.py** — новый файл (smoke: модель + вектор 384).
- **tests/test_semantic_retrieval_smoke.py** — тест `test_semantic_retrieval_canonical_path` и импорт `FAQRepository`.
- **tests/test_faq_semantic_search.py** — `import math`, проверка score с учётом NaN.

## 4. Команды для запуска

```bash
# Из корня репозитория

# 1) Smoke эмбеддингов (модель + вектор)
python scripts/smoke_embeddings.py

# 2) Все тесты (в т.ч. эмбеддинги и семантический поиск)
pytest -q

# 3) Только smoke-тесты (в т.ч. test_semantic_retrieval_canonical_path, test_local_embedding_smoke)
pytest -q -m smoke
```

## 5. Ожидаемый вывод

### scripts/smoke_embeddings.py

```
EMBEDDING_PROVIDER=local
EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
ENABLED=True
VECTOR_DIM=384
OK: model loaded, vector produced, length check passed
```

Код выхода: 0.

### pytest -q

```
153 passed, 1 warning in ...s
```

### pytest -q -m smoke

```
71 passed, 82 deselected, 1 warning in ...s
```

### Старт бота (фрагмент логов)

При включённом AI в логах должна быть строка:

```
active_embedding_backend: provider=local model=sentence-transformers/all-MiniLM-L6-v2 enabled=True
```

(и ранее одна строка из `embeddings_service`: `embedding_backend: provider=local model=... enabled=True`).

## Обязательные проверки (чек-лист)

- [x] Локальная модель загружается — `scripts/smoke_embeddings.py`, тест `test_local_embedding_smoke`.
- [x] Длина вектора выводится/проверяется — скрипт печатает `VECTOR_DIM=384`, тесты проверяют `len(vec) == 384`.
- [x] Smoke семантического поиска — тест `test_semantic_retrieval_canonical_path`.
- [x] `pytest -q` проходит — все 153 теста зелёные.
