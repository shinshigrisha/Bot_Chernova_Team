# AI-куратор

## 1) Что такое AI-куратор (RAG + policy)

AI-куратор в этом проекте — это сервис, который отвечает курьеру по многоуровневой схеме:

- сначала пытается дать быстрый ответ по правилам (rule-based);
- затем ищет подходящие записи в FAQ (RAG-слой через БД);
- при необходимости использует LLM-провайдеров для формулировки ответа;
- если уверенности недостаточно или кейс рискованный, маршрутизирует вопрос к человеку (эскалация).

Поведение AI регулируется policy-файлами в `data/ai/`:

- `core_policy.json` — правила маршрутизации, fallback, риск-темы;
- `intent_tags.json` — теги/интенты;
- `prompts/*` — системный промпт, стиль, уточняющие вопросы.

## 2) Как устроен ответ (обязательные блоки)

Для операционных ответов используйте единый формат:

- **Суть ситуации** — кратко, что произошло;
- **Кто отвечает** — кто должен действовать (курьер/даркстор/ТМ/поддержка);
- **Почему** — на какое правило или логику опирается ответ;
- **Что делать сейчас** — пошагово и практично.

Если есть релевантный тег/категория, добавляйте блок:

- **Правильное решение / тег**.

Если точного правила нет:

- **Правило / регламент** (что можно утверждать точно);
- явная эскалация к куратору/ответственному.

## 3) Провайдеры (OpenAI/DeepSeek/Groq), env-переменные

Поддерживаются три провайдера:

- OpenAI (`OPENAI_API_KEY`, `OPENAI_MODEL`);
- DeepSeek через OpenAI SDK (`DEEPSEEK_API_KEY`, `DEEPSEEK_BASE_URL`, `DEEPSEEK_MODEL`);
- Groq (`GROQ_API_KEY`, `GROQ_MODEL`).

Управляющие переменные:

- `AI_ENABLED` — общий флаг включения AI;
- `AI_PROVIDER_ORDER_CHAT` — порядок провайдеров для обычного ответа;
- `AI_PROVIDER_ORDER_REASON` — порядок для reasoning-режима.

Пример (из `.env.example`):

```env
AI_ENABLED=false
GROQ_API_KEY=...
GROQ_MODEL=llama-3.1-70b-versatile
DEEPSEEK_API_KEY=...
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_MODEL=deepseek-chat
OPENAI_API_KEY=...
OPENAI_MODEL=gpt-4o-mini
AI_PROVIDER_ORDER_CHAT=groq,deepseek,openai
AI_PROVIDER_ORDER_REASON=openai,deepseek,groq
```

## 4) Как добавить FAQ (через админ-команды)

Команда доступна только администратору из `ADMIN_USER_ID` (env):

- `/ai_add_faq`

Дальше бот ведет по FSM-шагам:

1. `question`
2. `answer`
3. `category` (или `-`)
4. `tag` (или `-`)
5. `keywords` через запятую (или `-`)

После последнего шага запись сохраняется в БД.  
Для поиска используйте:

- `/ai_search_faq <текст>` — вывод top-5 совпадений (`question` + короткий `answer`).

## 5) Как обновлять policy

Без рестарта бота:

- `/ai_policy_reload`

Команда вызывает `reload_policy()` в `AICourierService` и перечитывает:

- `data/ai/core_policy.json`
- `data/ai/intent_tags.json`
- `data/ai/prompts/clarify_questions.json`
- `data/ai/prompts/system_prompt.md`
- `data/ai/prompts/style_guide.md`

## 6) Типовые проблемы

- **Нет ответа / пришла эскалация**
  - Низкая уверенность по FAQ;
  - кейс помечен как рискованный policy-правилами;
  - не найден надежный маршрут для автоответа.

- **Пустая база FAQ**
  - Поиск не находит фактов, AI чаще уходит в общий fallback/эскалацию;
  - проверь сидирование FAQ и ручное добавление через `/ai_add_faq`.

- **Нет ключей API**
  - LLM-провайдеры не активируются;
  - сервис продолжает работать через FAQ/fallback, но без генерации LLM.

- **Timeouts**
  - Временные сетевые проблемы или задержки API;
  - провайдер может не ответить, роутер переключится на следующий по приоритету;
  - при недоступности провайдеров остается fallback-ответ.

## 7) Smoke-test: как локально прогнать тестовый вопрос без Telegram

### Вариант A: готовый smoke по golden cases

1. Убедитесь, что доступны:
   - `DATABASE_URL`
   - файл `data/ai/golden_cases.jsonl`
2. Запустите:

```bash
python scripts/smoke_ai.py
```

Ожидаемый итог в консоли:

- `SMOKE: X/Y passed`

### Вариант B: единичная локальная проверка

Можно временно добавить кейс в `data/ai/golden_cases.jsonl` с одним `input` и нужными проверками `must_contain_any`/`must_not_contain_any`, затем запустить тот же `python scripts/smoke_ai.py`.
