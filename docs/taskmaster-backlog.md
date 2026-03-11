# Delivery Assistant — Task Master Backlog

Этот backlog подготовлен как источник для Task Master-планирования проекта `Delivery Assistant`.

## Planning Principles
- Сохраняем layered architecture: `bot -> core -> infra`.
- Handler'ы остаются тонкими и не содержат бизнес-логику.
- Вся orchestration-логика живет в сервисах.
- Репозитории отвечают только за persistence и query contract.
- `AI Curator` рассматривается как отдельный bounded context.
- Для `AI Curator` приоритет маршрутизации: `must-match -> FAQ / retrieval -> generation -> escalation`.
- При недостаточной уверенности система должна эскалировать на человека, а не угадывать.

## Epic 1 — Infra / Bootstrap
Goal: стабилизировать каркас проекта, окружение, конфигурацию и базовый runtime для локального и контейнерного запуска.

### Task 1.1 — Align project skeleton and package boundaries
- Проверить текущую структуру `src/bot`, `src/core`, `src/infra`, `tests`, `migrations`.
- Нормализовать границы пакетов в соответствии с layered architecture.
- Убедиться, что bot-слой не тянет persistence или бизнес-логику напрямую.

Subtasks:
- `1.1.1` Провести inventory существующих модулей и отметить несоответствия целевой структуре.
- `1.1.2` Создать недостающие директории и пакеты без переноса бизнес-логики в handler'ы.
- `1.1.3` Добавить отсутствующие `__init__.py` и привести импорты к стабильному виду.
- `1.1.4` Проверить, что зависимости направлены только вниз по слоям.
- `1.1.5` Зафиксировать спорные места, где потребуется отдельная декомпозиция в следующих эпиках.

Definition of done:
- структура каталогов и пакетов согласована с архитектурой проекта
- импорты разрешаются без циклических зависимостей
- bot-слой не содержит прямых обращений к persistence/use-case логике

### Task 1.2 — Define configuration and environment contract
- Сформировать единый контракт конфигурации для bot, db, queue, storage, logging и AI-интеграций.
- Сохранить совместимость с уже существующими переменными окружения.

Subtasks:
- `1.2.1` Провести аудит существующих env-переменных и runtime-настроек.
- `1.2.2` Нормализовать `src/config.py` и разделить настройки по доменам ответственности.
- `1.2.3` Определить обязательные и опциональные переменные с явной валидацией.
- `1.2.4` Дополнить `.env.example`, не удаляя текущие рабочие переменные.
- `1.2.5` Подготовить понятные startup-ошибки для отсутствующих критичных настроек.

Definition of done:
- конфигурация читается централизованно
- обязательные переменные валидируются на старте
- `.env.example` отражает минимально необходимый контракт запуска

### Task 1.3 — Finalize container bootstrap
- Подготовить рабочее контейнерное окружение для локальной разработки и smoke-запуска.
- Разделить роли контейнеров bot/worker и инфраструктурных сервисов.

Subtasks:
- `1.3.1` Проверить и доработать `Dockerfile` под текущий runtime проекта.
- `1.3.2` Создать или нормализовать `docker-compose.yml` для `postgres`, `redis`, `minio`, `bot`, `worker`.
- `1.3.3` Настроить volumes, healthchecks и базовый порядок старта сервисов.
- `1.3.4` Убедиться, что миграции можно применить в containerized-сценарии.
- `1.3.5` Зафиксировать минимальный smoke flow: install -> up -> migrate -> bot/worker.

Definition of done:
- `docker compose up -d` поднимает базовую инфраструктуру без ручных правок
- bot и worker стартуют отдельно и используют общий конфиг
- контейнерный запуск не нарушает layered architecture

### Task 1.4 — Standardize developer commands and bootstrap workflow
- Свести локальные команды разработки к одному предсказуемому интерфейсу.
- Исключить ручные, неочевидные шаги из базового developer setup.

Subtasks:
- `1.4.1` Добавить или нормализовать `Makefile` либо эквивалентный task runner.
- `1.4.2` Завести команды `install`, `up`, `down`, `logs`, `migrate`, `bot`, `worker`, `test`, `lint`.
- `1.4.3` Проверить, что команды не инкапсулируют бизнес-логику и не обходят сервисный слой.
- `1.4.4` Добавить короткий bootstrap flow для нового разработчика.
- `1.4.5` Зафиксировать ожидаемые exit codes и типовые failure scenarios.

Definition of done:
- ключевые dev-команды запускаются из единой точки
- новый разработчик может поднять проект по короткому сценарию
- команды не требуют знания внутреннего устройства слоев

### Task 1.5 — Establish startup wiring and observability baseline
- Подготовить базовую инициализацию приложения, логирования и runtime-проверок.
- Отделить инфраструктурный startup от use-case логики.

Subtasks:
- `1.5.1` Выделить единый bootstrap для config/logging/DI wiring.
- `1.5.2` Включить структурированное логирование для bot и worker процессов.
- `1.5.3` Добавить startup-checks для критичных зависимостей и конфигурации.
- `1.5.4` Убедиться, что entrypoint'ы не содержат бизнес-операций.
- `1.5.5` Подготовить минимальные health/smoke точки наблюдаемости для дальнейших тестов.

Definition of done:
- runtime bootstrap воспроизводим и прозрачен
- логи позволяют понять конфигурацию старта и место падения
- entrypoint'ы не нарушают правило "thin orchestration only"

## Epic 2 — Database / Alembic / Persistence
Goal: собрать устойчивый persistence-слой с async-сессией, миграциями и репозиториями.

### Task 2.1 — Stabilize Alembic async migration flow
- Привести `alembic` и `migrations/env.py` к стабильному async migration contract.

### Task 2.2 — Implement database session and base persistence infra
- Вынести engine, session factory и базовые DB-зависимости в `infra/db`.

### Task 2.3 — Model core tables and constraints
- Описать ORM-модели, индексы, unique/partial unique constraints и связи.

### Task 2.4 — Create initial migration set
- Подготовить начальный набор миграций для разворота БД с нуля и корректного downgrade.

### Task 2.5 — Implement repositories by aggregate boundary
- Выделить репозитории по use-case доменам и не смешивать persistence с сервисной логикой.

## Epic 3 — Core Services
Goal: вынести все бизнес-правила и use-case orchestration в сервисный слой.

### Task 3.1 — Introduce domain exceptions and service contracts
- Определить единые исключения, сервисные интерфейсы и инварианты домена.

### Task 3.2 — Implement asset lifecycle service
- Реализовать выдачу, возврат и аудит событий по активам через сервисный слой.

### Task 3.3 — Implement incident and shift logging service
- Вынести создание инцидентов и журналирование смен в отдельный use-case слой.

### Task 3.4 — Implement notification orchestration service
- Реализовать постановку уведомлений в очередь через сервис, без прямой доставки из handler'ов.

### Task 3.5 — Implement ingest orchestration service
- Обработать загрузку CSV, dedupe, storage handoff и enqueue фоновой обработки.

## Epic 4 — Queue / Notifications / Storage
Goal: реализовать асинхронные доставки, фоновые задачи и объектное хранение.

### Task 4.1 — Setup Celery application and worker runtime
- Поднять отдельный queue runtime для фоновых задач.

### Task 4.2 — Implement notification delivery pipeline
- Добавить delivery task, retry policy и запись delivery attempts.

### Task 4.3 — Implement notification channels
- Вынести каналы доставки в изолированные infra-адаптеры.

### Task 4.4 — Implement storage adapter for S3 / MinIO
- Подготовить клиент хранения файлов и единый API для загрузки/чтения.

### Task 4.5 — Add reliability hooks for retries and idempotency
- Зафиксировать retry, timeout и idempotency rules для фоновых операций.

## Epic 5 — Telegram Bot / Admin / FSM
Goal: собрать bot-слой как thin interface над сервисами и AI curator bounded context.

### Task 5.1 — Stabilize bot entrypoint and dependency wiring
- Подключить config, middleware, routers и DI без внедрения use-case логики в entrypoint.

### Task 5.2 — Implement base user handlers
- Реализовать `/start`, onboarding и базовые пользовательские сценарии через сервисы.

### Task 5.3 — Implement admin panel and access control
- Добавить admin menu и разграничение по `ADMIN_IDS`.

### Task 5.4 — Implement FSM for assets workflows
- Собрать выдачу и возврат активов как управляемые FSM-сценарии.

### Task 5.5 — Implement FSM for incidents and operational reports
- Добавить формализованный сценарий регистрации инцидентов.

### Task 5.6 — Implement file upload and ingest bot flows
- Подключить загрузку CSV и вызов `IngestService`.

## Epic 6 — AI Curator / Knowledge / RAG
Goal: построить отдельный bounded context для curator-ответов с приоритетом must-match и контролируемой эскалацией.

### Task 6.1 — Standardize knowledge sources and FAQ persistence
- Нормализовать knowledge/FAQ storage и единый интерфейс чтения.

### Task 6.2 — Implement retrieval pipeline for grounded answers
- Реализовать keyword/text retrieval и подготовку контекста ответа.

### Task 6.3 — Implement curator routing policy
- Ввести порядок: must-match, затем FAQ/retrieval, затем safe generation, иначе escalation.

### Task 6.4 — Add curator conversation memory boundaries
- Ограничить историю в Redis по TTL, размеру и назначению.

### Task 6.5 — Integrate LLM generation with grounding guards
- Разрешить генерацию только поверх подтвержденного контекста и с безопасным fallback.

### Task 6.6 — Add explainability, confidence checks and validation
- Логировать route decision, confidence и причины эскалации; валидировать ответ на выходе.

### Task 6.7 — Add admin tools for knowledge operations
- Дать админам инструменты работы с FAQ, поиском и curator-метриками.

## Epic 7 — Documentation / Runbooks / Architecture
Goal: сделать проект понятным для запуска, сопровождения и безопасного развития.

### Task 7.1 — Update architecture documentation
- Описать роли слоев, bounded contexts и основные потоки данных.

### Task 7.2 — Update deployment and environment docs
- Зафиксировать compose flow, env contract, миграции и startup-порядок.

### Task 7.3 — Update admin and operations runbooks
- Подготовить runbook для ручных операций, поддержки и админских сценариев.

### Task 7.4 — Update troubleshooting and incident documentation
- Добавить типовые сбои, диагностику и пути эскалации.

### Task 7.5 — Maintain security and data dictionary docs
- Описать секреты, доступы, таблицы и чувствительные интеграции.

## Epic 8 — Tests / Quality / Reliability
Goal: зафиксировать архитектурные и поведенческие гарантии тестами и quality gates.

### Task 8.1 — Establish pytest async baseline
- Подготовить общие fixtures, test DB и единый способ запуска тестов.

### Task 8.2 — Cover repository invariants
- Проверить ограничения persistence-слоя и корректность репозиторных контрактов.

### Task 8.3 — Cover service-level business rules
- Добавить тесты для ключевых use-case инвариантов сервисов.

### Task 8.4 — Cover queue and delivery reliability paths
- Протестировать retries, delivery attempts и ошибки внешних каналов.

### Task 8.5 — Add bot smoke and FSM tests
- Зафиксировать критические пользовательские сценарии bot-слоя.

### Task 8.6 — Add AI curator routing and escalation tests
- Проверить must-match, grounding, low-confidence fallback и explainability-сигналы.