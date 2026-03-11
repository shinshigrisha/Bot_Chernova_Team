"""Tests for CaseClassifier: load ml_cases.jsonl, normalize, find_similar_case (lexical + semantic)."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from src.core.services.ai.case_classifier import (
    CaseClassifier,
    SimilarCaseResult,
    STRONG_MATCH_THRESHOLD,
    _cosine_similarity,
    _tokenize,
)


def test_tokenize():
    assert _tokenize("Яйца разбиты, пакет цел") == {"яйца", "разбиты", "пакет", "цел"}
    assert _tokenize("") == set()
    assert _tokenize("a") == set()
    assert _tokenize("ab 12 XY") == {"ab", "12", "xy"}


def test_normalize_case_skips_invalid():
    assert CaseClassifier._normalize_case({}) is None
    assert CaseClassifier._normalize_case({"id": "x"}) is None
    assert CaseClassifier._normalize_case({"input": "y"}) is None


def test_normalize_case_returns_dict():
    raw = {
        "id": "test_1",
        "input": "  разбиты яйца  ",
        "label": "damage",
        "decision": "фото",
        "explanation": "типовой кейс",
    }
    out = CaseClassifier._normalize_case(raw)
    assert out is not None
    assert out["id"] == "test_1"
    assert out["input"] == "разбиты яйца"
    assert out["label"] == "damage"
    assert out["decision"] == "фото"
    assert out["explanation"] == "типовой кейс"


def test_find_similar_case_empty_file():
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "ml_cases.jsonl"
        path.write_text("", encoding="utf-8")
        cl = CaseClassifier(data_root=tmp)
        assert cl.find_similar_case("разбиты яйца") is None


def test_find_similar_case_no_file():
    with tempfile.TemporaryDirectory() as tmp:
        cl = CaseClassifier(data_root=tmp)
        assert cl.find_similar_case("разбиты яйца") is None


def test_find_similar_case_returns_structure():
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "ml_cases.jsonl"
        path.write_text(
            json.dumps({
                "id": "eggs",
                "input": "Яйца разбиты, пакет цел",
                "label": "damage",
                "decision": "Фото и куратору",
                "explanation": "Типовой кейс.",
            }, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        cl = CaseClassifier(data_root=tmp, min_similarity=0.2)
        result = cl.find_similar_case("Яйца разбиты, пакет цел")
        assert result is not None
        assert isinstance(result, SimilarCaseResult)
        assert result.case_id == "eggs"
        assert result.input == "Яйца разбиты, пакет цел"
        assert result.label == "damage"
        assert result.decision == "Фото и куратору"
        assert result.explanation == "Типовой кейс."
        assert isinstance(result.similarity_score, (int, float))
        assert 0 <= result.similarity_score <= 1


def test_find_similar_case_lexical_overlap():
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "ml_cases.jsonl"
        path.write_text(
            json.dumps({
                "id": "eggs",
                "input": "Яйца разбиты, пакет цел",
                "label": "damage",
                "decision": "фото",
                "explanation": "",
            }, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        cl = CaseClassifier(data_root=tmp, min_similarity=0.2)
        exact = cl.find_similar_case("Яйца разбиты, пакет цел")
        partial = cl.find_similar_case("разбиты яйца в пакете")
        assert exact is not None
        assert partial is not None
        assert exact.similarity_score >= partial.similarity_score


def test_find_similar_case_below_threshold_returns_none():
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "ml_cases.jsonl"
        path.write_text(
            json.dumps({
                "id": "eggs",
                "input": "Яйца разбиты, пакет цел",
                "label": "damage",
                "decision": "",
                "explanation": "",
            }, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        cl = CaseClassifier(data_root=tmp, min_similarity=0.99)
        result = cl.find_similar_case("совсем другой текст про погоду")
        assert result is None


def test_strong_match_threshold_constant():
    assert 0 < STRONG_MATCH_THRESHOLD <= 1


def test_reload():
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "ml_cases.jsonl"
        path.write_text(
            json.dumps({
                "id": "a",
                "input": "первый кейс",
                "label": "x",
                "decision": "",
                "explanation": "",
            }, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        cl = CaseClassifier(data_root=tmp, min_similarity=0.2)
        assert cl.find_similar_case("первый кейс") is not None
        path.write_text("", encoding="utf-8")
        cl.reload()
        assert cl.find_similar_case("первый кейс") is None


# ---- Cosine similarity ----
def test_cosine_similarity_identical():
    v = [1.0, 0.0, 0.0]
    assert _cosine_similarity(v, v) == 1.0


def test_cosine_similarity_orthogonal():
    a = [1.0, 0.0, 0.0]
    b = [0.0, 1.0, 0.0]
    assert _cosine_similarity(a, b) == 0.0


def test_cosine_similarity_empty():
    assert _cosine_similarity([], [1.0, 0.0]) == 0.0
    assert _cosine_similarity([1.0], [1.0, 0.0]) == 0.0


# ---- Semantic search ----
def test_find_similar_case_semantic_returns_none_without_embeddings():
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "ml_cases.jsonl"
        path.write_text(
            json.dumps({
                "id": "1",
                "input": "Яйца разбиты",
                "label": "damage",
                "decision": "Фото",
                "explanation": "",
            }, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        cl = CaseClassifier(data_root=tmp)
        assert cl.has_semantic is False
        assert cl.find_similar_case_semantic([0.1, 0.2, 0.3]) is None


def test_find_similar_case_semantic_returns_best_when_embeddings_loaded():
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "ml_cases.jsonl"
        path.write_text(
            json.dumps({
                "id": "eggs",
                "input": "Яйца разбиты, пакет цел",
                "label": "damage",
                "decision": "Сделай фото и сообщи куратору",
                "explanation": "Хрупкий товар.",
            }, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        # Same-dim mock embedding for the one case (4 dims for test)
        emb = [0.8, 0.2, 0.1, 0.0]
        emb_path = Path(tmp) / "ml_cases_embeddings.json"
        emb_path.write_text(
            json.dumps([{"id": "eggs", "input": "Яйца разбиты, пакет цел", "label": "damage", "decision": "Сделай фото и сообщи куратору", "explanation": "Хрупкий товар.", "embedding": emb}]),
            encoding="utf-8",
        )
        cl = CaseClassifier(data_root=tmp, semantic_min_similarity=0.5)
        assert cl.has_semantic is True
        # Query with same vector -> similarity 1.0
        result = cl.find_similar_case_semantic(emb)
        assert result is not None
        assert result.case_id == "eggs"
        assert result.similarity_score >= 0.99
        assert "фото" in result.decision or "Сделай" in result.decision


def test_semantic_below_threshold_returns_none():
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "ml_cases.jsonl"
        path.write_text(
            json.dumps({
                "id": "eggs",
                "input": "Яйца разбиты",
                "label": "damage",
                "decision": "Фото",
                "explanation": "",
            }, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        emb = [1.0, 0.0, 0.0, 0.0]
        emb_path = Path(tmp) / "ml_cases_embeddings.json"
        emb_path.write_text(
            json.dumps([{"id": "eggs", "embedding": emb}]),
            encoding="utf-8",
        )
        cl = CaseClassifier(data_root=tmp, semantic_min_similarity=0.99)
        # Orthogonal query -> similarity 0
        result = cl.find_similar_case_semantic([0.0, 1.0, 0.0, 0.0])
        assert result is None


# ---- Semantic retrieval scenarios (eggs broken, no answer, missing, late, battery) ----
def test_semantic_eggs_broken_damaged_fragile():
    """Eggs broken / damaged fragile goods: semantic match to damage case."""
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "ml_cases.jsonl"
        path.write_text(
            json.dumps({
                "id": "1",
                "input": "Яйца разбиты, пакет целый",
                "label": "Неаккуратная доставка",
                "decision": "Ответственность курьера. Сделай фото.",
                "explanation": "Повреждение хрупкого товара.",
            }, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        v = [0.9, 0.1, 0.0, 0.0]
        emb_path = Path(tmp) / "ml_cases_embeddings.json"
        emb_path.write_text(
            json.dumps([{"id": "1", "input": "Яйца разбиты, пакет целый", "label": "x", "decision": "Сделай фото.", "explanation": "", "embedding": v}]),
            encoding="utf-8",
        )
        cl = CaseClassifier(data_root=tmp, semantic_min_similarity=0.6)
        # "повреждён хрупкий товар" -> same embedding for test => match
        result = cl.find_similar_case_semantic(v)
        assert result is not None
        assert result.case_id == "1"
        assert "фото" in result.decision or "Сделай" in result.decision


def test_semantic_customer_not_answering():
    """Customer not answering / no answer / intercom: semantic match to contact case."""
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "ml_cases.jsonl"
        path.write_text(
            json.dumps({
                "id": "43",
                "input": "Не дозвонился и сразу вернул заказ",
                "label": "Отмена / заказ вернулся в магазин",
                "decision": "Сделай 2–3 попытки связи, подожди у подъезда.",
                "explanation": "Недостаточно попыток связи с клиентом.",
            }, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        v = [0.1, 0.9, 0.0, 0.0]
        emb_path = Path(tmp) / "ml_cases_embeddings.json"
        emb_path.write_text(
            json.dumps([{"id": "43", "input": "Не дозвонился", "label": "x", "decision": "2–3 попытки связи", "explanation": "", "embedding": v}]),
            encoding="utf-8",
        )
        cl = CaseClassifier(data_root=tmp, semantic_min_similarity=0.6)
        result = cl.find_similar_case_semantic(v)
        assert result is not None
        assert result.case_id == "43"
        assert "попытки" in result.decision or "связи" in result.decision


def test_semantic_missing_package():
    """Missing package / missing items: semantic match to partial delivery case."""
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "ml_cases.jsonl"
        path.write_text(
            json.dumps({
                "id": "24",
                "input": "Одного пакета не было",
                "label": "Не отдали часть заказа",
                "decision": "Проверь места, сообщи в поддержку.",
                "explanation": "Недоставка части заказа.",
            }, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        v = [0.0, 0.1, 0.9, 0.0]
        emb_path = Path(tmp) / "ml_cases_embeddings.json"
        emb_path.write_text(
            json.dumps([{"id": "24", "input": "Одного пакета не было", "label": "x", "decision": "Проверь места", "explanation": "", "embedding": v}]),
            encoding="utf-8",
        )
        cl = CaseClassifier(data_root=tmp, semantic_min_similarity=0.6)
        result = cl.find_similar_case_semantic(v)
        assert result is not None
        assert result.case_id == "24"
        assert "Проверь" in result.decision or "места" in result.decision


def test_semantic_late_delivery_traffic():
    """Late due to traffic: semantic can match late/operational case."""
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "ml_cases.jsonl"
        path.write_text(
            json.dumps({
                "id": "late1",
                "input": "Опоздал из-за пробок",
                "label": "late_delivery",
                "decision": "Сообщи ETA и причину задержки.",
                "explanation": "Трафик.",
            }, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        v = [0.0, 0.0, 0.1, 0.9]
        emb_path = Path(tmp) / "ml_cases_embeddings.json"
        emb_path.write_text(
            json.dumps([{"id": "late1", "input": "Опоздал из-за пробок", "label": "late_delivery", "decision": "Сообщи ETA", "explanation": "", "embedding": v}]),
            encoding="utf-8",
        )
        cl = CaseClassifier(data_root=tmp, semantic_min_similarity=0.6)
        result = cl.find_similar_case_semantic(v)
        assert result is not None
        assert result.case_id == "late1"
        assert "ETA" in result.decision or "Сообщи" in result.decision


def test_semantic_battery_smoke():
    """Battery smoke: semantic match to safety-related case."""
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "ml_cases.jsonl"
        path.write_text(
            json.dumps({
                "id": "bat1",
                "input": "АКБ дымит в шкафу",
                "label": "battery_fire",
                "decision": "Прекрати зарядку, обесточь, сообщи о безопасности.",
                "explanation": "Риск возгорания.",
            }, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        v = [0.0, 0.0, 0.0, 1.0]
        emb_path = Path(tmp) / "ml_cases_embeddings.json"
        emb_path.write_text(
            json.dumps([{"id": "bat1", "input": "АКБ дымит", "label": "battery_fire", "decision": "Прекрати зарядку, обесточь", "explanation": "", "embedding": v}]),
            encoding="utf-8",
        )
        cl = CaseClassifier(data_root=tmp, semantic_min_similarity=0.6)
        result = cl.find_similar_case_semantic(v)
        assert result is not None
        assert result.case_id == "bat1"
        assert "обез" in result.decision or "Прекрати" in result.decision
