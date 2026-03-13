# Rule 01: Архитектура и структура проекта

## Цель
Сохранять единый каркас проекта без параллельных реализаций, дублирующих модулей и разъезжающихся путей импорта.

## Каноническая схема слоёв (верхний уровень)

Порядок слоёв сверху вниз (запрос пользователя идёт сверху вниз, ответ — снизу вверх):

1. **Telegram** — канал доставки сообщений.
2. **Bot Layer (aiogram)** — `Dispatcher`, роутеры (`src/bot/*`), middlewares. Только приём/отправка, инъекция зависимостей, логирование.
3. **Access / Role / Status Layer** — проверки прав и статуса пользователя (`AccessService`, middlewares/guards). Решает: что показать на /start, какое меню, может ли пользователь использовать AI, кто видит админ-панель, кому слать verification alerts. См. [docs/ACCESS_ROLE_STATUS_LAYER.md](../docs/ACCESS_ROLE_STATUS_LAYER.md).
4. **Scenario Router** — «дирижёр»: ветвление по группам A) Admin B) Courier C) Curator D) AI Analyst. Навигация и переходы состояний (`navigation`, `menu_renderer`, `states`). См. [docs/SCENARIO_ROUTER_LAYER.md](../docs/SCENARIO_ROUTER_LAYER.md).
5. **Application Services** — доменная логика: `UserService`, `AccessService`, `VerificationService`, `NotificationService`, `IngestService`, risk/proactive, вызов AI только через `AIFacade`. Без прямого знания о Telegram.
6. **AI Layer** — единственная точка входа `AIFacade`; внутри: decision → knowledge → retrieval → policy → generation → validation → explainability. Код в `src/core/services/ai/*`. Пайплайн и метки explainability: [docs/ARCHITECTURE_AI_LAYER.md](../docs/ARCHITECTURE_AI_LAYER.md).
7. **Infra** — Postgres, Redis, Celery, Storage, Notifications, n8n. Чистая инфраструктура, без доменной логики.

Правило: хендлеры не содержат бизнес-логики и не вызывают БД/очереди/LLM напрямую — только Application Services и `AIFacade`.

## Один вход в AI (AIFacade), три режима

Единственная точка входа в AI-слой — **AIFacade**. Три раздельных режима (см. docs/AI_MODES.md), не один «умный ответчик»:
- **Courier assistant:** `answer_user(user_id, text)`, `proactive_hint(risk_input)` — кейсы доставки.
- **Admin copilot:** `answer_admin(admin_id, text)` — помощь админу (FAQ, рассылки, анализ).
- **Analytics assistant:** `analyze_csv(tt_metrics, ...)` — анализ CSV/xlsx/pdf/таблиц.

Запрещено из handlers, admin, API и скриптов верхнего уровня:
- вызывать ProviderRouter, AICourierService, RAGService, IntentEngine, AnalyticsAssistant напрямую;
- дергать LLM/провайдеров в обход фасада.

Тесты и внутренняя реализация фасада могут использовать AICourierService/ProviderRouter напрямую.

## Обязательные правила

1. Не создавать новые параллельные каталоги для бота.
   - Использовать существующую структуру `src/bot/*` (handlers, admin, keyboards, middlewares, navigation, states).
   - Запрещено добавлять альтернативные деревья вида `app/bot/*`, `bot/*`, `telegram_bot/*`, если их нет в принятой архитектуре.
   - Новые сценарии вводить через роутеры и состояния в рамках Scenario Router, а не размазывать логику по хендлерам.

2. Новые AI-сервисы размещать в `src/core/services/ai/*`.
   - Логика orchestration, policy, роутинга, провайдеров и вспомогательных AI-утилит должна находиться только там.
   - Не дублировать AI-логику в хендлерах, админ-командах и скриптах, кроме тонких вызовов уже существующих сервисов.

3. Не дублировать DB/Redis клиенты.
   - Использовать существующие pool/session factory/клиенты проекта.
   - Запрещено поднимать отдельные новые подключения к тем же ресурсам без явной необходимости и архитектурного решения.
   - Для БД использовать принятую инфраструктуру доступа (репозитории, session factory, транзакции).

4. Соблюдать существующий DI-подход.
   - Подключать зависимости через уже используемый механизм (например, `bot[...]`, middleware, контейнер), а не внедрять новый параллельный способ.
   - При добавлении нового сервиса сначала проверить, как инициализируются текущие сервисы в `main`/startup.

5. Не ломать обратную совместимость без адаптера.
   - Если меняется интерфейс сервиса/репозитория, добавить адаптационный слой или совместимый контракт на переходный период.
   - Не удалять существующие маршруты/команды без явного запроса.

## Проверка перед merge

- Все новые/измененные пути соответствуют `src/bot/*` и `src/core/services/ai/*`.
- Нет повторной инициализации DB/Redis клиента.
- Нет вторичного "main entrypoint" или второго диспетчера/бота.
- Нет дублей одинаковых функций в разных каталогах.
