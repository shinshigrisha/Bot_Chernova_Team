from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from src.infra.db.repositories.faq_repo import FAQRepository
from src.services.ai.provider_router import ProviderRouter

logger = logging.getLogger(__name__)


class AICourierService:
    _policy_cache: dict[str, Any] | None = None

    def __init__(
        self,
        faq_repo: FAQRepository,
        provider_router: ProviderRouter,
        redis_client: Any | None = None,
        policy_path: str | Path = "src/ai_policy/core_policy.json",
    ) -> None:
        self._faq_repo = faq_repo
        self._provider_router = provider_router
        self._redis = redis_client
        self._policy_path = Path(policy_path)
        self._policy = self._load_policy()

    def _load_policy(self) -> dict[str, Any]:
        if AICourierService._policy_cache is not None:
            return AICourierService._policy_cache

        data = json.loads(self._policy_path.read_text(encoding="utf-8"))
        AICourierService._policy_cache = data
        return data

    @staticmethod
    def _tokenize(text: str) -> list[str]:
        text = (
            text.lower()
            .replace("/", " ")
            .replace("-", " ")
            .replace(",", " ")
            .replace(".", " ")
        )
        return [t for t in text.split() if len(t) >= 3]

    def _match_case(self, text: str) -> dict[str, Any] | None:
        lowered = text.lower()
        user_tokens = set(self._tokenize(lowered))

        for case in self._policy.get("must_match_cases", []):
            trigger = str(case.get("trigger", "")).lower().strip()
            if not trigger:
                continue
            if trigger in lowered:
                return case

            trig_tokens = set(self._tokenize(trigger))
            if not trig_tokens:
                continue
            overlap = len(trig_tokens.intersection(user_tokens))
            ratio = overlap / max(1, len(trig_tokens))
            if overlap >= 2 or ratio >= 0.6:
                return case

        return None

    def _build_system_prompt(self, has_tag: bool, has_rule: bool) -> str:
        blocks = self._policy.get("response_structure", {}).get(
            "mandatory_blocks",
            ["Суть ситуации", "Кто отвечает", "Почему", "Что делать сейчас"],
        )
        base = [
            "Ты AI-куратор. Отвечай строго по фактам и по найденным правилам.",
            "Не выдумывай правила, если их нет в контексте.",
            "Запрещены оценки личности и санкции.",
            f"Ответ обязан содержать блоки: {', '.join(blocks)}.",
        ]
        if has_tag:
            base.append("Добавь блок: Правильное решение / тег.")
        if not has_rule:
            base.append("Если прямого правила нет: добавь блок 'Правило / регламент' и рекомендацию эскалации.")
        base.append("Если недостаточно данных: задай максимум 1 уточняющий вопрос.")
        return "\n".join(base)

    async def _save_history(self, user_id: int, role: str, text: str) -> None:
        if self._redis is None:
            return
        try:
            key = f"ai:history:{user_id}"
            payload = json.dumps({"role": role, "text": text}, ensure_ascii=False)
            await self._redis.rpush(key, payload)
            await self._redis.ltrim(key, -10, -1)
        except Exception as exc:
            logger.warning("redis_history_save_failed: %s", exc)

    async def get_answer(self, user_id: int, text: str) -> str:
        question = (text or "").strip()
        if not question:
            return "Опиши, пожалуйста, ситуацию одним предложением."

        case = self._match_case(question)
        case_context = ""
        route = "route_to_curator"
        confidence = 0.0
        faq_hits: list[dict[str, Any]] = []

        if case:
            route = "must_match"
            confidence = 0.95
            case_context = json.dumps(case, ensure_ascii=False)
        else:
            try:
                faq_hits = await self._faq_repo.search_hybrid(question, limit=5)
            except Exception as exc:
                logger.warning("faq_search_failed: %s", exc)
                faq_hits = []

            if faq_hits:
                route = "faq"
                confidence = 0.8
            else:
                route = "route_to_curator"
                confidence = 0.0

        has_tag = bool(case and case.get("main_tag"))
        has_rule = bool(case or faq_hits)
        system_prompt = self._build_system_prompt(has_tag=has_tag, has_rule=has_rule)

        clarify_hint = ""
        if confidence < 0.8:
            clarify_hint = "Если для уверенного ответа не хватает данных, задай один уточняющий вопрос."

        escalation_message = self._policy.get(
            "escalation_message",
            "В базе знаний нет однозначного правила. Рекомендуется обратиться к куратору.",
        )

        context_chunks = []
        if case:
            context_chunks.append(f"Must-match кейс:\n{case_context}")
        if faq_hits:
            faq_context = "\n\n".join(
                [
                    f"FAQ#{i+1}\nQ: {row.get('question','')}\nA: {row.get('answer','')}\nScore: {row.get('score', 0)}"
                    for i, row in enumerate(faq_hits)
                ]
            )
            context_chunks.append(f"Найденные FAQ:\n{faq_context}")
        if not context_chunks:
            context_chunks.append(
                f"Прямое правило не найдено. Рекомендуемая эскалация: {escalation_message}"
            )

        user_payload = (
            f"Вопрос пользователя:\n{question}\n\n"
            f"Маршрут: {route}\n"
            f"Confidence: {confidence}\n\n"
            f"{clarify_hint}\n\n"
            f"{chr(10).join(context_chunks)}"
        ).strip()

        await self._save_history(user_id, "user", question)

        try:
            answer = await self._provider_router.chat(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_payload},
                ],
                temperature=0.2,
                max_tokens=500,
            )
            final = answer.strip()
        except Exception as exc:
            logger.warning("provider_chat_failed: %s", exc)
            if route == "route_to_curator":
                final = escalation_message
            elif faq_hits:
                first = faq_hits[0]
                final = (
                    "Суть ситуации: найдено близкое правило в базе.\n"
                    "Кто отвечает: курьер по регламенту, при споре — куратор.\n"
                    f"Почему: совпадение с FAQ (score={first.get('score', 0)}).\n"
                    f"Что делать сейчас: {first.get('answer', '')}"
                )
            elif case:
                final = (
                    "Суть ситуации: определён must-match кейс.\n"
                    f"Кто отвечает: {case.get('responsible', 'curator')}.\n"
                    f"Почему: {case.get('why', '')}\n"
                    f"Что делать сейчас: {'; '.join(case.get('actions', []))}"
                )
            else:
                final = escalation_message

        await self._save_history(user_id, "assistant", final)
        return final
