from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping, Sequence

import structlog
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.core.services.ai.case_classifier import (
    CaseClassifier,
    SimilarCaseResult,
)
from src.core.services.ai.embeddings_service import EmbeddingsService
from src.core.services.ai.intent_engine import (
    IntentDetectionResult,
    IntentEngine,
)
from src.infra.db.repositories.faq_repo import FAQRepository


log = structlog.get_logger(__name__)


@dataclass(slots=True)
class RAGKnowledgeContext:
    """Единый контекст знаний для LLM.

    Используется как часть RAG-слоя: intent → FAQ → кейсы → регламенты.
    """

    question: str
    intent: IntentDetectionResult
    high_risk: bool

    faq_hits: list[dict[str, Any]] = field(default_factory=list)
    faq_tag: str | None = None
    retrieval_stage: str = "none"  # keyword / semantic / hybrid / none

    case_lexical: SimilarCaseResult | None = None
    case_semantic: SimilarCaseResult | None = None

    regulations: list[dict[str, Any]] = field(default_factory=list)

    context_text: str = ""  # Готовая строка контекста для LLM


class RAGService:
    """Унифицированный retrieval-слой для AI-куратора.

    Обязанности:
    - определить intent пользователя;
    - найти релевантные FAQ (семантика + гибридный поиск);
    - найти похожие ML-кейсы (лексика + опционально семантика);
    - подобрать связанные регламенты (must_match_cases из core_policy);
    - собрать удобный для LLM текстовый контекст.
    """

    def __init__(
        self,
        *,
        session_factory: async_sessionmaker,
        data_root: str | Path = "data/ai",
        core_policy: Mapping[str, Any] | None = None,
        intent_tags: Mapping[str, Sequence[str]] | None = None,
        intents_catalog: Sequence[Mapping[str, Any]] | None = None,
    ) -> None:
        self._session_factory = session_factory
        self._data_root = Path(data_root)

        # Загрузка конфигурации знаний
        self._policy = dict(core_policy or self._load_json("core_policy.json", default={}))
        self._intent_tags = dict(intent_tags or self._load_json("intent_tags.json", default={}))
        intents_catalog_text = self._load_text("intents_catalog.json", default="")
        parsed_catalog = (
            list(intents_catalog)
            if intents_catalog is not None
            else IntentEngine.parse_intents_catalog_text(intents_catalog_text)
        )

        self._intent_engine = IntentEngine(
            router=None,
            intent_tags=self._intent_tags,
            intents_catalog=parsed_catalog,
        )

        self._faq_repo = FAQRepository()
        self._case_classifier = CaseClassifier(data_root=self._data_root)
        self._embeddings_service = EmbeddingsService()

        self._high_risk_topics = [
            str(x).strip().lower() for x in self._policy.get("high_risk_topics", [])
        ]
        self._must_match_cases: list[dict[str, Any]] = list(
            self._policy.get("must_match_cases", [])
        )

    # ---- Public API -----------------------------------------------------------------

    async def build_context(self, question: str) -> RAGKnowledgeContext:
        """Построить RAG-контекст для пользовательского сообщения."""
        normalized_question = (question or "").strip()
        if not normalized_question:
            empty_intent = IntentDetectionResult(
                intent="unknown",
                confidence=0.0,
                matched_keywords=[],
                matched_catalog_intent=None,
            )
            return RAGKnowledgeContext(
                question="",
                intent=empty_intent,
                high_risk=False,
                context_text="Пустой запрос, знаний нет.",
            )

        intent_result = self._intent_engine.detect_from_rules(normalized_question)
        high_risk = self._is_high_risk(normalized_question, intent_result.intent)

        faq_hits: list[dict[str, Any]] = []
        retrieval_stage = "none"
        faq_tag = self._intent_engine.faq_tag_for_intent(intent_result.intent)
        query_embedding_list: list[float] | None = None

        try:
            async with self._session_factory() as session:
                (
                    faq_hits,
                    retrieval_stage,
                    query_embedding_list,
                ) = await self._retrieve_faq(
                    question=normalized_question,
                    faq_tag=faq_tag,
                    session=session,
                )
        except Exception as exc:  # pragma: no cover - защитный слой
            log.warning(
                "rag_faq_retrieval_failed",
                error=str(exc),
            )

        case_lexical, case_semantic = self._retrieve_cases(
            question=normalized_question,
            query_embedding=query_embedding_list,
        )

        regulations = self._collect_regulations(intent_result.intent)

        context_text = self._build_llm_context(
            question=normalized_question,
            intent=intent_result,
            high_risk=high_risk,
            faq_hits=faq_hits,
            retrieval_stage=retrieval_stage,
            case_lexical=case_lexical,
            case_semantic=case_semantic,
            regulations=regulations,
        )

        return RAGKnowledgeContext(
            question=normalized_question,
            intent=intent_result,
            high_risk=high_risk,
            faq_hits=faq_hits,
            faq_tag=faq_tag,
            retrieval_stage=retrieval_stage,
            case_lexical=case_lexical,
            case_semantic=case_semantic,
            regulations=regulations,
            context_text=context_text,
        )

    # ---- Internal helpers -----------------------------------------------------------

    def _load_json(self, rel_path: str, default: Mapping[str, Any]) -> Mapping[str, Any]:
        path = self._data_root / rel_path
        if not path.exists():
            return default
        try:
            import json

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

    def _is_high_risk(self, text: str, intent: str) -> bool:
        lowered = (text or "").strip().lower()
        if not lowered:
            return False
        if intent in {"battery_fire", "rude_communication"}:
            return True
        return any(topic in lowered for topic in self._high_risk_topics)

    async def _retrieve_faq(
        self,
        *,
        question: str,
        faq_tag: str | None,
        session: AsyncSession,
        limit: int = 5,
    ) -> tuple[list[dict[str, Any]], str, list[float] | None]:
        """Семантический + гибридный поиск по FAQ."""
        retrieval_stage = "none"
        faq_hits: list[dict[str, Any]] = []
        query_embedding_list: list[float] | None = None

        # 1) Попытка чисто семантического поиска
        query_embedding_list = await self._embeddings_service.embed_text(question)
        if query_embedding_list:
            literal = self._faq_repo.serialize_embedding(query_embedding_list)
            if literal:
                semantic_hits = await self._faq_repo.search_semantic(
                    query_embedding=literal,
                    limit=limit,
                    tag=faq_tag,
                    session=session,
                )
                if semantic_hits:
                    faq_hits = semantic_hits
                    retrieval_stage = "semantic"

        # 2) Fallback / дополнение через гибридный поиск
        if not faq_hits:
            hybrid_hits = await self._faq_repo.search_hybrid(
                query=question,
                limit=limit,
                tag=faq_tag,
                session=session,
                query_embedding=self._faq_repo.serialize_embedding(query_embedding_list)
                if query_embedding_list
                else None,
            )
            if hybrid_hits:
                faq_hits = hybrid_hits
                retrieval_stage = "hybrid"

        return faq_hits, retrieval_stage, query_embedding_list

    def _retrieve_cases(
        self,
        *,
        question: str,
        query_embedding: list[float] | None,
    ) -> tuple[SimilarCaseResult | None, SimilarCaseResult | None]:
        """Найти похожие кейсы: лексика + опционально семантика."""
        lexical = self._case_classifier.find_similar_case(question)

        semantic: SimilarCaseResult | None = None
        if self._case_classifier.has_semantic and query_embedding:
            semantic = self._case_classifier.find_similar_case_semantic(query_embedding)

        return lexical, semantic

    def _collect_regulations(self, intent: str) -> list[dict[str, Any]]:
        """Подбор регламентов (must_match_cases) по intent."""
        if not self._must_match_cases:
            return []

        canonical_intent = self._intent_engine.normalize_intent(intent)
        regs: list[dict[str, Any]] = []
        for case in self._must_match_cases:
            intents = case.get("intents") or []
            normalized = {
                self._intent_engine.normalize_intent(str(x).strip().lower())
                for x in intents
                if str(x).strip()
            }
            if canonical_intent in normalized:
                regs.append(case)

        # Достаточно нескольких штук для контекста
        return regs[:3]

    def _build_llm_context(
        self,
        *,
        question: str,
        intent: IntentDetectionResult,
        high_risk: bool,
        faq_hits: list[dict[str, Any]],
        retrieval_stage: str,
        case_lexical: SimilarCaseResult | None,
        case_semantic: SimilarCaseResult | None,
        regulations: list[dict[str, Any]],
    ) -> str:
        """Собрать человеко-читаемый контекст для LLM на основе найденных знаний."""
        parts: list[str] = []

        parts.append(
            f"Входной запрос курьера: {question.strip()}\n"
            f"Предполагаемый intent: {intent.intent} (confidence={intent.confidence:.2f}). "
            f"high_risk={high_risk}."
        )

        if faq_hits:
            parts.append(
                f"\nFAQ (retrieval={retrieval_stage}, top {min(2, len(faq_hits))}):"
            )
            for hit in faq_hits[:2]:
                q = str(hit.get("question") or "").strip()
                a = str(hit.get("answer") or "").strip()
                score = float(hit.get("score", 0.0))
                parts.append(
                    f"- FAQ id={hit.get('id')} score={score:.3f}: "
                    f"Вопрос: {q[:200]} | Ответ: {a[:300]}"
                )

        if case_semantic or case_lexical:
            parts.append("\nПохожие ML-кейсы (ml_cases.jsonl):")
            primary = case_semantic or case_lexical
            backup = case_lexical if case_semantic else None

            if primary is not None:
                parts.append(
                    f"- Основной кейс id={primary.case_id}, label={primary.label}, "
                    f"similarity={primary.similarity_score:.3f}. "
                    f"Решение: {str(primary.decision or '')[:300]}"
                )
            if backup is not None and backup.case_id != getattr(primary, "case_id", None):
                parts.append(
                    f"- Доп. кейс id={backup.case_id}, label={backup.label}, "
                    f"similarity={backup.similarity_score:.3f}. "
                    f"Решение: {str(backup.decision or '')[:200]}"
                )

        if regulations:
            parts.append("\nРегламенты (must_match_cases из core_policy):")
            for case in regulations:
                trigger = str(case.get("trigger") or "").strip()
                response = str(case.get("response") or "").strip()
                parts.append(
                    f"- Регламент id={case.get('id')}: триггер='{trigger[:200]}', "
                    f"ответ='{response[:300]}'"
                )

        if not faq_hits and not (case_lexical or case_semantic) and not regulations:
            parts.append(
                "\nПо базе знаний не найдено надёжных совпадений. "
                "Если будешь генерировать ответ, держись общих регламентов доставки и "
                "не придумывай новых правил."
            )

        return "\n".join(parts).strip()

