# Слой Scenario Router

«Дирижёр» продукта: разделяет сценарии по типам флоу и направляет пользователя в нужный роутер и состояние. Не содержит бизнес-логики — только ветвление и переходы. Отрисовка меню и FSM — в `navigation.py`, `menu_renderer.py`, `states*.py`; типы флоу и маппинг callback → флоу — в `src/bot/scenario_router.py`.

---

## A. Admin flows

Меню администратора и все админ-сценарии (доступ через Access Layer: `can_access_admin`).

| Подфлоу | Описание | Роутер / callback | Состояния |
|--------|----------|-------------------|-----------|
| Меню администратора | Главный экран админ-панели | `admin` (admin_handlers), `Command("admin")` | — |
| Верификация | Список заявок, одобрение/отклонение/блок | `admin:verification_menu`, `admin:verification:approve/reject/block` | — |
| Мониторинг | Статус бота и AI | `admin:monitoring_menu`, `admin:monitor` | — |
| AI diagnostics | Статус провайдеров, перезагрузка политики, добавление FAQ | `/ai_status`, `/ai_policy_reload`, `/ai_add_faq`, `/ai_search_faq` | AIAddFAQStates |
| FAQ / база знаний | Просмотр и управление FAQ | `admin:faq_menu` | — |
| Анализ файлов (вход) | Раздел загрузки CSV | `admin:csv_menu`, `admin:ingest` | — |
| Рассылки | Раздел рассылок (заглушка) | `admin:broadcast_menu` | — |
| ТМЦ / журнал смены | Выдача ТМЦ, инциденты | `admin:tmc`, `admin:journal` | TMCIssueStates, IncidentStates |

Роутеры: `admin` (включает admin_main_menu, admin_tmc, admin_incident, admin_ingest, ai_admin).

Отдельно: **подача заявки на регистрацию** (со стороны пользователя) — роутер `verification`, BotFlow.VERIFICATION, состояния VerificationStates (choose_role → first_name → … → confirm). Доступ из корневого меню для guest.

---

## B. Courier flows

Сценарии курьера: быстрые кейсы, AI-куратор, статусные экраны, помощь.

| Подфлоу | Описание | Роутер / callback | Состояния |
|--------|----------|-------------------|-----------|
| Быстрые кейсы | Типовые кейсы (клиент не отвечает, недовоз и т.д.) | `ai_curator:case:*`, ROOT_AI_CURATOR → клавиатура кейсов | AIChatStates.active |
| AI-куратор | Диалог с AI по кейсам доставки, произвольный текст | `root:ai_curator`, `/ai`, `/ai_off`, текст в AIChatStates | AIChatStates |
| Статусные экраны | Pending / rejected / blocked (после /start) | `menu_renderer.show_entrypoint_menu`, `pending:refresh` | — |
| Помощь | Справка и навигация | `root:help`, `nav:help`, кнопки «Помощь» в меню | — |
| Смены / FAQ (меню курьера) | Пункты меню курьера | `courier:shifts`, `courier:faq` | — |

Роутеры: `start`, `navigation`, `ai_chat`. Меню курьера: `keyboards/courier_main.py`, отрисовка по роли в `menu_renderer`.

---

## C. Curator flows

Наблюдение, тревоги, эскалация, операционные кейсы.

| Подфлоу | Описание | Роутер / callback | Состояния |
|--------|----------|-------------------|-----------|
| Аналитика / просмотр | Просмотр аналитики доставок | `curator:analytics` | — |
| FAQ и регламенты | Просмотр FAQ | `curator:faq` | — |
| AI-куратор (вход) | Тот же AI-куратор, что у курьера | `root:ai_curator` | AIChatStates |
| Наблюдение за нарушениями / тревоги / эскалация | В текущей реализации частично через админку (инциденты, верификация). Отдельный curator-only UI — при расширении. | — | — |

Роутеры: те же `navigation`, `ai_chat`; меню куратора: `keyboards/curator_main.py`, отрисовка в `menu_renderer` по роли curator/viewer.

---

## D. AI Analyst flows

Загрузка данных, запуск анализа, получение отчёта.

| Подфлоу | Описание | Роутер / callback | Состояния |
|--------|----------|-------------------|-----------|
| Загрузка CSV | Загрузка файла, создание батча, постановка в очередь парсинга | `admin:ingest` | IngestCSVStates.upload |
| Загрузка XLSX/PDF | В перспективе (сейчас — CSV) | — | — |
| Запуск анализа | Парсинг батча (Celery), расчёт метрик | API / worker | — |
| Получение отчёта | Аналитический отчёт по метрикам (AnalyticsAssistant.analyze_csv) | Вызов из админки или отдельной команды | — |

Роутеры: `admin_ingest` (загрузка), аналитический отчёт — через AIFacade.analyze_csv (вызывается при необходимости из админ-сценариев).

---

## Сводка: флоу → роутеры

| Группа | BotFlow (scenario_router) | Роутеры aiogram |
|--------|---------------------------|------------------|
| A. Admin | ADMIN, частично AI_ANALYST | admin (admin_handlers, tmc_issue, incident, ingest, ai_admin) |
| B. Courier | COURIER_UI, AI_CURATOR | start, navigation, ai_chat |
| C. Curator | CURATOR_UI, AI_CURATOR | navigation, ai_chat |
| D. AI Analyst | AI_ANALYST | admin_ingest, вызовы AIFacade.analyze_csv |

Точный маппинг callback_data → флоу: `src/bot/scenario_router.py` (CALLBACK_TO_FLOW, resolve_flow).
