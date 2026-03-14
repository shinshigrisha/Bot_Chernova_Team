# Стабилизация AI-слоя — отчёт

**Статус:** отчёт о выполненной стабилизации; актуальное описание AI — [ARCHITECTURE_AI_LAYER.md](ARCHITECTURE_AI_LAYER.md). Минимальные изменения: explainability-поля, пометки deprecated/legacy, обновление документации. Рантайм и пайплайн не переписывались.

---

## 1. What is currently unstable

- **Explainability:** В контракте не было полей `fallback_reason` и `escalation_reason`; в логах нельзя было однозначно понять причину fallback или эскалации.
- **Дубликаты/legacy:** Модули `intent_ml_engine.py` и `semantic_search.py` не используются в рантайме, но не помечены; возможны случайные импорты. В `app/infrastructure/openai/responses.py` — прямой вызов провайдера без пометки «вне канонического пути».
- **Документация:** В ARCHITECTURE_AI_LAYER не были явно зафиксированы целевой поток (normalize → must_match → … → explainability), полный набор route classes и правило «menu/access/verification не вызывают LLM».

Стабильно и не менялось: AIFacade как единая точка входа, разделение Curator / Analyst, прохождение всех completion через ProviderRouter, порядок шагов пайплайна, загрузка политики в AICourierService/RAGService.

---

## 2. Canonical AI path to keep

- **Entrypoint:** AIFacade (`src/core/services/ai/ai_facade.py`) — answer_user, answer_admin, proactive_hint, analyze_csv, reload_policy, get_provider_names.
- **Curator flow:** input → normalize (question) → safety_blocker → intent detection → must_match → case_engine (deterministic rules) → FAQ lexical → semantic retrieval → ML case hints → policy/route decision → generation (_format_with_llm) → validation (RAG format wrap) → explainability (_log_explainability, AICourierResult).
- **Decision:** IntentEngine (rules + catalog + IntentMLClassifier + опционально _detect_with_llm); выбор ветки в AICourierService.
- **Retrieval:** RAGService.build_context; FAQRepository; CaseClassifier; get_embedding_service().
- **Generation:** ProviderRouter.complete(); провайдеры только через роутер.
- **Validation:** Пороги и обёртка ответа в RAG-формат внутри AICourierService (отдельного модуля нет).
- **Explainability:** AICourierResult (route, source, confidence, evidence, fallback_reason, escalation_reason); _log_explainability с теми же полями.
- **Route classes:** AirRouteClass (no_llm, fast_chat, reasoning, analytics, fallback) в ai_modes.py; ROUTE_TO_CLASS, route_class(route).
- **Analyst (отдельный контур):** AIFacade.analyze_csv → AnalyticsAssistant.build_report; mode="analysis" в ProviderRouter; не участвует в пайплайне ответа курьеру.

---

## 3. Files to modify minimally

| Файл | Изменения |
|------|-----------|
| `src/core/services/ai/ai_courier_service.py` | AICourierResult: добавлены поля fallback_reason, escalation_reason; во все конструкторы AICourierResult передаются эти поля; _log_explainability логирует fallback_reason и escalation_reason. |
| `src/core/services/ai/intent_ml_engine.py` | В начало файла добавлен docstring: DEPRECATED, canonical — IntentEngine + IntentMLClassifier. |
| `src/core/services/ai/semantic_search.py` | В начало файла добавлен docstring: DEPRECATED, canonical — RAGService + FAQRepository + get_embedding_service. |
| `app/infrastructure/openai/responses.py` | В начало файла добавлен docstring: LEGACY, не в рантайме, прямой вызов провайдера; из src использовать только AIFacade/ProviderRouter. |
| `docs/ARCHITECTURE_AI_LAYER.md` | Описан целевой поток (curator), добавлены разделы про route classes, fallback_reason/escalation_reason, разделение Curator/Analyst, правило про menu/access/verification. |

---

## 4. Risks

- **Обратная совместимость:** Новые поля AICourierResult имеют значения по умолчанию (пустая строка); существующие вызовы и тесты без этих полей остаются валидными. Риск низкий.
- **Логи:** Добавление полей в лог не меняет формат существующих полей; потребители логов могут игнорировать новые ключи. Риск низкий.
- **Deprecated-модули:** Только пометки в docstring; код не удалялся. При будущем удалении нужно убедиться, что ни тесты, ни скрипты их не импортируют. Риск низкий.
- **app/:** Только комментарий; рантайм по-прежнему не загружает app. Риск отсутствует.

---

## 5. Final diff by files

**src/core/services/ai/ai_courier_service.py**

- В `AICourierResult` добавлены поля: `fallback_reason: str = field(default="")`, `escalation_reason: str = field(default="")`.
- В каждом месте создания `AICourierResult` добавлены аргументы `fallback_reason=...`, `escalation_reason=...` (для fallback — `fallback_reason="no_strong_match_or_llm_unavailable"`, для эскалаций — осмысленные строки: `must_match_policy`, `case_engine_always_escalate`, `high_risk_severity`, `high_risk_after_llm`, `high_risk_escalate` и т.д.).
- В `_log_explainability` в вызов `log.info("ai_explainability", ...)` добавлены ключи `fallback_reason=result.fallback_reason or ""`, `escalation_reason=result.escalation_reason or ""`.

**src/core/services/ai/intent_ml_engine.py**

- В начало файла (перед `from __future__`) добавлен однострочный module docstring: DEPRECATED, canonical — IntentEngine + IntentMLClassifier.

**src/core/services/ai/semantic_search.py**

- В начало файла добавлен module docstring: DEPRECATED, canonical — RAGService + FAQRepository + get_embedding_service.

**app/infrastructure/openai/responses.py**

- В начало файла добавлен module docstring: LEGACY, не в рантайме, прямой вызов; из src только AIFacade/ProviderRouter.

**docs/ARCHITECTURE_AI_LAYER.md**

- Заголовок дополнен: «(stable canonical architecture)»; добавлено правило: menu/access/verification/navigation не вызывают LLM.
- Добавлен раздел «Целевой канонический поток (curator)»: input → normalize → must_match → … → explainability.
- Добавлен раздел «Классы маршрутов (route classes)»: AirRouteClass, ROUTE_TO_CLASS, route_class(route).
- В разделе «Точки explainability» добавлены поля fallback_reason, escalation_reason и их описание в логах.
- Добавлен раздел «Разделение контуров»: Curator vs Analyst.
- В разделе «Файлы» добавлены ссылки на ai_facade и ai_modes.

---

## 6. Validation commands

```bash
python -m compileall src
pytest -q
pytest -q
pytest -q
```

Опционально:

```bash
grep -r "AsyncOpenAI\|AsyncGroq\|\.complete\(" src --include="*.py" | grep -v provider_router | grep -v providers/
grep -r "IntentMLEngine\|intent_ml_engine\|semantic_search" src --include="*.py"
grep -r "analyze_csv\|answer_user\|answer_admin" src/bot src/api --include="*.py"
```

(Ожидается: прямых вызовов провайдеров вне providers/ и router нет; импортов deprecated-модулей в рабочем коде нет; вход в AI только через фасад/хендлеры.)

---

## 7. Manual Telegram test checklist

- [ ] `/start` — приветствие, меню без вызова AI.
- [ ] Вход в раздел верификации (если доступен) — без вызова LLM.
- [ ] Вход в админ-меню (если есть права) — без вызова LLM при открытии меню.
- [ ] Открытие статуса AI / списка провайдеров в админке — без вызова LLM.
- [ ] Отправка текста в AI-куратор (чат курьера) — ответ приходит; в логах есть `ai_explainability` с полями route, source, confidence, evidence, fallback_reason, escalation_reason.
- [ ] Вопрос, который закрывается must_match или case_engine — route в ответе и в логе no_llm-типа (safety_blocker, must_match, case_engine, faq, semantic_faq, semantic_case).
- [ ] Вопрос, ведущий к fallback — в логе fallback_reason заполнен (например no_strong_match_or_llm_unavailable).
- [ ] Сценарий с эскалацией (например high_risk) — в логе escalation_reason не пустой.
- [ ] POST /automation/event с event=user_question — ответ через AIFacade; в логах те же explainability-поля.
- [ ] POST /automation/event с event=delivery_risk_eval — ответ без LLM (risk engine); route=delivery_risk.
