# Telegram Adapter Rules (aiogram)

## Golden rule
Telegram handlers are thin: validate → call service → respond.

## Must-haves
- Callback handlers always call `answerCallbackQuery`.
- Use FSM only for interactive flows (asset issue/return, incident creation, CSV upload).
- All long operations must be asynchronous (queue task).
- Any mass send/alerts are queued via `NotificationService`, never sent inside handler loops.

## Topics / forum
- Support binding per Team/Territory:
  - chat_id
  - optional topic_id per message type (alerts, daily, assets, incidents)
- If forum binding missing → fallback to base chat_id and log warning.
