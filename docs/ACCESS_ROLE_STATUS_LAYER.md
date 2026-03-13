# Слой Access / Role / Status

Обязательный слой зрелого операционного бота. Решает **что показать**, **какое меню открыть** и **кому что разрешено** на основе статуса и роли пользователя.

## Статусы (UserStatus)

| Статус | Описание |
|--------|----------|
| **guest** | Нет записи в БД или явный статус guest → экран регистрации |
| **pending** | Заявка на рассмотрении → экран «Ожидайте подтверждения» |
| **approved** | Одобрен → меню по роли (admin / courier / curator) |
| **rejected** | Заявка отклонена → экран «Подать новую заявку» |
| **blocked** | Заблокирован → экран «Аккаунт заблокирован» |

## Роли (UserRole)

| Роль | Меню после /start (при approved) | Доступ в админ-панель |
|------|-----------------------------------|------------------------|
| **admin** | Админ-меню | Да (и по ADMIN_IDS) |
| **lead** | Админ-меню | Да |
| **courier** | Меню курьера | Нет |
| **curator** | Меню куратора | Да (при enable_new_auth_flow) |
| **viewer** | Меню куратора | Нет |

## Пять ответственностей слоя

1. **Что показать на /start**  
   Решает `AccessService.get_principal()` + `menu_renderer.show_entrypoint_menu(principal)`: guest → регистрация; pending → ожидание; rejected → повторная заявка; blocked → сообщение о блокировке; approved → меню по роли.

2. **Какое меню открыть**  
   Та же связка: по `principal.status` и `principal.role` выбирается экран (клавиатура). Логика сосредоточена в `menu_renderer.show_entrypoint_menu()`.

3. **Может ли пользователь использовать AI**  
   Решает `AccessService.can_use_ai(tg_user_id)`: только пользователи в статусе **approved** могут вызывать AI-куратора; guest / pending / rejected / blocked получают сообщение о необходимости регистрации/одобрения.

4. **Кто может видеть admin panel**  
   Решает `AccessService.can_access_admin(tg_user_id)`: статический список ADMIN_IDS из конфига + при включённом auth flow — роль admin/lead/curator и статус не blocked/rejected. Используется в AdminOnlyMiddleware и guard'ах `require_admin_for_*`.

5. **Кому слать verification alerts**  
   Решает `AccessService.get_verification_alert_recipient_ids()`: возвращает список tg_user_id (по умолчанию ADMIN_IDS), которым отправляются уведомления о новой заявке на верификацию. Проактивный слой вызывает этот метод, а не читает конфиг напрямую.

## Модули

- **Источник данных**: `src/core/services/access_service.py` (AccessService, Principal).
- **Энумы**: `src/infra/db/enums.py` (UserStatus, UserRole).
- **Отрисовка по статусу/роли**: `src/bot/menu_renderer.py` (show_entrypoint_menu).
- **Точка входа**: `src/bot/handlers/start.py` (cmd_start → get_principal → show_entrypoint_menu).
- **Guard'ы для админки**: `src/bot/access_guards.py` (require_admin_for_message, require_admin_for_callback).

Все решения «пускать / не пускать» и «что показать» должны опираться на Principal и методы AccessService, а не на разрозненные проверки в хендлерах.
