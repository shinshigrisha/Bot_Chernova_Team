# AI-куратор

## 1) Что такое AI-куратор (regulation-first RAG)

AI-куратор — электронный куратор для курьеров: распознаёт типовые ситуации доставки и отвечает по регламенту. Ответы строятся по принципу **regulation-first**: правила, FAQ и кейсы доминируют; LLM только форматирует и поясняет, не придумывая операционных правил.

**Ответ не идёт сразу в LLM.** Сначала выполняется каскад решений (см. ниже); LLM вызывается только на шаге 7, если предыдущие шаги не дали уверенного ответа.

## 2) Каскад решений (обязательный порядок)

Порядок проверок перед формированием ответа:

| # | Этап | Описание |
|---|------|----------|
| 1 | **Access check** | Проверка доступа к AI-куратору (роль/статус пользователя). Выполняется на стороне вызывающего (handler, middleware) до вызова `answer_user` / `get_answer`. |
| 2 | **Must-match cases** | Жёсткие кейсы из `core_policy.json` (яйца разбиты, недозвон, недовоз, опоздание, АКБ дымит). При совпадении — фиксированный ответ без LLM. |
| 3 | **Rules** | Правила и типовые шаги (case_engine по интенту: damaged_goods, contact_customer, missing_items, late_delivery, battery_fire и др.). Ответ по регламенту, без LLM. |
| 4 | **Intent detection** | Определение интента запроса (keyword + при необходимости catalog/LLM). Результат используется в шагах 2–3 и далее. |
| 5 | **Semantic FAQ / RAG** | Поиск по базе знаний: keyword → semantic → hybrid. При сильном совпадении — ответ из FAQ/RAG, без генерации LLM. |
| 6 | **ML classifier** | Семантическое совпадение по `ml_cases.jsonl` (case memory). При сильном совпадении — ответ по решению классификатора, без LLM. |
| 7 | **LLM reasoning** | Только если шаги 1–6 не дали уверенного ответа. LLM лишь оформляет переданный контекст (факты из правил/FAQ/case); не придумывает регламентов. |
| 8 | **Escalation / fallback** | Если LLM недоступен или не ответил — фиксированный fallback и при необходимости эскалация куратору. |

Реализация каскада: `AICourierService.get_answer()` (шаги 2–8); шаг 1 — обязанность handler'а/фасада при входе в AI-чат.

**Порядок маршрутизации (источники ответа):**
1. **must_match** — жёсткие кейсы из `core_policy.json`.
2. **case_engine** — типовые интенты с фиксированными шагами.
3. **FAQ** — поиск по ключевым словам и семантика (keyword → semantic → hybrid).
4. **ML case memory (semantic_case)** — семантическое совпадение по `ml_cases.jsonl`.
5. **llm_reason** — только оформление по переданному контексту; при отсутствии доказательств — один уточняющий вопрос.
6. **fallback** — только если нет сильного совпадения и LLM недоступен или не ответил.

**Реализация:** `src/core/services/ai/` (AICourierService, ProviderRouter, CaseEngine, IntentEngine, EmbeddingsService, CaseClassifier); политика и промпты — `data/ai/`; единственный репозиторий FAQ — `src/infra/db/repositories/faq_repo.py`.

**Единственный вход в AI:** все вызовы LLM — только через **AIFacade**. Режимов три (см. [AI_MODES.md](AI_MODES.md)): **Courier assistant** (`answer_user`, `proactive_hint`), **Admin copilot** (`answer_admin`), **Analytics assistant** (`analyze_csv`). Handlers, admin и API не вызывают AICourierService, ProviderRouter, RAGService, AnalyticsAssistant напрямую.

## 3) RAG-формат ответа (обязательные блоки)

Все операционные ответы приводятся к единому виду:

- **Ситуация:** кратко, что произошло (или **Критично:** для опасных кейсов).
- **Что делать сейчас:** нумерованные шаги (1) … 2) …).
- **Когда писать куратору:** при каких условиях эскалировать.

Для опасных кейсов (АКБ, дым, пожар) используется срочный формат: «Критично / Действия / Немедленно сообщи куратору».

Источники для заполнения блоков: must_match (response/actions), case_engine (шаги по интенту), FAQ (answer), ML case (decision/explanation). LLM не изобретает новые правила — только перелагает переданные факты в этот формат.

## 4) Провайдеры (OpenAI/DeepSeek/Groq), env-переменные

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

## 5) ML case memory и семантический поиск

- **ml_cases.jsonl** — кейсы с полями: id, input, label, decision, explanation. Используются для лексического (токены) и при наличии кэша — семантического поиска.
- **ml_cases_embeddings.json** — кэш эмбеддингов по полю `input` (создаётся скриптом `python scripts/rebuild_case_embeddings.py`). Без этого файла семантический маршрут `semantic_case` не используется.
- Семантический поиск по FAQ: колонка `embedding_vector` в таблице `faq_ai`, пересборка — `python scripts/rebuild_faq_embeddings.py`. Подробнее: [AI_FAQ_SEARCH.md](AI_FAQ_SEARCH.md).

## 5.1) Проактивная оценка риска доставки (delivery_risk)

AI-сервис вызывает **risk_engine** и **recommendation_engine** (`src/core/services/risk/`), чтобы выдавать рекомендации по рискам доставки (опоздание, недовоз, контакт с клиентом, хрупкий груз, оплата, возврат, перегрузка курьера). Ответ формируется в том же RAG-формате: Ситуация / Что делать сейчас / Когда писать куратору.

- **Команда в боте:** `/risk` — выводит рекомендацию по демо-контексту (риск опоздания). В дальнейшем контекст можно передавать из приложения курьера (order_id, ETA, дедлайн и т.д.).
- **Точка входа в коде:** `AICourierService.get_risk_recommendation(risk_input: RiskInput)` и `AIFacade.get_risk_recommendation(risk_input)`; маршрут ответа — `delivery_risk`.

## 5.2) Explainability (логирование каждого AI-ответа)

Каждый AI-ответ логируется в едином формате для аудита и разбора маршрутизации. Событие: `ai_explainability`. Поля:

| Поле | Описание |
|------|----------|
| `route` | Маршрут ответа: `must_match`, `case_engine`, `faq` / `semantic_faq`, `semantic_case`, `llm_reason`, `fallback`, `safety_blocker` и т.д. |
| `intent` | Определённый интент (например `battery_fire`, `contact_customer`) или `unknown`. |
| `confidence` | Уверенность 0.0–1.0. |
| `evidence` | Список строк-идентификаторов доказательств (например `["must_match:battery_fire_smoke"]`, `["faq:123"]`). |
| `user_id` | ID пользователя (курьер или админ). |
| `role` | Роль вызывающего: `courier` или `admin`. |

Пример записи в логе (structlog JSON):

```json
{
  "event": "ai_explainability",
  "route": "must_match",
  "intent": "battery_fire",
  "confidence": 0.97,
  "evidence": ["must_match:battery_fire_smoke"],
  "user_id": 123,
  "role": "courier"
}
```

Реализация: `AICourierService._log_explainability()` вызывается перед каждым возвратом из `get_answer()`; роль передаётся из фасада (`answer_user` → `courier`, `answer_admin` → `admin`).

## 6) Как добавить FAQ (через админ-команды)

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

## 7) Как обновлять policy

Без рестарта бота:

- `/ai_policy_reload`

Команда вызывает `reload_policy()` в `AICourierService` и перечитывает:

- `data/ai/core_policy.json`
- `data/ai/intent_tags.json`
- `data/ai/prompts/clarify_questions.json`
- `data/ai/prompts/system_prompt.md`
- `data/ai/prompts/style_guide.md`

## 8) Типовые проблемы

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

## 9) Smoke-test: как локально прогнать тестовый вопрос без Telegram

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
