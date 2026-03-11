from __future__ import annotations

import pytest

from src.core.services.ai.intent_engine import IntentEngine


def _mini_catalog():
    return [
        {
            "intent": "courier_phone_busy_unreachable",
            "questions": [
                "Клиент не отвечает, телефон занят",
                "Не могу дозвониться клиенту",
                "Абонент недоступен",
            ],
        },
        {
            "intent": "courier_payment_terminal_problem",
            "questions": [
                "Терминал не работает",
                "Не проходит оплата терминалом",
                "Терминал не принимает платеж",
            ],
        },
        {
            "intent": "courier_damaged_goods",
            "questions": [
                "Яйца разбились по дороге",
                "Товар поврежден при доставке",
                "Пакет порвался и товар пострадал",
            ],
        },
        {
            "intent": "courier_refuse_door_delivery",
            "questions": [
                "Курьер не хочет подниматься до квартиры",
                "Мне сказали забрать заказ из машины",
                "Курьер отказался нести до двери",
            ],
        },
        {
            "intent": "courier_left_without_permission",
            "questions": [
                "Курьер оставил заказ у двери без разрешения",
                "Заказ оставили без согласования",
                "Пакеты лежали у двери без звонка",
            ],
        },
        {
            "intent": "courier_missing_package",
            "questions": [
                "Мне не привезли один пакет",
                "В заказе не хватает пакета",
                "Курьер привез не все пакеты",
            ],
        },
        {
            "intent": "courier_temperature_melted",
            "questions": [
                "Мороженое полностью растаяло",
                "Заморозка приехала мягкая",
                "Температурный режим при доставке нарушен",
            ],
        },
    ]


@pytest.mark.parametrize(
    ("text", "expected_intent", "expected_catalog"),
    [
        ("Клиент не отвечает, телефон занят. Что делать?", "contact_customer", "courier_phone_busy_unreachable"),
        ("Терминал не принимает платеж, не проходит оплата", "payment_terminal", "courier_payment_terminal_problem"),
        ("Яйца разбились по дороге, все в пакете", "damaged_goods", "courier_damaged_goods"),
        ("Курьер отказался нести до двери, просит выйти", "no_door_delivery", "courier_refuse_door_delivery"),
        ("Курьер оставил заказ у двери без разрешения и ушел", "leave_at_door", "courier_left_without_permission"),
        ("Мне не привезли один пакет из заказа", "missing_items", "courier_missing_package"),
        ("Мороженое растаяло, температурный режим нарушен", "temperature_issue", "courier_temperature_melted"),
    ],
)
def test_intent_engine_catalog_fuzzy_detects_representative_intents(
    text: str, expected_intent: str, expected_catalog: str
):
    engine = IntentEngine(intents_catalog=_mini_catalog())
    res = engine.detect_from_rules(text)
    assert res.intent == expected_intent
    assert res.matched_catalog_intent == expected_catalog

