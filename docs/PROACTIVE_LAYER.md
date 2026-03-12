# Проактивный слой AI-куратора

AI-куратор становится «умным», когда сам инициирует действия по событиям, а не только отвечает на вопросы.

## Четыре сценария

| Условие | Действие |
|--------|-----------|
| Риск просрочки высокий | Отправить подсказку курьеру |
| Похожий кейс жалобы найден | Показать памятку (ответ по semantic_case) |
| Пользователь pending | Уведомить админа |
| FAQ обновлён | Пересобрать индекс эмбеддингов |

## Реализация

### 1. Высокий риск просрочки → подсказка

- **Источник события:** внешняя система (n8n, приложение курьера) шлёт на `POST /automation/event` событие `delivery_risk_eval` с телом в формате `RiskInput` (order_id, minutes_to_deadline, eta_minutes, active_orders_count и т.д.), опционально `courier_tg_id`.
- **Обработка:** AI-куратор вызывает risk_engine + recommendation_engine, возвращает в ответе `hint`, `severity`, `escalate`. При `severity === "high"` или `escalate === true` эмитируется событие `high_risk_detected` в event_bus.
- **Действие:** n8n или другой подписчик по `high_risk_detected` или по ответу webhook отправляет подсказку курьеру (например, в Telegram по `courier_tg_id`).

Пример тела запроса:

```json
{
  "event": "delivery_risk_eval",
  "order_id": "ord-123",
  "courier_id": "c1",
  "minutes_to_deadline": 10,
  "eta_minutes": 25,
  "active_orders_count": 2,
  "courier_tg_id": 123456789
}
```

Ответ при высоком риске содержит `hint` (текст подсказки) и `escalate`; можно отправить `hint` курьеру.

### 2. Похожий кейс → памятка

- **Источник:** ответ AI-куратора по маршруту `semantic_case` (семантическое совпадение с ml_cases).
- **Обработка:** при возврате из `answer_user` с `route === "semantic_case"` хендлер эмитирует событие `similar_case_shown` с payload: `user_id`, `evidence`, `text_preview`, `intent`.
- **Действие:** ответ пользователю уже содержит памятку (текст ответа). Событие нужно для аналитики и опционально для дополнительного уведомления (например, «похожий кейс был у курьера X»).

### 3. Пользователь pending → уведомить админа

- **Источник:** после успешного `create_application_and_mark_pending` в сценарии верификации.
- **Обработка:** вызывается `notify_verification_pending(payload)` (n8n webhook) и эмитируется событие `verification.pending` в event_bus с теми же данными.
- **Действие:** n8n-воркфлоу по webhook шлёт уведомление в админский канал/чат. Подписчики event_bus также видят событие (логи, мониторинг).

### 4. FAQ обновлён → пересобрать индекс

- **Источник:** после добавления FAQ через `/ai_add_faq` эмитируется `faq_added` (payload: faq_id, question, answer, category, tag).
- **Обработка:** подписчик проактивного слоя (`register_proactive_handlers`) по событию `faq_added` запускает в фоне пересборку эмбеддингов FAQ (`rebuild_faq_embeddings_async`).
- **Действие:** семантический поиск по FAQ остаётся актуальным без ручного запуска `scripts/rebuild_faq_embeddings.py`.

## Модули

- **События:** `src/core/events.py` — `AutomationEvent.FAQ_ADDED`, `VERIFICATION_PENDING`, `HIGH_RISK_DETECTED`, `SIMILAR_CASE_SHOWN`; для webhook — `delivery_risk_eval`.
- **Проактивная подписка:** `src/core/proactive_layer.py` — `register_proactive_handlers(event_bus, session_factory)`; подписка на `faq_added` → пересборка индекса.
- **Пересборка FAQ:** `src/core/services/ai/faq_embeddings_rebuild.py` — `rebuild_faq_embeddings_async(session_factory, embeddings_service=None)`.
- **API:** `src/api/automation.py` — обработка `delivery_risk_eval`, эмит `high_risk_detected` при высоком риске.
- **Хендлеры:** верификация эмитирует `verification.pending`; ai_chat при `route === "semantic_case"` эмитирует `similar_case_shown`.

## Зависимости

- Для пересборки FAQ после `faq_added` нужен настроенный `OPENAI_API_KEY`; при его отсутствии пересборка логируется и завершается без ошибки.
- Для проактивной подсказки по риску нужен источник контекста доставки (n8n, приложение), вызывающий webhook с `delivery_risk_eval`.
