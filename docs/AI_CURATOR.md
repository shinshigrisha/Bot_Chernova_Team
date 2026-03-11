# AI-куратор

## 1) Что такое AI-куратор (regulation-first RAG)

AI-куратор — электронный куратор для курьеров: распознаёт типовые ситуации доставки и отвечает по регламенту. Ответы строятся по принципу **regulation-first**: правила, FAQ и кейсы доминируют; LLM только форматирует и поясняет, не придумывая операционных правил.

**Порядок маршрутизации:**
1. **must_match** — жёсткие кейсы из `core_policy.json` (яйца разбиты, недозвон, недовоз, опоздание, АКБ дымит).
2. **case_engine** — типовые интенты с фиксированными шагами (damaged_goods, contact_customer, missing_items, late_delivery, battery_fire, payment_terminal и др.).
3. **FAQ** — поиск по ключевым словам и семантика (keyword → semantic → hybrid).
4. **ML case memory (semantic_case)** — семантическое совпадение по `ml_cases.jsonl` (при наличии кэша эмбеддингов).
5. **llm_reason** — только оформление/пояснение по переданному контексту; при отсутствии доказательств — один уточняющий вопрос.
6. **fallback** — только если нет ни одного сильного совпадения и LLM недоступен или не ответил.

**Реализация:** `src/core/services/ai/` (AICourierService, ProviderRouter, CaseEngine, IntentEngine, EmbeddingsService, CaseClassifier); политика и промпты — `data/ai/`; единственный репозиторий FAQ — `src/infra/db/repositories/faq_repo.py`.

## 2) RAG-формат ответа (обязательные блоки)

Все операционные ответы приводятся к единому виду:

- **Ситуация:** кратко, что произошло (или **Критично:** для опасных кейсов).
- **Что делать сейчас:** нумерованные шаги (1) … 2) …).
- **Когда писать куратору:** при каких условиях эскалировать.

Для опасных кейсов (АКБ, дым, пожар) используется срочный формат: «Критично / Действия / Немедленно сообщи куратору».

Источники для заполнения блоков: must_match (response/actions), case_engine (шаги по интенту), FAQ (answer), ML case (decision/explanation). LLM не изобретает новые правила — только перелагает переданные факты в этот формат.

## 3) Провайдеры (OpenAI/DeepSeek/Groq), env-переменные

Поддерживаются три провайдера:

- OpenAI (`OPENAI_API_KEY`, `OPENAI_MODEL`);
- DeepSeek через OpenAI SDK (`DEEPSEEK_API_KEY`, `DEEPSEEK_BASE_URL`, `DEEPSEEK_MODEL`);
- Groq (`GROQ_API_KEY`, `GROQ_MODEL`).

Управляющие переменные:

- `AI_ENABLED` — общий флаг включения AI;
- `AI_PROVIDER_ORDER_CHAT` — порядок провайдеров для обычного ответа;
- `AI_PROVIDER_ORDER_REASON` — порядок для reasoning-режима.

Пример (из `.env.example`):

```env
AI_ENABLED=false
GROQ_API_KEY=...
GROQ_MODEL=llama-3.1-70b-versatile
DEEPSEEK_API_KEY=...
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_MODEL=deepseek-chat
OPENAI_API_KEY=...
OPENAI_MODEL=gpt-4o-mini
AI_PROVIDER_ORDER_CHAT=groq,deepseek,openai
AI_PROVIDER_ORDER_REASON=openai,deepseek,groq
```

## 4) ML case memory и семантический поиск

- **ml_cases.jsonl** — кейсы с полями: id, input, label, decision, explanation. Используются для лексического (токены) и при наличии кэша — семантического поиска.
- **ml_cases_embeddings.json** — кэш эмбеддингов по полю `input` (создаётся скриптом `python scripts/rebuild_case_embeddings.py`). Без этого файла семантический маршрут `semantic_case` не используется.
- Семантический поиск по FAQ: колонка `embedding_vector` в таблице `faq_ai`, пересборка — `python scripts/rebuild_faq_embeddings.py`. Подробнее: [AI_FAQ_SEARCH.md](AI_FAQ_SEARCH.md).

## 4.1) Проактивная оценка риска доставки (delivery_risk)

AI-сервис вызывает **risk_engine** и **recommendation_engine** (`src/core/services/risk/`), чтобы выдавать рекомендации по рискам доставки (опоздание, недовоз, контакт с клиентом, хрупкий груз, оплата, возврат, перегрузка курьера). Ответ формируется в том же RAG-формате: Ситуация / Что делать сейчас / Когда писать куратору.

- **Команда в боте:** `/risk` — выводит рекомендацию по демо-контексту (риск опоздания). В дальнейшем контекст можно передавать из приложения курьера (order_id, ETA, дедлайн и т.д.).
- **Точка входа в коде:** `AICourierService.get_risk_recommendation(risk_input: RiskInput)` и `AIFacade.get_risk_recommendation(risk_input)`; маршрут ответа — `delivery_risk`.

## 5) Как добавить FAQ (через админ-команды)

Команда доступна только администратору из `ADMIN_USER_ID` (env):

- `/ai_add_faq`

Дальше бот ведет по FSM-шагам:

1. `question`
2. `answer`
3. `category` (или `-`)
4. `tag` (или `-`)
5. `keywords` через запятую (или `-`)

После последнего шага запись сохраняется в БД.  
Для поиска используйте:

- `/ai_search_faq <текст>` — вывод top-5 совпадений (`question` + короткий `answer`).

## 6) Как обновлять policy

Без рестарта бота:

- `/ai_policy_reload`

Команда вызывает `reload_policy()` в `AICourierService` и перечитывает:

- `data/ai/core_policy.json`
- `data/ai/intent_tags.json`
- `data/ai/prompts/clarify_questions.json`
- `data/ai/prompts/system_prompt.md`
- `data/ai/prompts/style_guide.md`

## 7) Типовые проблемы

- **Нет ответа / пришла эскалация**
  - Низкая уверенность по FAQ;
  - кейс помечен как рискованный policy-правилами;
  - не найден надежный маршрут для автоответа.

- **Пустая база FAQ**
  - Поиск не находит фактов, AI чаще уходит в общий fallback/эскалацию;
  - проверь сидирование FAQ и ручное добавление через `/ai_add_faq`.

- **Нет ключей API**
  - LLM-провайдеры не активируются;
  - сервис продолжает работать через FAQ/fallback, но без генерации LLM.

- **Timeouts**
  - Временные сетевые проблемы или задержки API;
  - провайдер может не ответить, роутер переключится на следующий по приоритету;
  - при недоступности провайдеров остается fallback-ответ.

## 8) Smoke-test: как локально прогнать тестовый вопрос без Telegram

### Вариант A: готовый smoke по golden cases

1. Убедитесь, что доступны:
   - `DATABASE_URL`
   - файл `data/ai/golden_cases.jsonl`
2. Запустите:

```bash
python scripts/smoke_ai.py
```

Ожидаемый итог в консоли:

- `SMOKE: X/Y passed`

### Вариант B: единичная локальная проверка

Можно временно добавить кейс в `data/ai/golden_cases.jsonl` с одним `input` и нужными проверками `must_contain_any`/`must_not_contain_any`, затем запустить тот же `python scripts/smoke_ai.py`.
