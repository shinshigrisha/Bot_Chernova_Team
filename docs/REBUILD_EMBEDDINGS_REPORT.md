# Отчёт: пересборка эмбеддингов FAQ и ML-кейсов (локальный MiniLM)

## 1. Текущий поток пересборки

### FAQ (--faq)
- **Вход:** записи из БД `faq_ai` (question, answer).
- **Бэкенд эмбеддингов:** канонический `EmbeddingsService()` из `src.core.services.ai.embeddings_service`. Провайдер задаётся конфигом: `EMBEDDING_PROVIDER=local` (по умолчанию) — SentenceTransformer (MiniLM), иначе OpenAI.
- **Текст для эмбеддинга:** `EmbeddingsService.build_faq_text(question, answer)` → `"Вопрос: ...\nОтвет: ..."`.
- **Куда пишется:** PostgreSQL, таблица `faq_ai`: колонки `embedding` (jsonb/текст) и `embedding_vector` (vector(384), pgvector). Коммит в одной транзакции.
- **Вызов:** `rebuild_faq_embeddings_async(session_factory, embeddings_service=None)` в `scripts/rebuild_embeddings.py`; при `embeddings_service=None` создаётся новый сервис и по завершении вызывается `emb.close()`.

### ML-кейсы (--cases)
- **Вход:** файл `data/ai/ml_cases.jsonl` (по одной JSONL-строке на кейс, поля: id, input, label, decision, explanation).
- **Бэкенд эмбеддингов:** тот же `EmbeddingsService()`; эмбеддинг считается по полю `input` каждого кейса.
- **Куда пишется:** файл `data/ai/ml_cases_embeddings.json` — JSON-массив объектов с полями id, input, label, decision, explanation, embedding (массив float).
- **Вызов:** `scripts/rebuild_embeddings.py` запускает в subprocess `scripts/rebuild_case_embeddings.py` (cwd=ROOT).

Оба потока используют один и тот же канонический бэкенд; при `EMBEDDING_PROVIDER=local` внешний API для эмбеддингов не нужен.

---

## 2. Что изменено

| Файл | Изменения |
|------|-----------|
| **src/core/services/ai/faq_embeddings_rebuild.py** | Во все возвращаемые словари добавлено поле `"output": "DB (pgvector, faq_ai.embedding_vector)"` для единообразного логирования места записи. |
| **scripts/rebuild_embeddings.py** | После успешной пересборки FAQ выводится строка `output: <result["output"]>`. Добавлен `flush=True` к сообщениям "Rebuilding FAQ/ML case embeddings..." для предсказуемого порядка вывода. |
| **scripts/rebuild_case_embeddings.py** | Пути к файлам переведены на ROOT: `ML_CASES_PATH = ROOT / "data" / "ai" / "ml_cases.jsonl"`, `ML_CASES_EMBEDDINGS_PATH = ROOT / "data" / "ai" / "ml_cases_embeddings.json"` (стабильные пути при любом CWD). Сообщение при отключённых эмбеддингах заменено на: "Embeddings disabled (set EMBEDDING_PROVIDER=local for local MiniLM, or configure OpenAI API key for openai provider)." Логи приведены к формату: одна строка `total: N, updated: N, skipped: N` и одна строка `output: <абсолютный путь к ml_cases_embeddings.json>`. В docstring указано, что по умолчанию используется локальный MiniLM и внешний API не требуется. |

---

## 3. Риски

- **FAQ:** для пересборки нужна работающая БД (PostgreSQL с pgvector). При неверном/недоступном `DATABASE_URL` будет ошибка соединения; подсказка в stderr уже выводится.
- **ML-кейсы:** при первом запуске с `EMBEDDING_PROVIDER=local` загружается модель SentenceTransformer (сеть/кэш Hugging Face); возможны предупреждения HF (например, про HF_TOKEN). Файл `data/ai/ml_cases.jsonl` должен существовать и содержать валидные строки JSON с полями `id` и `input`.
- **Единый бэкенд:** и FAQ, и кейсы используют один и тот же `EmbeddingsService()`; размерность (384 для MiniLM) должна совпадать с миграциями и использованием в поиске (pgvector vector(384), семантический поиск по кейсам).

---

## 4. Итоговый diff по файлам

### src/core/services/ai/faq_embeddings_rebuild.py
- В возврат при `emb.enabled == False` добавлено `"output": "DB (pgvector, faq_ai.embedding_vector)"`.
- При пустом списке FAQ возврат дополнен полем `"output": "DB (pgvector, faq_ai.embedding_vector)"`.
- Успешный возврат дополнен полем `"output": "DB (pgvector, faq_ai.embedding_vector)"`.

### scripts/rebuild_embeddings.py
- Печать "Rebuilding FAQ embeddings..." с `flush=True`.
- После успешного FAQ: `if result.get("output"): print(f"output: {result['output']}")`.
- Печать "Rebuilding ML case embeddings..." с `flush=True`.

### scripts/rebuild_case_embeddings.py
- Docstring: уточнено про локальный MiniLM по умолчанию и отсутствие необходимости во внешнем API.
- `ML_CASES_PATH` и `ML_CASES_EMBEDDINGS_PATH` заданы как `ROOT / "data" / "ai" / ...`.
- Сообщение при `not service.enabled` заменено на текст про `EMBEDDING_PROVIDER=local` и OpenAI API key, вывод в stderr.
- В конце: `print(f"total: {total}, updated: {updated}, skipped: {skipped}")` и `print(f"output: {output_path}")` с абсолютным путём.

---

## 5. Команды для запуска

Из корня репозитория:

```bash
# Только FAQ (нужны DATABASE_URL и запущенный PostgreSQL с pgvector)
python scripts/rebuild_embeddings.py --faq

# Только ML-кейсы (внешний API не нужен при EMBEDDING_PROVIDER=local)
python scripts/rebuild_embeddings.py --cases

# Оба
python scripts/rebuild_embeddings.py --all
# или по умолчанию (без флагов)
python scripts/rebuild_embeddings.py
```

С хоста при поднятом compose и проброшенном порте 5432:

```bash
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/delivery_assistant python scripts/rebuild_embeddings.py --faq
```

Из контейнера:

```bash
docker compose run --rm bot python scripts/rebuild_embeddings.py --faq
docker compose run --rm bot python scripts/rebuild_embeddings.py --cases
```

---

## 6. Примеры ожидаемого вывода

### Успешный запуск только ML-кейсов

```
Rebuilding ML case embeddings...
Warning: You are sending unauthenticated requests to the HF Hub. ...
Loading weights: 100%|██████████| 103/103 [00:00<00:00, ...]
total: 90, updated: 90, skipped: 0
output: /Users/.../Bot_Chernova_Team/data/ai/ml_cases_embeddings.json
```

### Успешный запуск только FAQ (при доступной БД и наличии записей в faq_ai)

```
Rebuilding FAQ embeddings...
FAQ: total=12, updated=12, skipped=0
output: DB (pgvector, faq_ai.embedding_vector)
```

### FAQ при недоступной БД

```
Rebuilding FAQ embeddings...
FAQ rebuild error: connection was closed in the middle of operation
Hint: check DATABASE_URL and that PostgreSQL is running.
```

### ML-кейсы при отключённых эмбеддингах (например, openai без API key)

```
Rebuilding ML case embeddings...
Embeddings disabled (set EMBEDDING_PROVIDER=local for local MiniLM, or configure OpenAI API key for openai provider).
```

---

## Проверка

- Выполнено: `python scripts/rebuild_embeddings.py --cases` — успех (90 кейсов, 90 updated, 0 skipped, файл записан).
- Выполнено: `python scripts/rebuild_embeddings.py --faq` — ожидаемая ошибка при отсутствии доступной БД (connection closed); логи и подсказка выводятся корректно.
