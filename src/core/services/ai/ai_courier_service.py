from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

import structlog
from sqlalchemy.ext.asyncio import async_sessionmaker

from src.core.services.ai.case_classifier import (
    CaseClassifier,
    STRONG_MATCH_THRESHOLD,
    SimilarCaseResult,
)
from src.core.services.ai.case_engine import CaseEngine
from src.core.services.ai.embeddings_service import EmbeddingsService
from src.core.services.ai.intent_engine import IntentDetectionResult, IntentEngine
from src.core.services.ai.provider_router import ProviderRouter
from src.core.services.ai.rag_service import RAGKnowledgeContext, RAGService
from src.core.services.risk import RecommendationEngine, RiskEngine, RiskInput
from src.infra.db.repositories.faq_repo import FAQRepository

log = structlog.get_logger(__name__)


@dataclass
class AnswerContext:
    """Inputs for regulation-first final answer. LLM only formats; rules dominate."""

    intent: str
    must_match_result: dict[str, Any] | None
    faq_result: dict[str, Any] | None
    semantic_faq: bool
    case_memory_result: SimilarCaseResult | None
    case_engine_result: Any
    escalation_signal: bool
    high_risk: bool


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
    _STRICT_INTENTS_DEFAULT = {
        "battery_fire",
        "contact_customer",
        "damaged_goods",
        "late_delivery",
        "missing_items",
    }

    def __init__(
        self,
        session_factory: async_sessionmaker,
        router: ProviderRouter | None = None,
        data_root: str | Path = "data/ai",
    ) -> None:
        self._session_factory = session_factory
        self._router = router
        self._faq_repo = FAQRepository()
        self._case_engine = CaseEngine()
        self._data_root = Path(data_root)
        self._case_classifier = CaseClassifier(data_root=self._data_root)
        self._embeddings_service = EmbeddingsService()

        self._policy = self._load_json("core_policy.json", default={})
        self._intent_tags = self._load_json("intent_tags.json", default={})
        intents_catalog_text = self._load_text("intents_catalog.json", default="")
        intents_catalog = IntentEngine.parse_intents_catalog_text(intents_catalog_text)
        self._intent_engine = IntentEngine(
            router=self._router,
            intent_tags=self._intent_tags,
            intents_catalog=intents_catalog,
        )
        self._clarify_questions = self._load_json(
            "prompts/clarify_questions.json", default={}
        )
        self._system_prompt = self._load_text("prompts/system_prompt.md", default="")
        self._style_guide = self._load_text("prompts/style_guide.md", default="")

        self._fallbacks = self._policy.get("fallbacks", {})
        self._faq_threshold = float(self._policy.get("routing", {}).get("faq_threshold", 0.72))
        self._faq_strong_threshold = float(
            self._policy.get("routing", {}).get("faq_strong_threshold", 0.6)
        )
        self._clarify_questions = self._normalize_intent_mapping(self._clarify_questions)
        self._high_risk_topics = [
            str(x).lower() for x in self._policy.get("high_risk_topics", [])
        ]
        self._must_match_cases = list(self._policy.get("must_match_cases", []))
        self._strict_intents = {
            self._intent_engine.normalize_intent(str(x).lower())
            for x in self._policy.get("routing", {}).get(
                "strict_intents", list(self._STRICT_INTENTS_DEFAULT)
            )
            if self._intent_engine.normalize_intent(str(x).lower()) != "unknown"
        }

        self._rule_reply_fn = self._resolve_rule_reply_fn()
        self._risk_engine = RiskEngine()
        self._recommendation_engine = RecommendationEngine()
        self._rag_service = RAGService(
            session_factory=self._session_factory,
            data_root=self._data_root,
            core_policy=self._policy,
            intent_tags=self._intent_tags,
            intents_catalog=intents_catalog,
        )

    def reload_policy(self) -> None:
        self._policy = self._load_json("core_policy.json", default={})
        self._intent_tags = self._load_json("intent_tags.json", default={})
        intents_catalog_text = self._load_text("intents_catalog.json", default="")
        intents_catalog = IntentEngine.parse_intents_catalog_text(intents_catalog_text)
        self._intent_engine = IntentEngine(
            router=self._router,
            intent_tags=self._intent_tags,
            intents_catalog=intents_catalog,
        )
        self._clarify_questions = self._load_json(
            "prompts/clarify_questions.json", default={}
        )
        self._system_prompt = self._load_text("prompts/system_prompt.md", default="")
        self._style_guide = self._load_text("prompts/style_guide.md", default="")
        self._fallbacks = self._policy.get("fallbacks", {})
        self._faq_threshold = float(
            self._policy.get("routing", {}).get("faq_threshold", 0.72)
        )
        self._faq_strong_threshold = float(
            self._policy.get("routing", {}).get("faq_strong_threshold", 0.6)
        )
        self._clarify_questions = self._normalize_intent_mapping(self._clarify_questions)
        self._high_risk_topics = [
            str(x).lower() for x in self._policy.get("high_risk_topics", [])
        ]
        self._must_match_cases = list(self._policy.get("must_match_cases", []))
        self._strict_intents = {
            self._intent_engine.normalize_intent(str(x).lower())
            for x in self._policy.get("routing", {}).get(
                "strict_intents", list(self._STRICT_INTENTS_DEFAULT)
            )
            if self._intent_engine.normalize_intent(str(x).lower()) != "unknown"
        }

    def _resolve_rule_reply_fn(self) -> None:
        """Optional quick-reply builder; module ai_response_service not in use. Returns None."""
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

    def _normalize_intent_mapping(self, mapping: dict[str, str]) -> dict[str, str]:
        normalized: dict[str, str] = {}
        for raw_intent, value in mapping.items():
            canonical_intent = self._intent_engine.normalize_intent(raw_intent)
            if canonical_intent == "unknown" and str(raw_intent).strip().lower() != "unknown":
                continue
            normalized[canonical_intent] = value
        return normalized

    @staticmethod
    def _debug_with_route_decision(debug: dict[str, Any], route_decision: str) -> dict[str, Any]:
        return debug | {"route_decision": route_decision}

    def detect_intent(self, text: str) -> str:
        return self._intent_engine.detect_from_rules(text).intent

    def _is_high_risk(self, text: str, intent: str) -> bool:
        lowered = text.lower()
        topic_match = any(topic in lowered for topic in self._high_risk_topics)
        return topic_match or intent in {"battery_fire", "rude_communication"}

    def get_risk_recommendation(self, risk_input: RiskInput) -> AICourierResult:
        """Проактивная оценка риска доставки: вызов risk_engine + recommendation_engine, ответ в RAG-формате."""
        risk = self._risk_engine.evaluate(risk_input)
        if risk is None:
            text = (
                "Ситуация:\nПо текущим данным рисков доставки не выявлено.\n\n"
                "Что делать сейчас:\n1) Следуй регламенту в приложении.\n\n"
                "Когда писать куратору:\nПри необходимости по регламенту."
            )
            return AICourierResult(
                text=text,
                route="delivery_risk",
                confidence=0.0,
                intent="delivery_risk",
                need_clarify=False,
                clarify_question="",
                escalate=False,
                evidence=[],
                debug={"risk_evaluated": True, "risk_detected": False},
            )
        rec = self._recommendation_engine.recommend(risk)
        if rec is None:
            text = self._format_rag_answer(
                risk.risk_type,
                ["Связаться с куратором"],
                "При необходимости по регламенту.",
                high_risk=risk.severity == "high",
            )
        else:
            when = "Сразу сообщи куратору при сохранении риска или по регламенту." if rec.escalate else "При необходимости по регламенту."
            text = self._format_rag_answer(
                rec.short_message,
                rec.action_steps,
                when,
                high_risk=rec.escalate,
            )
        log.info(
            "risk_recommendation",
            risk_type=risk.risk_type,
            severity=risk.severity,
            escalate=rec.escalate if rec else False,
        )
        return AICourierResult(
            text=text,
            route="delivery_risk",
            confidence=risk.risk_score,
            intent="delivery_risk",
            need_clarify=False,
            clarify_question="",
            escalate=rec.escalate if rec else False,
            evidence=[f"risk:{risk.risk_type}"],
            debug={
                "risk_type": risk.risk_type,
                "severity": risk.severity,
                "risk_reasons": risk.risk_reasons,
            },
        )

    @staticmethod
    def _tokenize(text: str) -> set[str]:
        return {
            token
            for token in re.findall(r"[0-9a-zA-Zа-яА-ЯёЁ]+", (text or "").lower())
            if len(token) >= 2
        }

    def _match_must_case(self, text: str, intent: str) -> dict[str, Any] | None:
        lowered = (text or "").strip().lower()
        if not lowered or not self._must_match_cases:
            return None

        user_tokens = self._tokenize(lowered)
        best_case: dict[str, Any] | None = None
        best_score = 0.0

        for case in self._must_match_cases:
            trigger = str(case.get("trigger", "")).strip().lower()
            keywords = [str(x).strip().lower() for x in case.get("keywords", []) if str(x).strip()]
            case_intents = {
                self._intent_engine.normalize_intent(str(x).strip().lower())
                for x in case.get("intents", [])
                if str(x).strip()
            }
            trigger_tokens = self._tokenize(trigger)
            keyword_tokens = self._tokenize(" ".join(keywords))

            direct_hit = bool(trigger) and trigger in lowered
            keyword_hit = any(keyword in lowered for keyword in keywords)
            intent_hit = intent != "unknown" and intent in case_intents
            overlap_tokens = user_tokens.intersection(trigger_tokens | keyword_tokens)
            overlap = len(overlap_tokens)
            ref_len = max(1, len(trigger_tokens or keyword_tokens))
            overlap_ratio = overlap / ref_len

            score = 0.0
            if direct_hit:
                score += 1.0
            if keyword_hit:
                score += 0.75
            if intent_hit:
                score += 0.45
            score += min(0.35, overlap_ratio * 0.35)

            strong_match = (
                direct_hit
                or (intent_hit and keyword_hit)
                or (intent_hit and overlap >= 2)
                or (keyword_hit and overlap >= 2)
            )
            if strong_match and score > best_score:
                best_case = case
                best_score = score

        return best_case

    def _faq_effective_score(
        self, question: str, intent: str, top_hit: dict[str, Any]
    ) -> tuple[float, dict[str, Any]]:
        raw_score = float(top_hit.get("score", 0.0))
        faq_question = str(top_hit.get("question") or "")
        faq_answer = str(top_hit.get("answer") or "")
        faq_tag = self._intent_engine.normalize_intent(top_hit.get("tag"))

        query_tokens = self._tokenize(question)
        faq_tokens = self._tokenize(faq_question)
        answer_tokens = self._tokenize(faq_answer)

        token_overlap = len(query_tokens.intersection(faq_tokens | answer_tokens))
        question_overlap = len(query_tokens.intersection(faq_tokens))
        bonus = 0.0
        reasons: list[str] = []

        if faq_tag and faq_tag == intent:
            bonus += 0.12
            reasons.append("intent_tag_match")
        if token_overlap >= 3:
            bonus += 0.08
            reasons.append("token_overlap>=3")
        elif question_overlap >= 2:
            bonus += 0.05
            reasons.append("question_overlap>=2")
        if intent in self._strict_intents and faq_tag == intent:
            bonus += 0.08
            reasons.append("strict_intent_bonus")

        return min(1.0, raw_score + bonus), {
            "faq_raw_score": raw_score,
            "faq_bonus": round(bonus, 4),
            "faq_bonus_reasons": reasons,
            "faq_top_tag": faq_tag,
        }

    @staticmethod
    def _normalize_reply(text: str) -> str:
        lines = [line.strip() for line in str(text).splitlines() if line.strip()]
        return "\n".join(lines).strip()

    @staticmethod
    def _steps_from_text(text: str) -> list[str]:
        """Extract numbered steps from '1) ... 2) ...' or '1. ...' style text."""
        if not (text or "").strip():
            return []
        steps: list[str] = []
        for line in str(text).splitlines():
            line = line.strip()
            if not line:
                continue
            # Match "1) step" or "1. step" or "1)step"
            if re.match(r"^\d+[).]\s*", line):
                steps.append(re.sub(r"^\d+[).]\s*", "", line).strip())
            elif not steps and line:
                steps.append(line)
        return steps if steps else [line.strip() for line in str(text).splitlines() if line.strip()]

    _INTENT_SITUATION: dict[str, str] = {
        "damaged_goods": "Повреждение товара при доставке.",
        "damage": "Повреждение товара при доставке.",
        "contact_customer": "Нет связи с клиентом / домофон.",
        "missing_items": "Недовоз / не хватает части заказа.",
        "late_delivery": "Опоздание / задержка доставки.",
        "battery_fire": "Риск по АКБ / дым, нагрев.",
        "payment_terminal": "Проблема с терминалом оплаты.",
        "payment_hyperlink": "Оплата по ссылке.",
        "rude_communication": "Жалоба на общение.",
        "leave_at_door": "Оставить у двери по запросу.",
        "return_order": "Возврат заказа.",
    }

    def _format_rag_answer(
        self,
        situation: str,
        steps: list[str],
        when_escalate: str,
        *,
        high_risk: bool = False,
    ) -> str:
        """Build regulation-first RAG answer: Ситуация / Что делать сейчас / Когда писать куратору."""
        situation = (situation or "").strip() or "Операционная ситуация по доставке."
        when_escalate = (when_escalate or "").strip() or "При необходимости по регламенту."
        if not steps:
            steps = ["Следуй регламенту в приложении. При сомнениях — куратору."]

        steps_block = "\n".join(f"{i}) {s}" for i, s in enumerate(steps, start=1))
        if high_risk:
            return (
                "Критично: " + situation + "\n\n"
                "Действия:\n" + steps_block + "\n\n"
                "Немедленно сообщи куратору: " + when_escalate
            )
        return (
            "Ситуация:\n" + situation + "\n\n"
            "Что делать сейчас:\n" + steps_block + "\n\n"
            "Когда писать куратору:\n" + when_escalate
        )

    def _build_rag_answer(
        self,
        *,
        must_rule: dict[str, Any] | None = None,
        faq_top: dict[str, Any] | None = None,
        ml_case: SimilarCaseResult | None = None,
        case_engine_result: Any = None,
        intent: str = "unknown",
        escalate: bool = False,
        high_risk: bool = False,
        context: AnswerContext | None = None,
    ) -> str:
        """Compose final answer from first available evidence (regulation-first).
        Priority: must_rule > case_engine > faq_top > ml_case. LLM is not used here."""
        when_escalate = "При необходимости по регламенту."
        if escalate or high_risk:
            when_escalate = "Сразу сообщи куратору при сохранении риска или по регламенту."

        if must_rule:
            trigger = str(must_rule.get("trigger") or "").strip()
            situation = trigger or self._INTENT_SITUATION.get(intent, "Операционный кейс.")
            raw = self._build_must_match_reply(
                must_rule, high_risk=high_risk, intent=intent
            )
            steps = self._steps_from_text(raw)
            if must_rule.get("escalate") or (high_risk and intent == "battery_fire"):
                when_escalate = "Сразу сообщи куратору/ответственному."
            return self._format_rag_answer(situation, steps, when_escalate, high_risk=high_risk)

        if case_engine_result is not None:
            situation = self._INTENT_SITUATION.get(
                intent, (getattr(case_engine_result, "route", None) or intent) + "."
            )
            steps = self._steps_from_text(
                getattr(case_engine_result, "answer", "") or ""
            )
            if getattr(case_engine_result, "escalate", False):
                when_escalate = "Сразу куратору по регламенту."
            return self._format_rag_answer(situation, steps, when_escalate, high_risk=high_risk)

        if faq_top:
            q = str(faq_top.get("question") or "").strip()
            situation = q or self._INTENT_SITUATION.get(intent, "Вопрос по доставке.")
            steps = self._steps_from_text(str(faq_top.get("answer") or ""))
            return self._format_rag_answer(situation, steps, when_escalate, high_risk=high_risk)

        if ml_case:
            situation = (ml_case.input or ml_case.label or intent or "").strip() or "Похожий кейс."
            steps = self._steps_from_text(ml_case.decision or ml_case.explanation or "")
            return self._format_rag_answer(situation, steps, when_escalate, high_risk=high_risk)

        return self._format_rag_answer(
            self._INTENT_SITUATION.get(intent, "Ситуация не распознана."),
            ["Опиши ситуацию коротко — дам шаги по регламенту."],
            when_escalate,
            high_risk=high_risk,
        )

    def _build_must_match_reply(
        self, case: dict[str, Any], *, high_risk: bool, intent: str
    ) -> str:
        response = self._normalize_reply(str(case.get("response") or ""))
        if response:
            return response

        actions = [str(x).strip() for x in case.get("actions", []) if str(x).strip()]
        if not actions:
            fallback = self._fallbacks.get("generic") or "Опиши ситуацию коротко."
            return self._normalize_reply(fallback)

        lines = [f"{idx}) {action}" for idx, action in enumerate(actions, start=1)]
        if high_risk and intent in {"battery_fire", "rude_communication"}:
            lines.append("Если риск для безопасности сохраняется — сразу сообщи куратору.")
        return "\n".join(lines)

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
        intent = "unknown"
        high_risk = False
        evidence: list[str] = []
        debug: dict[str, Any] = {}
        intent_result = IntentDetectionResult(intent="unknown", confidence=0.0, matched_keywords=[])
        faq_hits: list[dict[str, Any]] = []

        try:
            async with self._session_factory() as session:
                intent_result = await self._intent_engine.detect(
                    question,
                    faq_repo=self._faq_repo,
                    session=session,
                )
                intent = intent_result.intent
                high_risk = self._is_high_risk(question, intent)
                debug = {
                    "high_risk": high_risk,
                    "intent": intent,
                    "intent_confidence": intent_result.confidence,
                    "matched_keywords": intent_result.matched_keywords,
                    "matched_catalog_intent": intent_result.matched_catalog_intent,
                }
                log.info(
                    "intent_detected",
                    intent=intent,
                    intent_confidence=intent_result.confidence,
                    matched_keywords=intent_result.matched_keywords,
                    matched_catalog_intent=intent_result.matched_catalog_intent,
                )
        except Exception as exc:
            debug = {
                "high_risk": high_risk,
                "intent": intent,
                "intent_confidence": intent_result.confidence,
                "matched_keywords": intent_result.matched_keywords,
                "matched_catalog_intent": intent_result.matched_catalog_intent,
                "intent_engine_error": str(exc),
            }

        # 1) Must-match layer for strict operational cases
        must_case = self._match_must_case(question, intent)
        if must_case is not None:
            response = self._build_rag_answer(
                must_rule=must_case,
                intent=intent,
                escalate=bool(must_case.get("escalate", high_risk and intent == "battery_fire")),
                high_risk=high_risk,
            )
            result = AICourierResult(
                text=response,
                route="must_match",
                confidence=float(must_case.get("confidence", 0.96)),
                intent=intent,
                need_clarify=False,
                clarify_question="",
                escalate=bool(must_case.get("escalate", high_risk and intent == "battery_fire")),
                evidence=[f"must_match:{must_case.get('id') or must_case.get('trigger') or intent}"],
                debug=self._debug_with_route_decision(
                    debug | {"must_match_trigger": must_case.get("trigger", "")},
                    f"must_match:{must_case.get('id') or intent}",
                ),
            )
            log.info("ai_explainability", user_id=user_id, **asdict(result))
            return result

        # 2) Case engine for typical courier situations
        case_result = self._case_engine.resolve(
            intent=intent,
            confidence=float(intent_result.confidence),
            clarify_question=self._clarify_questions.get(intent, ""),
        )
        if case_result is not None:
            rag_text = self._build_rag_answer(
                case_engine_result=case_result,
                intent=intent,
                escalate=case_result.escalate,
                high_risk=high_risk,
            )
            result = AICourierResult(
                text=rag_text,
                route=case_result.route,
                confidence=max(0.78, float(intent_result.confidence)),
                intent=intent,
                need_clarify=case_result.need_clarify,
                clarify_question=case_result.clarify_question,
                escalate=case_result.escalate,
                evidence=evidence or [f"case:{intent}"],
                debug=self._debug_with_route_decision(debug, f"case_engine:{intent}"),
            )
            log.info("ai_explainability", user_id=user_id, **asdict(result))
            return result

        # 3) FAQ: must_match → keyword → semantic → LLM (hybrid retrieval)
        faq_hits = []
        retrieval_stage = "none"
        semantic_hit = False
        semantic_score = 0.0
        query_embedding_literal: str | None = None
        query_embedding_list: list[float] | None = None  # for ML case semantic step
        faq_tag = self._intent_engine.faq_tag_for_intent(intent)
        try:
            async with self._session_factory() as session:
                # 3a) Keyword search first
                keyword_hits = await self._faq_repo.search_by_keywords(
                    query=question,
                    limit=5,
                    tag=faq_tag,
                    session=session,
                )
                if keyword_hits:
                    effective_score, faq_debug = self._faq_effective_score(
                        question, intent, keyword_hits[0]
                    )
                    debug.update(faq_debug)
                    debug["faq_top_score"] = keyword_hits[0].get("score", 0.0)
                    debug["faq_top_id"] = keyword_hits[0].get("id")
                    debug["faq_text_score"] = keyword_hits[0].get("text_score", 0.0)
                    debug["faq_keyword_score"] = keyword_hits[0].get("score", 0.0)
                    debug["faq_semantic_score"] = keyword_hits[0].get("semantic_score", 0.0)
                    strong_keyword = effective_score >= self._faq_threshold or (
                        effective_score >= self._faq_strong_threshold
                        and intent in self._strict_intents
                        and (
                            faq_debug.get("faq_top_tag") == intent
                            or "token_overlap>=3" in faq_debug.get("faq_bonus_reasons", [])
                        )
                    )
                    if strong_keyword:
                        retrieval_stage = "keyword"
                        faq_hits = keyword_hits
                # 3b) If keyword not strong, try semantic search
                if retrieval_stage != "keyword":
                    query_embedding = await self._embeddings_service.embed_text(question)
                    query_embedding_list = query_embedding
                    query_embedding_literal = self._embeddings_service.serialize_embedding(
                        query_embedding
                    )
                    if query_embedding_literal:
                        semantic_hits = await self._faq_repo.search_semantic(
                            query_embedding=query_embedding_literal,
                            limit=5,
                            tag=faq_tag,
                            session=session,
                        )
                        if semantic_hits:
                            top_sem = semantic_hits[0]
                            sem_score = float(top_sem.get("score", 0.0))
                            semantic_score = sem_score
                            semantic_hit = True
                            debug["semantic_score"] = round(sem_score, 4)
                            debug["semantic_hit"] = True
                            debug["faq_text_score"] = top_sem.get("text_score", 0.0)
                            debug["faq_keyword_score"] = top_sem.get("keyword_score", 0.0)
                            debug["faq_semantic_score"] = top_sem.get("semantic_score", sem_score)
                            if sem_score >= self._faq_threshold:
                                retrieval_stage = "semantic_faq"
                                faq_hits = semantic_hits
                                effective_score = sem_score
                                debug["faq_top_score"] = sem_score
                                debug["faq_top_id"] = top_sem.get("id")
                    # 3c) Fallback: hybrid (keyword + text) for context if still no strong hit
                    if retrieval_stage == "none" and not faq_hits:
                        faq_hits = await self._faq_repo.search_hybrid(
                            session=session,
                            query=question,
                            limit=3,
                            tag=faq_tag,
                            query_embedding=query_embedding_literal if query_embedding_literal else None,
                        )
                        if faq_hits:
                            effective_score, faq_debug = self._faq_effective_score(
                                question, intent, faq_hits[0]
                            )
                            debug.update(faq_debug)
                            debug["faq_top_score"] = faq_hits[0].get("score", 0.0)
                            debug["faq_top_id"] = faq_hits[0].get("id")
                            debug["faq_text_score"] = faq_hits[0].get("text_score", 0.0)
                            debug["faq_keyword_score"] = faq_hits[0].get("keyword_score", 0.0)
                            debug["faq_semantic_score"] = faq_hits[0].get("semantic_score", 0.0)
                debug["retrieval_stage"] = retrieval_stage
                debug["semantic_hit"] = semantic_hit
                debug["semantic_score"] = round(semantic_score, 4)
        except Exception as exc:
            debug["faq_error"] = str(exc)

        effective_score = 0.0
        if faq_hits:
            effective_score, faq_debug = self._faq_effective_score(question, intent, faq_hits[0])
            debug.update(faq_debug)
            evidence.append(f"faq:{faq_hits[0]['id']}")
            log.info(
                "faq_search_result",
                faq_top_score=round(float(faq_hits[0].get("score", 0.0)), 4),
                faq_top_id=faq_hits[0].get("id"),
                faq_evidence_source=f"faq:{faq_hits[0]['id']}",
                faq_text_score=round(float(faq_hits[0].get("text_score", 0.0)), 4),
                faq_keyword_score=round(float(faq_hits[0].get("keyword_score", 0.0)), 4),
                faq_semantic_score=round(float(faq_hits[0].get("semantic_score", semantic_score)), 4),
                semantic_score=round(semantic_score, 4),
                semantic_hit=semantic_hit,
                retrieval_stage=retrieval_stage,
            )

        # 3.5) Case memory (ml_cases): подключаем ПОСЛЕ FAQ retrieval.
        # Guardrail: case memory не может переопределить must_match, и не подменяет сильный FAQ;
        # используется либо как evidence/explainability, либо как отдельный route semantic_case (см. ниже).
        matched_case: SimilarCaseResult | None = self._case_classifier.find_similar_case(question)
        if matched_case is not None:
            debug["case_id"] = matched_case.case_id
            debug["case_label"] = matched_case.label
            debug["case_similarity"] = matched_case.similarity_score
            debug["case_decision"] = matched_case.decision
            debug["case_explanation"] = matched_case.explanation
            if matched_case.similarity_score >= STRONG_MATCH_THRESHOLD:
                evidence.append(f"case_memory:{matched_case.case_id}")

        strong_faq_match = faq_hits and (
            effective_score >= self._faq_threshold
            or (
                effective_score >= self._faq_strong_threshold
                and intent in self._strict_intents
                and (
                    debug.get("faq_top_tag") == intent
                    or "token_overlap>=3" in debug.get("faq_bonus_reasons", [])
                )
            )
        )
        if strong_faq_match:
            route_label = "semantic_faq" if retrieval_stage == "semantic_faq" else "faq"
            faq_answer = self._build_rag_answer(
                faq_top=faq_hits[0],
                intent=intent,
                escalate=False,
                high_risk=high_risk,
            )
            result = AICourierResult(
                text=faq_answer,
                route=route_label,
                confidence=effective_score,
                intent=intent,
                need_clarify=False,
                clarify_question="",
                escalate=False,
                evidence=evidence or ["faq"],
                debug=self._debug_with_route_decision(
                    debug | {"retrieval_stage": retrieval_stage, "semantic_score": semantic_score, "semantic_hit": semantic_hit},
                    "faq_search",
                ),
            )
            log.info(
                "ai_explainability",
                user_id=user_id,
                route=route_label,
                semantic_score=round(semantic_score, 4),
                semantic_hit=semantic_hit,
                retrieval_stage=retrieval_stage,
                **asdict(result),
            )
            return result

        # 4) ML case semantic: strong similarity over ml_cases (additive to case_engine/FAQ)
        if self._case_classifier.has_semantic:
            embed_for_case = query_embedding_list
            if embed_for_case is None and self._embeddings_service.enabled:
                embed_for_case = await self._embeddings_service.embed_text(question)
            if embed_for_case:
                sem_case = self._case_classifier.find_similar_case_semantic(embed_for_case)
                if (
                    sem_case is not None
                    and sem_case.similarity_score >= STRONG_MATCH_THRESHOLD
                ):
                    reply = self._build_rag_answer(
                        ml_case=sem_case,
                        intent=intent,
                        escalate=False,
                        high_risk=high_risk,
                    )
                    if reply:
                        result = AICourierResult(
                            text=reply,
                            route="semantic_case",
                            confidence=sem_case.similarity_score,
                            intent=intent,
                            need_clarify=False,
                            clarify_question="",
                            escalate=False,
                            evidence=evidence or [f"semantic_case:{sem_case.case_id}"],
                            debug=self._debug_with_route_decision(
                                debug
                                | {
                                    "case_id": sem_case.case_id,
                                    "case_label": sem_case.label,
                                    "case_similarity": sem_case.similarity_score,
                                    "case_decision": sem_case.decision,
                                    "case_explanation": sem_case.explanation,
                                },
                                f"semantic_case:{sem_case.case_id}",
                            ),
                        )
                        log.info("ai_explainability", user_id=user_id, **asdict(result))
                        return result

        # 5) LLM: only format from evidence; do not invent operational rules
        has_evidence = bool(evidence or faq_hits or matched_case)
        answer_ctx = AnswerContext(
            intent=intent,
            must_match_result=None,
            faq_result=faq_hits[0] if faq_hits else None,
            semantic_faq=(retrieval_stage == "semantic_faq"),
            case_memory_result=matched_case,
            case_engine_result=None,
            escalation_signal=high_risk,
            high_risk=high_risk,
        )
        rag_ctx: RAGKnowledgeContext | None = None
        try:
            rag_ctx = await self._rag_service.build_context(question)
        except Exception as exc:  # pragma: no cover - защитный слой
            log.warning("rag_context_failed", error=str(exc))

        llm_context_parts: list[str] = [
            "Входы для ответа: intent=%s, эскалация=%s, high_risk=%s"
            % (intent, high_risk, high_risk),
        ]
        if faq_hits:
            for hit in faq_hits[:2]:
                llm_context_parts.append(
                    "FAQ (score=%.2f): Q: %s | A: %s"
                    % (
                        float(hit.get("score", 0.0)),
                        (hit.get("question") or "")[:200],
                        (hit.get("answer") or "")[:300],
                    )
                )
        if matched_case:
            llm_context_parts.append(
                "Case memory: %s -> %s"
                % (matched_case.label or "", (matched_case.decision or "")[:200])
            )
        if rag_ctx is not None and rag_ctx.context_text:
            llm_context_parts.append(
                "RAG-контекст знаний (intent=%s, retrieval_stage=%s):\n%s"
                % (
                    rag_ctx.intent.intent,
                    rag_ctx.retrieval_stage,
                    rag_ctx.context_text[:2000],
                )
            )
        llm_context_parts.append(
            "Строго: используй ТОЛЬКО факты выше. Не придумывай регламентов. "
            "Формат ответа обязательно: Ситуация: ... Что делать сейчас: 1) ... 2) ... Когда писать куратору: ..."
        )
        if high_risk:
            llm_context_parts.append(
                "Критичная ситуация: используй формат Критично: ... Действия: ... Немедленно сообщи куратору: ..."
            )

        llm_text = await self._format_with_llm(
            text=question,
            context="\n\n".join(llm_context_parts),
            mode="reason",
        )
        if llm_text:
            # At most one clarification when evidence is weak
            need_clarify = (
                not has_evidence
                and intent in self._clarify_questions
                and not high_risk
            )
            clarify_q = self._clarify_questions.get(intent, "") if need_clarify else ""
            # Enforce RAG format: if LLM didn't follow structure, wrap
            text_lower = (llm_text or "").lower()
            if "ситуация" not in text_lower and "что делать" not in text_lower:
                situation = self._INTENT_SITUATION.get(intent, "Операционный кейс.")
                steps = self._steps_from_text(llm_text)
                llm_text = self._format_rag_answer(
                    situation, steps, "При необходимости по регламенту.", high_risk=high_risk
                )
            result = AICourierResult(
                text=self._normalize_reply(llm_text),
                route="llm_reason",
                confidence=0.62 if has_evidence else 0.45,
                intent=intent,
                need_clarify=need_clarify,
                clarify_question=clarify_q,
                escalate=high_risk and not need_clarify,
                evidence=evidence or ["llm_reason"],
                debug=self._debug_with_route_decision(
                    debug | {"answer_context_intent": answer_ctx.intent}, "llm_reason"
                ),
            )
            log.info("ai_explainability", user_id=user_id, **asdict(result))
            return result

        # 6) Fallback only for true unknown: no strong evidence, LLM unavailable or no answer
        fallback = self._fallbacks.get("no_llm") or self._fallbacks.get("generic") or (
            "Понял. Я помогу. Опиши ситуацию коротко, и я дам шаги."
        )
        # At most one clarification
        clarify_q = self._clarify_questions.get(intent, "") if not high_risk else ""
        result = AICourierResult(
            text=fallback,
            route="fallback",
            confidence=0.25,
            intent=intent,
            need_clarify=bool(clarify_q),
            clarify_question=clarify_q,
            escalate=high_risk and not bool(clarify_q),
            evidence=evidence or ["fallback"],
            debug=self._debug_with_route_decision(debug, "fallback"),
        )
        log.info("ai_explainability", user_id=user_id, **asdict(result))
        return result
