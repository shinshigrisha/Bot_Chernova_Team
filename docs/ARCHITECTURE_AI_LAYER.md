# AI Layer: пайплайн и explainability

Единственная точка входа в AI-слой — **AIFacade** (`src/core/services/ai/ai_facade.py`). Реализация пайплайна ответа курьеру/админу — в **AICourierService.get_answer** (`src/core/services/ai/ai_courier_service.py`).

## Порядок пайплайна (canonical route order)

Ответ формируется по каскаду; переход к следующему шагу только если текущий не дал ответа:

1. **safety_blocker** — правила безопасности/блокировки (расширяемо; по умолчанию no-op).
2. **must_match** — жёсткие кейсы из `core_policy.json` (must_match_cases); ответ без вызова LLM.
3. **case_engine** — правила по интенту (регламент, структурированный FAQ).
4. **faq / semantic_faq** — поиск по FAQ: keyword → semantic → hybrid (RAG).
5. **semantic_case** — ML intent / case ranking (case memory).
6. **llm_reason** — RAG + вызов LLM (ProviderRouter).
7. **fallback** — эскалация или фиксированный fallback-текст, если LLM недоступен или нет уверенного ответа.

Intent detection выполняется в начале и используется на шагах 2–6.

## Метки источника (source) для explainability

В `AICourierResult` и логах используются канонические метки (константы в `ai_courier_service.py`):

| source | Описание |
|--------|----------|
| `safety_blocker` | Ответ из правил безопасности |
| `must_match` | Ответ из must_match_cases (core_policy) |
| `structured_faq` | Ответ из структурированного FAQ / case_engine |
| `semantic_retrieval` | Ответ из семантического поиска по FAQ |
| `ml_intent_case` | Ответ из ML intent / case memory |
| `llm_synthesis` | Ответ сгенерирован LLM (RAG + generation) |
| `fallback` | Ответ из fallback (эскалация / generic) |
| `delivery_risk` | Проактивная рекомендация по риску доставки |

## Точки explainability

- **AICourierResult**: поля `route`, `intent`, `confidence`, `evidence`, `source_ids`, `source` — каждый ответ несёт структурированные метаданные.
- **Логирование**: для каждого ответа вызывается `_log_explainability(user_id, result, role)` — пишется структурированный лог `ai_explainability` с полями route, intent, confidence, evidence, source_ids, source, user_id, role.
- **Логи** позволяют анализировать, откуда взялся ответ (какой шаг пайплайна, какие FAQ/кейсы использованы).

## Режимы AIFacade

- **Courier assistant**: `answer_user()`, `proactive_hint(risk_input)` — пайплайн выше.
- **Admin copilot**: `answer_admin()` — тот же пайплайн, роль `admin` для explainability.
- **Analytics assistant**: `analyze_csv()` — отдельный путь (AnalyticsAssistant), без этого пайплайна.

## Файлы

- Пайплайн и константы source: `src/core/services/ai/ai_courier_service.py`
- Политика и must_match_cases: `data/ai/core_policy.json`
- Режимы: `src/core/services/ai/ai_modes.py`
