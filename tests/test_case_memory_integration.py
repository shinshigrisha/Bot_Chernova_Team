from __future__ import annotations

import json
import tempfile
from dataclasses import dataclass
from pathlib import Path

import pytest

from src.core.services.ai.ai_courier_service import AICourierService
from src.core.services.ai.intent_engine import IntentDetectionResult


class _DummySession:
    async def __aenter__(self):
        return object()

    async def __aexit__(self, exc_type, exc, tb):
        return False


@dataclass(frozen=True)
class _CaseScenario:
    name: str
    query: str
    case_id: str
    label: str
    decision_must_contain: str


async def _empty_hits(*, session, **_kwargs):
    return []


def _write_ml_cases(data_root: Path, cases: list[dict]) -> None:
    (data_root / "ml_cases.jsonl").write_text(
        "\n".join(json.dumps(c, ensure_ascii=False) for c in cases) + "\n",
        encoding="utf-8",
    )


def _write_case_embeddings(data_root: Path, embeddings: list[dict]) -> None:
    (data_root / "ml_cases_embeddings.json").write_text(
        json.dumps(embeddings, ensure_ascii=False),
        encoding="utf-8",
    )


@pytest.mark.asyncio
async def test_case_memory_called_after_faq_retrieval(monkeypatch) -> None:
    """
    Инвариант интеграции: case memory (ml_cases) дергается ПОСЛЕ FAQ retrieval.
    Это важно, чтобы не подменять/смещать приоритеты must_match/FAQ, а добавлять память как evidence.
    """
    with tempfile.TemporaryDirectory() as tmp:
        data_root = Path(tmp)
        _write_ml_cases(
            data_root,
            [
                {
                    "id": "c1",
                    "input": "тестовый кейс",
                    "label": "x",
                    "decision": "делай так",
                    "explanation": "пояснение",
                }
            ],
        )

        call_order: list[str] = []
        service = AICourierService(session_factory=_DummySession, router=None, data_root=data_root)
        service._must_match_cases = []
        monkeypatch.setattr(service._case_engine, "resolve", lambda **_kw: None)

        async def _detect_stub(*_a, **_kw):
            return IntentDetectionResult(intent="unknown", confidence=0.0, matched_keywords=[])

        monkeypatch.setattr(service._intent_engine, "detect", _detect_stub)

        async def _search_by_keywords(*, session, **kwargs):
            call_order.append("faq_keyword")
            return []

        async def _search_semantic(*, session, **kwargs):
            call_order.append("faq_semantic")
            return []

        async def _search_hybrid(*, session, **kwargs):
            call_order.append("faq_hybrid")
            return []

        monkeypatch.setattr(service._faq_repo, "search_by_keywords", _search_by_keywords)
        monkeypatch.setattr(service._faq_repo, "search_semantic", _search_semantic)
        monkeypatch.setattr(service._faq_repo, "search_hybrid", _search_hybrid)

        def _find_similar_case_stub(text: str):
            call_order.append("case_memory_lexical")
            return None

        monkeypatch.setattr(service._case_classifier, "find_similar_case", _find_similar_case_stub)

        result = await service.get_answer(user_id=1, text="произвольный вопрос без FAQ")
        assert result.text
        assert "case_memory_lexical" in call_order
        assert call_order.index("case_memory_lexical") > call_order.index("faq_keyword")


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "scenario",
    [
        _CaseScenario(
            name="broken_eggs",
            query="Яйца приехали разбитые, что делать?",
            case_id="eggs_1",
            label="Неаккуратная доставка",
            decision_must_contain="фото",
        ),
        _CaseScenario(
            name="terminal_issue",
            query="Терминал не пробивает оплату, клиент ждёт",
            case_id="terminal_1",
            label="Проблема с терминалом",
            decision_must_contain="терминал",
        ),
        _CaseScenario(
            name="missing_package",
            query="Не хватает пакета, одного пакета нет",
            case_id="missing_1",
            label="Не отдали часть заказа",
            decision_must_contain="проверь",
        ),
        _CaseScenario(
            name="wrong_leave_at_door",
            query="Оставил у двери без разрешения, что теперь?",
            case_id="door_1",
            label="Игнор комментариев",
            decision_must_contain="клиент",
        ),
        _CaseScenario(
            name="customer_no_answer",
            query="Клиент не отвечает, домофон молчит",
            case_id="no_answer_1",
            label="Коммуникация с покупателем",
            decision_must_contain="попыт",
        ),
    ],
    ids=lambda s: s.name,
)
async def test_semantic_case_memory_routes_and_explainability(
    monkeypatch, scenario: _CaseScenario
) -> None:
    """
    Проверяем, что семантическая память кейсов может дать отдельный route `semantic_case`
    (когда отключены must_match/FAQ/case_engine), и что explainability включает требуемые поля.
    """
    with tempfile.TemporaryDirectory() as tmp:
        data_root = Path(tmp)
        cases = [
            {
                "id": scenario.case_id,
                "input": scenario.query,
                "label": scenario.label,
                "decision": f"Решение: {scenario.decision_must_contain}",
                "explanation": "обоснование",
            }
        ]
        v = [0.9, 0.1, 0.0, 0.0]
        _write_ml_cases(data_root, cases)
        _write_case_embeddings(data_root, [{"id": scenario.case_id, "embedding": v}])

        service = AICourierService(session_factory=_DummySession, router=None, data_root=data_root)
        service._must_match_cases = []
        monkeypatch.setattr(service._case_engine, "resolve", lambda **_kw: None)
        monkeypatch.setattr(service._intent_engine, "detect", lambda *_a, **_kw: IntentDetectionResult(intent="unknown", confidence=0.0, matched_keywords=[]))

        monkeypatch.setattr(service._faq_repo, "search_by_keywords", _empty_hits)
        monkeypatch.setattr(service._faq_repo, "search_semantic", _empty_hits)
        monkeypatch.setattr(service._faq_repo, "search_hybrid", _empty_hits)

        async def _embed_text_stub(_text: str):
            return v

        service._embeddings_service.enabled = True
        monkeypatch.setattr(service._embeddings_service, "embed_text", _embed_text_stub)

        result = await service.get_answer(user_id=2, text=scenario.query)
        assert result.route == "semantic_case"
        assert result.debug.get("case_id") == scenario.case_id
        assert result.debug.get("case_label") == scenario.label
        assert float(result.debug.get("case_similarity", 0.0)) >= 0.5
        assert scenario.decision_must_contain.lower() in str(result.debug.get("case_decision", "")).lower()
        assert "case_explanation" in result.debug


@pytest.mark.asyncio
async def test_case_memory_does_not_override_must_match(monkeypatch) -> None:
    """
    Guardrail: если сработал must_match (критичный флоу), case memory не вмешивается и не меняет route.
    """
    with tempfile.TemporaryDirectory() as tmp:
        data_root = Path(tmp)
        _write_ml_cases(
            data_root,
            [
                {
                    "id": "eggs_1",
                    "input": "Яйца разбиты, пакет цел",
                    "label": "Неаккуратная доставка",
                    "decision": "Фото",
                    "explanation": "Хрупкий товар",
                }
            ],
        )
        _write_case_embeddings(data_root, [{"id": "eggs_1", "embedding": [1.0, 0.0, 0.0, 0.0]}])

        service = AICourierService(session_factory=_DummySession, router=None, data_root=data_root)

        # Делаем must_match детерминированным, чтобы не зависеть от core_policy.json.
        service._must_match_cases = [
            {
                "id": "must_eggs",
                "trigger": "Яйца разбиты",
                "keywords": ["яйца", "разбиты"],
                "intents": ["damaged_goods"],
                "response": "1) Сделай фото. 2) Сообщи куратору.",
                "confidence": 0.96,
                "escalate": False,
            }
        ]

        monkeypatch.setattr(service._intent_engine, "detect", lambda *_a, **_kw: IntentDetectionResult(intent="damaged_goods", confidence=0.9, matched_keywords=["разбит"]))
        monkeypatch.setattr(service._case_engine, "resolve", lambda **_kw: None)
        monkeypatch.setattr(service._faq_repo, "search_by_keywords", _empty_hits)
        monkeypatch.setattr(service._faq_repo, "search_semantic", _empty_hits)
        monkeypatch.setattr(service._faq_repo, "search_hybrid", _empty_hits)

        result = await service.get_answer(user_id=3, text="Яйца разбиты, пакет цел")
        assert result.route == "must_match"
        assert "фото" in (result.text or "").lower()
