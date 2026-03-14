# Админ-панель

Вход: команда `/admin` в боте. Доступ: роль **ADMIN**, **LEAD** или **CURATOR** (при включённом auth flow) либо Telegram ID в списке **ADMIN_IDS** в `.env`. Проверки: `AccessService.can_access_admin()`, middleware `AdminOnlyMiddleware`, guard'ы в `src/bot/access_guards.py`. Подробнее — [ACCESS_ROLE_STATUS_LAYER.md](ACCESS_ROLE_STATUS_LAYER.md).

## Пункты меню

- **ТМЦ** — выдача/возврат активов (`admin:tmc`, `tmc_issue`)
- **Журнал смены** — инциденты (`admin:journal`, `incident`)
- **Импорт CSV** — загрузка данных (`admin:ingest`)
- **Верификация** — заявки на регистрацию: одобрение/отклонение/блок (`admin:verification_menu`, `admin:verification:approve/reject/block`)
- **Мониторинг** — статус бота и AI (`admin:monitoring_menu`, `admin:monitor`)
- **AI** — статус провайдеров, перезагрузка политики, добавление/поиск FAQ (`/ai_status`, `/ai_policy_reload`, `/ai_add_faq`, `/ai_search_faq`)
- **FAQ / база знаний** — просмотр и управление FAQ (`admin:faq_menu`)
- **Анализ / CSV** — раздел загрузки (`admin:csv_menu`, `admin:ingest`)
- **Рассылки** — раздел рассылок (заглушка) (`admin:broadcast_menu`)

Роутеры админки: `src/bot/admin/admin_router.py` (включает admin_handlers, admin_menu, ai_admin, ingest, incident, tmc_issue). Сценарии и callback → flow — [SCENARIO_ROUTER_LAYER.md](SCENARIO_ROUTER_LAYER.md).

## Роли

| Роль | Доступ в админку |
|------|-------------------|
| ADMIN | Да (и по ADMIN_IDS) |
| LEAD | Да |
| CURATOR | Да (при включённом auth flow) |
| VIEWER | Нет |
| COURIER | Нет |

Обзор возможностей и команд бота — в корневом [README.md](../README.md).
