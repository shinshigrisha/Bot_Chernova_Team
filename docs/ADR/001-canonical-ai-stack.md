# ADR 001: Canonical AI stack и удаление legacy

## Статус
Принято (2026-03-11)

## Контекст
В проекте был разрозненный AI-код: дубликаты в `src/services/ai/`, плоские провайдеры и router/base в `src/core/services/ai/`, отдельный `src/ai_policy/`. Требовался один канонический путь для runtime, тестов и скриптов, без дублирования логики и импортов.

## Решение
- **Канонический код AI:** только `src/core/services/ai/` — AICourierService, ProviderRouter, провайдеры в подкаталоге `providers/`, CaseEngine, IntentEngine, EmbeddingsService.
- **FAQ:** единственный репозиторий `src/infra/db/repositories/faq_repo.py` (схема v2, таблица `faq_ai`).
- **Политика и промпты:** только `data/ai/` (core_policy.json, intent_tags.json, prompts/).
- **Удалено / не используется в runtime:** `src/services/ai/`, `src/core/services/ai_service.py`, `src/core/services/ai/router.py`, `src/core/services/ai/base.py`, плоские провайдеры в корне `ai/`, `src/ai_policy/`. Импорты только из core и faq_repo.

## Последствия
- Положительные: один источник истины, предсказуемые импорты, проще онбординг и рефакторинг.
- Отрицательные: при добавлении новых AI-фич нужно следовать только canonical paths.
- Дальнейшие шаги: документация и cursor rules ссылаются на эти пути; smoke-скрипты и тесты используют только core.

## Рассмотренные альтернативы
- Оставить два дерева (legacy + core): отклонено из-за дублирования и риска рассинхрона.
- Перенести политику в БД: отклонено на текущем этапе; `data/ai/` остаётся файловым источником.
