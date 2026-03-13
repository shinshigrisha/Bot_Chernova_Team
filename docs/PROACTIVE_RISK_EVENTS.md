# Проактивный слой и риск: контракты событий

Единый контракт событий и риск-входов для event_bus, API automation и проактивных обработчиков.

## Event bus и источники событий

- **EventBus** (`src/core/events.py`): in-process шина. Подписчики регистрируются через `subscribe(handler)`. События эмитятся через `emit(event, payload)`.
- **Проактивные обработчики** регистрируются в `register_proactive_handlers(event_bus, session_factory, bot)` (`src/core/proactive_layer.py`).
- **API automation** (`src/api/automation.py`): POST `/automation/event` принимает внешние события (n8n и др.), валидирует по `parse_event()`, для AI-событий вызывает AIFacade, для `delivery_risk_eval` — proactive_hint и при высоком риске эмитирует `HIGH_RISK_DETECTED` в event_bus.

## AutomationEvent (канонические типы)

Определены в `src/core/events.py`:

| Событие | Описание | Кто эмитит | Подписчики |
|--------|----------|------------|------------|
| `user_question` | Вопрос пользователя (AI) | — | — |
| `poll_closed` | Опрос закрыт | — | — |
| `courier_warning` | Предупреждение курьеру | — | — |
| `faq_added` | Добавлен FAQ | admin (ai_admin) | proactive_layer: пересборка эмбеддингов FAQ |
| `verification.pending` | Новая заявка на верификацию | verification handler | proactive_layer: уведомление админам в Telegram |
| `high_risk_detected` | Выявлен высокий риск доставки | API automation (после proactive_hint) | опционально n8n/логи |
| `similar_case_shown` | Показан похожий кейс (AI) | ai_chat handler | опционально логи/n8n |

Дополнительно для webhook: `courier_question` (alias), `delivery_risk_eval` (внешний запрос на оценку риска).

## Контракты payload

- **verification.pending**: `tg_user_id`, `first_name`, `last_name`, `role`, `tt_number`, `phone` (и при необходимости `ds_code`). Используется в proactive_layer для текста уведомления админам.
- **faq_added**: `faq_id` (опционально). Используется для пересборки эмбеддингов.
- **high_risk_detected**: `courier_tg_id`, `risk_type`, `severity`, `hint`, `escalate`, `order_id`. Эмитируется из API automation при severity high или escalate после `proactive_hint(risk_input)`.
- **similar_case_shown**: payload по соглашению с потребителями (логи, n8n).

## RiskInput (контракт входа для оценки риска)

Определён в `src/core/services/risk/features.py`. Создание из JSON: `RiskInput.from_dict(body)`.

Поля:

- `order_id`, `courier_id` (str)
- `minutes_to_deadline`, `eta_minutes`, `active_orders_count` (int)
- `has_customer_comment` (bool)
- `address_flags`, `item_flags` (dict)
- `zone`, `tt`, `event_type` (str)

Используется в: `AIFacade.proactive_hint(risk_input)`, API automation для события `delivery_risk_eval`.

## Поток данных

1. **Верификация**: хендлер верификации после создания заявки вызывает `VerificationService`, затем `event_bus.emit(VERIFICATION_PENDING, payload)`. Проактивный слой отправляет уведомление админам в Telegram.
2. **FAQ**: админ добавляет FAQ → эмит `FAQ_ADDED` → proactive_layer запускает пересборку эмбеддингов в фоне.
3. **Риск**: внешний POST `delivery_risk_eval` с телом = RiskInput → API вызывает `ai_facade.proactive_hint(risk_input)`; при высоком риске эмитирует `HIGH_RISK_DETECTED` в event_bus.
4. Все проактивные действия идут через event_bus или очередь (пересборка FAQ — async task), без прямых вызовов из бота в сервисы уведомлений/риска кроме как через сервисы и эмит событий.
