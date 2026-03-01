from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

import structlog
from sqlalchemy.ext.asyncio import async_sessionmaker

from src.core.services.ai.provider_router import ProviderRouter
from src.infra.db.repositories.faq_ai import FAQAIRepository

log = structlog.get_logger(__name__)


@dataclass
class AICourierResult:
    text: str
    route: str
    confidence: float
    intent: str
    need_clarify: bool
    clarify_question: str
    escalate: bool
    evidence: list[str] = field(default_factory=list)
    debug: dict[str, Any] = field(default_factory=dict)


class AICourierService:
    def __init__(
        self,
        session_factory: async_sessionmaker,
        router: ProviderRouter | None = None,
        data_root: str | Path = "data/ai",
    ) -> None:
        self._session_factory = session_factory
        self._router = router
        self._faq_repo = FAQAIRepository()
        self._data_root = Path(data_root)

        self._policy = self._load_json("core_policy.json", default={})
        self._intent_tags = self._load_json("intent_tags.json", default={})
        self._clarify_questions = self._load_json(
            "prompts/clarify_questions.json", default={}
        )
        self._system_prompt = self._load_text("prompts/system_prompt.md", default="")
        self._style_guide = self._load_text("prompts/style_guide.md", default="")

        self._fallbacks = self._policy.get("fallbacks", {})
        self._faq_threshold = float(self._policy.get("routing", {}).get("faq_threshold", 0.72))
        self._high_risk_topics = [
            str(x).lower() for x in self._policy.get("high_risk_topics", [])
        ]

        self._rule_reply_fn = self._resolve_rule_reply_fn()

    def reload_policy(self) -> None:
        self._policy = self._load_json("core_policy.json", default={})
        self._intent_tags = self._load_json("intent_tags.json", default={})
        self._clarify_questions = self._load_json(
            "prompts/clarify_questions.json", default={}
        )
        self._system_prompt = self._load_text("prompts/system_prompt.md", default="")
        self._style_guide = self._load_text("prompts/style_guide.md", default="")
        self._fallbacks = self._policy.get("fallbacks", {})
        self._faq_threshold = float(
            self._policy.get("routing", {}).get("faq_threshold", 0.72)
        )
        self._high_risk_topics = [
            str(x).lower() for x in self._policy.get("high_risk_topics", [])
        ]

    def _resolve_rule_reply_fn(self):
        try:
            from src.core.services.ai_response_service import build_courier_quick_reply

            return build_courier_quick_reply
        except Exception:
            return None

    def _load_json(self, rel_path: str, default: dict[str, Any]) -> dict[str, Any]:
        path = self._data_root / rel_path
        if not path.exists():
            return default
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return default

    def _load_text(self, rel_path: str, default: str) -> str:
        path = self._data_root / rel_path
        if not path.exists():
            return default
        try:
            return path.read_text(encoding="utf-8")
        except Exception:
            return default

    def detect_intent(self, text: str) -> str:
        lowered = text.lower()
        best_intent = "unknown"
        best_score = 0
        for intent, keywords in self._intent_tags.items():
            score = sum(1 for kw in keywords if kw.lower() in lowered)
            if score > best_score:
                best_intent = intent
                best_score = score
        return best_intent

    def _is_high_risk(self, text: str, intent: str) -> bool:
        lowered = text.lower()
        topic_match = any(topic in lowered for topic in self._high_risk_topics)
        return topic_match or intent in {"battery_fire", "conflict"}

    async def _format_with_llm(
        self, *, text: str, context: str, mode: str = "chat"
    ) -> str | None:
        if self._router is None or not self._router.providers:
            return None

        messages = [
            {
                "role": "system",
                "content": (
                    self._system_prompt
                    + "\n\n"
                    + self._style_guide
                    + "\n\n"
                    + ("Контекст:\n" + context if context else "")
                ).strip(),
            },
            {"role": "user", "content": text},
        ]
        try:
            resp = await self._router.complete(messages, mode=mode, temperature=0.2)
            return resp.text.strip()
        except Exception as exc:
            log.warning("llm_call_failed", mode=mode, error=str(exc))
            return None

    async def get_answer(self, user_id: int, text: str) -> AICourierResult:
        question = (text or "").strip()
        intent = self.detect_intent(question)
        high_risk = self._is_high_risk(question, intent)
        evidence: list[str] = []
        debug: dict[str, Any] = {"high_risk": high_risk}

        # 1) RULE layer (optional)
        if self._rule_reply_fn is not None:
            try:
                quick = self._rule_reply_fn(question)
                if quick:
                    result = AICourierResult(
                        text=str(quick),
                        route="rule",
                        confidence=0.9,
                        intent=intent,
                        need_clarify=False,
                        clarify_question="",
                        escalate=False,
                        evidence=["rule_based"],
                        debug=debug,
                    )
                    log.info("ai_explainability", user_id=user_id, **asdict(result))
                    return result
            except Exception as exc:
                debug["rule_error"] = str(exc)

        # 2) FAQ search
        faq_hits: list[dict[str, Any]] = []
        try:
            async with self._session_factory() as session:
                faq_hits = await self._faq_repo.search(
                    session=session,
                    text=question,
                    tags=[intent] if intent != "unknown" else None,
                    top_k=3,
                )
            if faq_hits:
                evidence.append(f"faq:{faq_hits[0]['id']}")
                debug["faq_top_score"] = faq_hits[0]["score"]
        except Exception as exc:
            debug["faq_error"] = str(exc)

        # 3) FAQ confident answer (+ optional LLM formatting)
        if faq_hits and float(faq_hits[0]["score"]) >= self._faq_threshold:
            faq_answer = str(faq_hits[0]["a"])
            formatted = await self._format_with_llm(
                text=question,
                context=f"FAQ answer:\n{faq_answer}",
                mode="chat",
            )
            result = AICourierResult(
                text=formatted or faq_answer,
                route="faq",
                confidence=min(1.0, float(faq_hits[0]["score"])),
                intent=intent,
                need_clarify=False,
                clarify_question="",
                escalate=False,
                evidence=evidence or ["faq"],
                debug=debug,
            )
            log.info("ai_explainability", user_id=user_id, **asdict(result))
            return result

        # 4) LLM reason mode + one clarify
        llm_text = await self._format_with_llm(text=question, context="", mode="reason")
        if llm_text:
            need_clarify = intent in self._clarify_questions
            clarify_q = self._clarify_questions.get(intent, "") if need_clarify else ""
            result = AICourierResult(
                text=llm_text,
                route="llm_reason",
                confidence=0.62,
                intent=intent,
                need_clarify=need_clarify,
                clarify_question=clarify_q,
                escalate=high_risk and not need_clarify,
                evidence=evidence or ["llm_reason"],
                debug=debug,
            )
            log.info("ai_explainability", user_id=user_id, **asdict(result))
            return result

        # 5) No LLM -> policy fallback
        fallback = self._fallbacks.get("no_llm") or self._fallbacks.get("generic") or (
            "Понял. Я помогу. Опиши ситуацию коротко, и я дам шаги."
        )
        clarify_q = self._clarify_questions.get(intent, "")
        result = AICourierResult(
            text=fallback,
            route="fallback",
            confidence=0.25,
            intent=intent,
            need_clarify=bool(clarify_q),
            clarify_question=clarify_q,
            escalate=high_risk and not bool(clarify_q),
            evidence=evidence or ["fallback"],
            debug=debug,
        )
        log.info("ai_explainability", user_id=user_id, **asdict(result))
        return result
