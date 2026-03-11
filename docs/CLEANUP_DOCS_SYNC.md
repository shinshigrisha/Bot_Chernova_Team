# Синхронизация docs и rules после cleanup

Соответствие правилу: при изменении поведения обновлять docs (`.cursor/rules/60-docs-required.md`).

## Проверенные документы (минимум по 60-docs-required)

| Документ | Статус | Замечания |
|----------|--------|-----------|
| **docs/ARCHITECTURE.md** | Обновлён | Добавлен раздел «AI (куратор)»: канонический стек (core/services/ai, faq_repo, data/ai), указано удаление legacy. |
| **docs/DEPLOYMENT.md** | Соответствует | Упоминаний удалённых модулей нет; переменные и сервисы актуальны. |
| **docs/RUNBOOK.md** | Соответствует | Упоминаний AI legacy нет. |
| **docs/ADMIN_GUIDE.md** | Соответствует | Пункты меню и роли актуальны; AI — общие формулировки (управление базой знаний и политиками). |
| **docs/DATA_DICTIONARY.md** | Соответствует | Таблицы и поля не затронуты cleanup. |
| **docs/SECURITY.md** | Соответствует | Секреты, RBAC, сеть — без изменений. |

## Дополнительно обновлено

- **docs/ai-architecture-audit.md** — в начало добавлен блок «Статус после cleanup»: миграция выполнена, перечислены удалённые пути, указана ссылка на ARCHITECTURE.md.

## Правила Cursor

- **.cursor/rules/60-docs-required.md** — без изменений; список обязательных доков (ARCHITECTURE, DEPLOYMENT, RUNBOOK, ADMIN_GUIDE, DATA_DICTIONARY, SECURITY) соблюдён.

## Отдельный кусок cleanup (если понадобится)

- **docs/DOCS.md**, **docs/AI_CURATOR.md** — содержат упоминания `/ai_policy_reload` и команд AI; содержание актуально (команды остались), пути к модулям в этих файлах не перечисляются. При желании можно явно указать в DOCS.md/AI_CURATOR.md, что реализация AI — только `src/core/services/ai/` и `data/ai/`.
