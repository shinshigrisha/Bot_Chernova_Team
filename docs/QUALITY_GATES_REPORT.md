# Quality gates: стабилизация тестов и регрессия AI

Цель: усилить качественные пороги и регрессионную уверенность для AI без изменения рантайм-логики.

---

## 1. Current test risks

| Риск | Описание | Мера |
|------|----------|------|
| **Дефолтный прогон мог бы вызвать external** | В pyproject не было addopts; при появлении тестов с маркером `external` они бы попали в обычный `pytest -q` и потребовали бы сеть/LLM. | Добавлен `addopts = "-m 'not external'"` — по умолчанию external не запускаются. |
| **Explainability-поля не проверялись** | После добавления `fallback_reason` и `escalation_reason` в AICourierResult контракт не был закреплён в тестах. | В test_ai_result_canonical_contract_metadata добавлены проверки fallback_reason и escalation_reason; отдельный тест на fallback и escalation. |
| **Fallback-сценарий без проверки причины** | test_ai_fallback_when_provider_unavailable проверял только route=fallback и наличие текста. | Добавлена проверка непустого fallback_reason. |
| **Нет явного smoke-набора для AI** | AI policy routes не были помечены smoke, хотя не требуют сети/LLM. | test_ai_policy_routes помечен pytestmark = pytest.mark.smoke. |
| **Локальная/сетевая зависимость** | test_semantic_retrieval_smoke вызывает generate_embedding("тест") — при наличии OPENAI_API_KEY возможен реальный запрос. | Тест допускает и None, и list; с addopts external по умолчанию не запускаются. Интеграционные тесты с БД (async_session) требуют поднятый Postgres — это ожидаемо для integration. |

---

## 2. Missing coverage

- **Explainability:** Покрыто: проверка полей fallback_reason и escalation_reason в контракте; fallback-кейс проверяет непустой fallback_reason; отдельный тест escalation_explainability для must_match (battery) при escalate=True.
- **Must_match / faq / case_engine / fallback / escalation:** Уже покрыты в test_ai_policy_routes (golden cases, strict_cases_prefer_must_match, test_ai_fallback_when_provider_unavailable, regulation_first_rag_regression_scenarios, known_courier_cases_regression, urgent_format_for_dangerous_situations). Добавлены только проверки explainability.
- **Semantic/retrieval route:** Покрыто в test_faq_semantic_search (БД) и test_semantic_retrieval_smoke (RAGKnowledgeContext, retrieval_stage). Отдельный тест «semantic route в get_answer» косвенно даётся через ai_service с _fake_search (keyword-style); полноценный semantic в get_answer требует БД с эмбеддингами — остаётся в integration (test_faq_semantic_search, test_rag_build_context).

Итого: явных провалов покрытия не восполняли; усилен контракт explainability и дефолтный безопасный прогон.

---

## 3. Minimal changes

| Файл | Изменение |
|------|-----------|
| **pyproject.toml** | addopts = "-m 'not external'"; в описании маркера smoke добавлено «AI policy routes». |
| **tests/test_ai_policy_routes.py** | Модульный docstring; pytestmark = pytest.mark.smoke; в test_ai_result_canonical_contract_metadata — проверки fallback_reason и escalation_reason; в test_ai_fallback_when_provider_unavailable — проверка непустого fallback_reason; новый test_escalation_explainability_for_high_risk_must_match. |
| **docs/TESTING.md** | Раздел «Команды (quality gates)»: compileall, три раза pytest -q; уточнено про addopts и отсутствие зависимости от сети/LLM; доп. команды (smoke, integration, все тесты). |

Рантайм-код не менялся.

---

## 4. Final diff by files

**pyproject.toml**
- В `[tool.pytest.ini_options]` добавлено `addopts = "-m 'not external'"`.
- В маркере smoke к описанию добавлено «, AI policy routes».

**tests/test_ai_policy_routes.py**
- В начале файла добавлен module docstring (AI regression pack, no network/LLM).
- Добавлено `pytestmark = pytest.mark.smoke`.
- test_ai_fallback_when_provider_unavailable: добавлены проверки `hasattr(result, "fallback_reason")`, `isinstance(result.fallback_reason, str)`, `result.fallback_reason != ""`.
- test_ai_result_canonical_contract_metadata: в docstring и в проверки добавлены fallback_reason и escalation_reason.
- Добавлен тест test_escalation_explainability_for_high_risk_must_match (battery, must_match, при escalate проверка escalation_reason).

**docs/TESTING.md**
- Уточнено про addopts и дефолтный безопасный прогон.
- Добавлен блок «Команды (quality gates)»: `python -m compileall src`, три раза `pytest -q`.
- Обновлены «Дополнительные команды» и формулировка про все тесты.

**docs/QUALITY_GATES_REPORT.md**
- Новый файл: отчёт по текущим рискам, покрытию, минимальным изменениям, диффам, командам и чеклисту.

---

## 5. Commands to run

```bash
python -m compileall src
pytest -q
pytest -q
pytest -q
```

Опционально:

```bash
pytest -q -m smoke
pytest -q -m integration
pytest tests/ -v
python scripts/smoke_ai.py
python scripts/smoke_provider_router.py
```

---

## 6. Manual Telegram smoke checklist

- [ ] `/start` — приветствие и меню без ошибок.
- [ ] Вход в AI-куратор (кнопка или команда) — при выключенном AI сообщение о недоступности; при включённом — ответ на типовой вопрос (например «не дозвонился до клиента»).
- [ ] Вопрос из must_match (например «АКБ дымит», «яйца разбиты») — ответ без задержки LLM, структура «Ситуация / Что делать / Куратор».
- [ ] Вопрос без совпадений (произвольный текст) — ответ fallback или от LLM без падения.
- [ ] `/admin` (для админа) — открытие меню; раздел AI — статус провайдеров, при необходимости reload policy.
- [ ] Верификация: подача заявки (guest) → уведомление админам; одобрение/отклонение — обновление статуса и уведомление пользователю.
- [ ] Логи: при ответе AI в логах есть запись ai_explainability с полями route, source, confidence, fallback_reason, escalation_reason (где применимо).
