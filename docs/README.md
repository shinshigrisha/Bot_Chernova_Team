# Документация проекта Delivery Assistant

**Рантайм:** только `src/`. Каталог `app/` — legacy, в запуск не входит.

## Канонический набор

| Файл | Назначение |
|------|------------|
| [ARCHITECTURE.md](ARCHITECTURE.md) | Слои приложения, сценарии (Admin / Courier / Curator / AI Analyst), куда класть новую логику |
| [ARCHITECTURE_AI_LAYER.md](ARCHITECTURE_AI_LAYER.md) | AI: пайплайн куратора, route classes, explainability, разделение Curator / Analyst |
| [ADMIN_PANEL.md](ADMIN_PANEL.md) | Админ-панель: пункты меню, доступ, верификация |
| [TESTING.md](TESTING.md) | Тесты: маркеры, команды pytest, smoke |
| [DEPLOYMENT.md](DEPLOYMENT.md) | Развёртывание: сервисы, обновление, бэкапы |
| [RUNBOOK.md](RUNBOOK.md) | Ops: health-чеклист, устранение неполадок |

Дополнительно по слоям:

- [ACCESS_ROLE_STATUS_LAYER.md](ACCESS_ROLE_STATUS_LAYER.md) — доступ, роли, статусы, что показывать на /start
- [SCENARIO_ROUTER_LAYER.md](SCENARIO_ROUTER_LAYER.md) — сценарии и роутинг (Admin / Courier / Curator / AI Analyst)
- [PROACTIVE_RISK_EVENTS.md](PROACTIVE_RISK_EVENTS.md) — события (EventBus), риск доставки, API automation

## Справочно (аудит и отчёты)

- [ARCHITECTURE_AUDIT_REPORT.md](ARCHITECTURE_AUDIT_REPORT.md) — снимок аудита архитектуры (src vs app, точки входа)
- [AI_LAYER_DUPLICATE_AUDIT.md](AI_LAYER_DUPLICATE_AUDIT.md) — аудит дубликатов AI-слоя
- [STABLE_AI_LAYER_REPORT.md](STABLE_AI_LAYER_REPORT.md) — отчёт стабилизации AI (explainability, deprecated-модули)

Актуальная архитектура и AI — в ARCHITECTURE.md и ARCHITECTURE_AI_LAYER.md.
