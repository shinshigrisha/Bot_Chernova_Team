# Coding Standards

## Python
- Python 3.12
- Type hints everywhere (mypy-friendly)
- Prefer `pydantic` models for IO boundaries (bot payloads, API)
- Use `structlog` or stdlib `logging` with JSON formatter

## Architecture
- Handlers do **not** touch DB directly. Handlers call services.
- Services use repositories (unit-testable).
- Repositories are thin, no business rules.

## Error handling
- Always `answerCallbackQuery` for Telegram callbacks.
- For expected domain errors: raise `DomainError(code, message)` and map to user-friendly output.
- For unexpected errors: log with context + return safe message.

## Logging
- Include correlation ids: `request_id`, `user_id`, `chat_id`, `batch_id`, `notification_id`
- Log at INFO for domain events (ingest accepted, notification queued, vote upserted)
- Log at WARNING for recoverable failures (429, temporary integration failures)
- Log at ERROR for permanent failures (schema mismatch, invalid CSV structure)

## Formatting
- Black + Ruff
- Import order: isort
