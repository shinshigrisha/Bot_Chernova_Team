# Система событий и webhook automation

Единый набор событий для n8n и внутренней автоматизации. Проактивный слой описан в [PROACTIVE_LAYER.md](PROACTIVE_LAYER.md).

## События (events)

| Событие                 | Направление   | Описание                                    | Webhook: тело ответа                          |
|-------------------------|---------------|---------------------------------------------|-----------------------------------------------|
| `user_question`         | in            | Вопрос курьера → AI-куратор                 | Ответ куратора (text, route, intent, …)      |
| `courier_question`      | in            | То же (legacy)                              | То же                                         |
| `poll_closed`           | in            | Закрытие опроса                             | `ok`, `event`, `user_id`, `text` (если есть)   |
| `courier_warning`       | in            | Предупреждение по курьеру                  | То же                                         |
| `faq_added`             | in/out        | Добавлен FAQ (админка); в приложении → пересборка индекса | То же                                         |
| `delivery_risk_eval`    | in            | Оценка риска доставки (тело = RiskInput)    | `hint`, `severity`, `escalate`, `courier_tg_id`; при high risk эмит `high_risk_detected` |
| `verification.pending`  | out (in-app)  | Пользователь переведён в pending после заявки| —                                             |
| `high_risk_detected`    | out (in-app)  | Обнаружен высокий риск доставки             | —                                             |
| `similar_case_shown`    | out (in-app)  | Показан ответ по похожему кейсу (semantic_case) | —                                          |

Для `user_question` и `courier_question` в теле запроса обязательны `user_id` и `text`; запрос уходит в AI-куратора. Для `delivery_risk_eval` тело должно содержать поля RiskInput (order_id, minutes_to_deadline, eta_minutes и т.д.), опционально `courier_tg_id`.

## Webhook

- **Маршрут:** `POST /automation/event`
- **Включение:** `AUTOMATION_HTTP_PORT=8080` (0 = выключено)
- **Тело запроса (JSON):** `event`, `user_id` (для AI-событий), `text` (для AI-событий), при необходимости — свои поля.

Пример:

```json
{
  "event": "user_question",
  "user_id": 12345,
  "text": "как открыть смену"
}
```

## Event bus (в приложении)

В процессе работы бота доступен `EventBus` (`dp["event_bus"]`). Подписка: `event_bus.subscribe(handler)`. Эмит: `await event_bus.emit("faq_added", {"faq_id": 1, ...})`.

Событие `faq_added` эмитируется автоматически после успешного добавления FAQ через `/ai_add_faq`; подписчик проактивного слоя запускает пересборку эмбеддингов FAQ в фоне. События `verification.pending`, `high_risk_detected`, `similar_case_shown` эмитируются из хендлеров и API (см. PROACTIVE_LAYER.md).
