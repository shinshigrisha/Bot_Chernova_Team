from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Mapping, Sequence

from sqlalchemy.ext.asyncio import AsyncSession

from src.core.services.ai.provider_router import ProviderRouter
from src.infra.db.repositories.faq_repo import FAQRepository


SUPPORTED_INTENTS = (
    "damaged_goods",
    "contact_customer",
    "missing_items",
    "late_delivery",
    "payment_terminal",
    "payment_hyperlink",
    "battery_fire",
    "rude_communication",
    "leave_at_door",
    "return_order",
    "unknown",
)


@dataclass(slots=True)
class IntentDetectionResult:
    intent: str
    confidence: float
    matched_keywords: list[str] = field(default_factory=list)


class IntentEngine:
    _DEFAULT_RULES: dict[str, tuple[tuple[str, float], ...]] = {
        "damaged_goods": (
            ("разбит", 0.48),
            ("треснул", 0.46),
            ("повред", 0.42),
            ("помят", 0.32),
            ("протек", 0.36),
            ("разлил", 0.32),
            ("разлилось", 0.36),
            ("порван", 0.32),
            ("битый", 0.40),
            ("повреждение", 0.38),
        ),
        "contact_customer": (
            ("не дозвонил", 0.56),
            ("не отвечает", 0.52),
            ("домофон", 0.44),
            ("не открыва", 0.42),
            ("нет связи", 0.38),
            ("дозвон", 0.40),
            ("не берёт", 0.44),
            ("код домофон", 0.40),
        ),
        "missing_items": (
            ("недовоз", 0.58),
            ("не хватает", 0.50),
            ("нет пакета", 0.46),
            ("нет позиции", 0.44),
            ("не довез", 0.46),
            ("потерял пакет", 0.44),
            ("недосдача", 0.42),
        ),
        "late_delivery": (
            ("опаздыв", 0.56),
            ("опоздал", 0.56),
            ("не успеваю", 0.54),
            ("пробк", 0.38),
            ("задержк", 0.38),
            ("таймер", 0.36),
            ("не успею", 0.48),
        ),
        "payment_terminal": (
            ("терминал", 0.62),
            ("эквайр", 0.56),
            ("оплата карт", 0.52),
            ("картой", 0.36),
            ("безнал", 0.36),
            ("пин", 0.24),
            ("чек", 0.22),
            ("не пробивает", 0.44),
        ),
        "payment_hyperlink": (
            ("ссылка на оплат", 0.72),
            ("оплата по ссылк", 0.68),
            ("гиперссыл", 0.60),
            ("линк на оплат", 0.60),
            ("ссылку клиент", 0.48),
            ("оплатить по ссылке", 0.58),
        ),
        "battery_fire": (
            ("дым", 0.68),
            ("запах гари", 0.72),
            ("гари", 0.56),
            ("гарь", 0.56),
            ("акб", 0.58),
            ("батаре", 0.52),
            ("зарядк", 0.38),
            ("возгора", 0.76),
            ("нагрелся", 0.42),
        ),
        "rude_communication": (
            ("грубит", 0.56),
            ("хамит", 0.56),
            ("оскорб", 0.68),
            ("угрож", 0.72),
            ("агрес", 0.62),
            ("конфликт", 0.46),
            ("ругается", 0.48),
        ),
        "leave_at_door": (
            ("оставить у двери", 0.72),
            ("оставь у двери", 0.72),
            ("под двер", 0.60),
            ("без контакта", 0.48),
            ("у двери", 0.34),
            ("положить у порога", 0.58),
        ),
        "return_order": (
            ("возврат", 0.62),
            ("вернуть заказ", 0.62),
            ("возвращаю заказ", 0.62),
            ("не принял", 0.46),
            ("отказался", 0.42),
            ("отмена", 0.32),
            ("клиент отказался", 0.48),
        ),
    }

    _INTENT_ALIASES = {
        "damage": "damaged_goods",
        "damaged_goods": "damaged_goods",
        "contact_customer": "contact_customer",
        "missing_items": "missing_items",
        "late_delivery": "late_delivery",
        "payment_terminal": "payment_terminal",
        "payment_hyperlink": "payment_hyperlink",
        "battery_fire": "battery_fire",
        "conflict": "rude_communication",
        "rude_communication": "rude_communication",
        "leave_at_door": "leave_at_door",
        "return": "return_order",
        "return_order": "return_order",
        "equipment": "payment_terminal",
        "unknown": "unknown",
    }

    _FAQ_TAG_ALIASES = {
        "damaged_goods": "damage",
        "contact_customer": "contact_customer",
        "missing_items": "missing_items",
        "late_delivery": "late_delivery",
        "payment_terminal": "payment_terminal",
        "payment_hyperlink": "payment_hyperlink",
        "battery_fire": "battery_fire",
        "rude_communication": "conflict",
        "leave_at_door": "leave_at_door",
        "return_order": "return",
        "unknown": None,
    }

    _JSON_BLOCK_RE = re.compile(r"\{.*\}", re.DOTALL)

    def __init__(
        self,
        *,
        router: ProviderRouter | None = None,
        intent_tags: Mapping[str, Sequence[str]] | None = None,
    ) -> None:
        self._router = router
        self._keyword_rules = self._build_keyword_rules(intent_tags or {})

    @classmethod
    def normalize_intent(cls, intent: str | None) -> str:
        lowered = str(intent or "").strip().lower()
        if not lowered:
            return "unknown"
        return cls._INTENT_ALIASES.get(lowered, lowered if lowered in SUPPORTED_INTENTS else "unknown")

    @classmethod
    def faq_tag_for_intent(cls, intent: str | None) -> str | None:
        canonical = cls.normalize_intent(intent)
        return cls._FAQ_TAG_ALIASES.get(canonical)

    @staticmethod
    def _normalize_text(text: str) -> str:
        lowered = str(text or "").strip().lower()
        return re.sub(r"\s+", " ", lowered)

    @classmethod
    def _build_keyword_rules(
        cls,
        intent_tags: Mapping[str, Sequence[str]],
    ) -> dict[str, list[tuple[str, float]]]:
        rules: dict[str, list[tuple[str, float]]] = {
            intent: list(entries) for intent, entries in cls._DEFAULT_RULES.items()
        }
        for raw_intent, keywords in intent_tags.items():
            canonical_intent = cls.normalize_intent(raw_intent)
            if canonical_intent == "unknown":
                continue
            bucket = rules.setdefault(canonical_intent, [])
            seen = {keyword for keyword, _weight in bucket}
            for keyword in keywords:
                normalized_keyword = cls._normalize_text(str(keyword))
                if normalized_keyword and normalized_keyword not in seen:
                    bucket.append((normalized_keyword, 0.24))
                    seen.add(normalized_keyword)
        return rules

    @staticmethod
    def _unknown_result() -> IntentDetectionResult:
        return IntentDetectionResult(intent="unknown", confidence=0.0, matched_keywords=[])

    def detect_from_rules(self, text: str) -> IntentDetectionResult:
        normalized_text = self._normalize_text(text)
        if not normalized_text:
            return self._unknown_result()

        best_intent = "unknown"
        best_confidence = 0.0
        best_keywords: list[str] = []

        for intent, rules in self._keyword_rules.items():
            matched_keywords: list[str] = []
            total_weight = 0.0
            for keyword, weight in rules:
                if keyword and keyword in normalized_text:
                    matched_keywords.append(keyword)
                    total_weight += weight

            if not matched_keywords:
                continue

            confidence = min(0.97, 0.45 + min(total_weight, 1.0) * 0.55)
            if confidence > best_confidence:
                best_intent = intent
                best_confidence = confidence
                best_keywords = matched_keywords

        if best_intent == "unknown":
            return self._unknown_result()

        return IntentDetectionResult(
            intent=best_intent,
            confidence=round(best_confidence, 4),
            matched_keywords=best_keywords[:5],
        )

    async def _detect_from_faq(
        self,
        text: str,
        *,
        faq_repo: FAQRepository,
        session: AsyncSession,
    ) -> IntentDetectionResult:
        faq_hits = await faq_repo.search_hybrid(query=text, limit=3, session=session)
        if not faq_hits:
            return self._unknown_result()

        aggregated: dict[str, dict[str, float]] = {}
        for hit in faq_hits:
            intent = self.normalize_intent(hit.get("tag"))
            if intent == "unknown":
                continue
            score = float(hit.get("score", 0.0))
            bucket = aggregated.setdefault(intent, {"top": 0.0, "total": 0.0, "count": 0.0})
            bucket["top"] = max(bucket["top"], score)
            bucket["total"] += score
            bucket["count"] += 1.0

        if not aggregated:
            return self._unknown_result()

        best_intent, best_stats = max(
            aggregated.items(),
            key=lambda item: (item[1]["total"], item[1]["top"], item[1]["count"]),
        )
        top_score = best_stats["top"]
        if top_score < 0.35:
            return self._unknown_result()

        confidence = min(
            0.89,
            0.38 + min(top_score, 1.0) * 0.45 + min(best_stats["total"] - top_score, 0.6) * 0.15,
        )
        return IntentDetectionResult(
            intent=best_intent,
            confidence=round(confidence, 4),
            matched_keywords=[],
        )

    @classmethod
    def _combine_results(
        cls,
        rule_result: IntentDetectionResult,
        faq_result: IntentDetectionResult,
    ) -> IntentDetectionResult:
        if rule_result.intent == "unknown":
            return faq_result
        if faq_result.intent == "unknown":
            return rule_result
        if rule_result.intent == faq_result.intent:
            return IntentDetectionResult(
                intent=rule_result.intent,
                confidence=round(min(0.98, max(rule_result.confidence, faq_result.confidence) + 0.10), 4),
                matched_keywords=rule_result.matched_keywords,
            )
        if rule_result.confidence >= faq_result.confidence + 0.08:
            return rule_result
        return faq_result

    async def _detect_with_llm(self, text: str) -> IntentDetectionResult:
        if self._router is None or not self._router.providers:
            return self._unknown_result()

        messages = [
            {
                "role": "system",
                "content": (
                    "Ты классификатор intent для курьерских ситуаций. "
                    "Выбери только один intent из списка: "
                    + ", ".join(intent for intent in SUPPORTED_INTENTS if intent != "unknown")
                    + ", unknown. "
                    'Верни только JSON формата {"intent": "...", "confidence": 0.0, "matched_keywords": []}. '
                    "Не добавляй пояснений."
                ),
            },
            {"role": "user", "content": text},
        ]

        try:
            response = await self._router.complete(
                messages,
                mode="reason",
                temperature=0.0,
                max_tokens=160,
            )
        except Exception:
            return self._unknown_result()

        payload = response.text.strip()
        match = self._JSON_BLOCK_RE.search(payload)
        if match is None:
            normalized_intent = self.normalize_intent(payload)
            if normalized_intent == "unknown":
                return self._unknown_result()
            return IntentDetectionResult(
                intent=normalized_intent,
                confidence=0.55,
                matched_keywords=[],
            )

        try:
            parsed = json.loads(match.group(0))
        except json.JSONDecodeError:
            return self._unknown_result()

        normalized_intent = self.normalize_intent(parsed.get("intent"))
        if normalized_intent == "unknown":
            return self._unknown_result()

        raw_confidence = parsed.get("confidence", 0.55)
        try:
            confidence = float(raw_confidence)
        except (TypeError, ValueError):
            confidence = 0.55

        matched_keywords = parsed.get("matched_keywords", [])
        if not isinstance(matched_keywords, list):
            matched_keywords = []

        return IntentDetectionResult(
            intent=normalized_intent,
            confidence=round(min(0.74, max(0.45, confidence)), 4),
            matched_keywords=[str(item) for item in matched_keywords[:5]],
        )

    async def detect(
        self,
        text: str,
        *,
        faq_repo: FAQRepository | None = None,
        session: AsyncSession | None = None,
    ) -> IntentDetectionResult:
        rule_result = self.detect_from_rules(text)
        if rule_result.intent != "unknown" and rule_result.confidence >= 0.78:
            return rule_result

        faq_result = self._unknown_result()
        if faq_repo is not None and session is not None:
            faq_result = await self._detect_from_faq(
                text,
                faq_repo=faq_repo,
                session=session,
            )

        combined_result = self._combine_results(rule_result, faq_result)
        if combined_result.intent != "unknown" and combined_result.confidence >= 0.65:
            return combined_result

        llm_result = await self._detect_with_llm(text)
        if llm_result.intent == "unknown":
            return combined_result
        if combined_result.intent == llm_result.intent and combined_result.intent != "unknown":
            return IntentDetectionResult(
                intent=llm_result.intent,
                confidence=round(min(0.92, max(llm_result.confidence, combined_result.confidence) + 0.05), 4),
                matched_keywords=combined_result.matched_keywords or llm_result.matched_keywords,
            )
        return llm_result
