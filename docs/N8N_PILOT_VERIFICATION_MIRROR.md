# n8n pilot: Verification mirror

Пилотная интеграция с n8n: при создании заявки на верификацию бот отправляет webhook в n8n для зеркалирования/уведомлений (например, в канал админов). **Источник истины — Python и Postgres;** n8n только получает событие и оркестрирует доставку.

## 1. Границы

- **Python (бот):** создаёт заявку в БД, ставит пользователя в `PENDING`, по желанию отправляет POST на webhook n8n.
- **n8n:** принимает webhook, форматирует и отправляет уведомление (Telegram/Slack/email). Не пишет в нашу БД и не принимает решений по верификации.

## 2. Включение (feature flag)

Интеграция выключена по умолчанию. Чтобы включить:

```env
N8N_VERIFICATION_MIRROR_ENABLED=true
N8N_VERIFICATION_WEBHOOK_URL=https://your-n8n-host/webhook/verification-pending
```

- Если `N8N_VERIFICATION_MIRROR_ENABLED` не `true` или URL пустой — POST не выполняется, поведение бота как без n8n.
- Рекомендуется использовать HTTPS и, при необходимости, секрет в query/header (n8n может проверять его в workflow).

## 3. Формат payload

POST body (JSON):

```json
{
  "event": "verification.pending",
  "tg_user_id": 123456789,
  "role": "courier",
  "first_name": "Иван",
  "last_name": "Иванов",
  "tt_number": "12345",
  "ds_code": "DS-XXX",
  "phone": "+79001234567"
}
```

## 4. n8n workflow (структура)

1. **Trigger:** Webhook node  
   - Method: POST  
   - Path: например `/webhook/verification-pending`  
   - Полный URL — тот, что задаётся в `N8N_VERIFICATION_WEBHOOK_URL`.

2. **Обработка:**  
   - При необходимости проверка секрета (Header/Query).  
   - Формирование текста сообщения из `body.first_name`, `body.last_name`, `body.role`, `body.tt_number`, `body.ds_code`, `body.phone`, `body.tg_user_id`.

3. **Действие:**  
   - Telegram node (отправка в группу/канал админов) или Slack / Email — по выбору.

4. **Ошибки:**  
   - При падении ноды n8n логирует выполнение; бот не повторяет отправку (fire-and-forget). При необходимости можно добавить в n8n повтор или очередь.

## 5. Deployment

- Включить переменные в среде запуска бота (`.env` или контейнер).
- Убедиться, что n8n workflow с Webhook node развёрнут и URL доступен из сети, где крутится бот.
- После деплоя один раз подать заявку на верификацию и проверить приход webhook в n8n (Executions) и появление уведомления.

## 6. Rollback

- **Быстрый откат без деплоя:**  
  `N8N_VERIFICATION_MIRROR_ENABLED=false` или удалить/обнулить `N8N_VERIFICATION_WEBHOOK_URL`. Перезапуск бота не обязателен, если конфиг перечитывается; иначе — перезапуск.

- **Откат кода:**  
  Удалить вызов `asyncio.create_task(notify_verification_pending(payload))` из `src/bot/handlers/verification.py` и задеплоить предыдущую версию. БД и логика верификации не зависят от n8n.

## 7. Риски и ограничения

- **Доставка:** бот не ждёт ответа n8n и не повторяет запрос при ошибке (timeout 5 с). Критичные уведомления при необходимости дублировать другими средствами.
- **Секреты:** URL webhook может содержать секрет в query; не логировать полный URL в открытом виде.
- **PII:** в payload передаются имя, фамилия, телефон — те же данные, что видит админ в боте. Доставка только в доверенный n8n и закрытые каналы.
