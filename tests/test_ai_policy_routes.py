from __future__ import annotations

from dataclasses import dataclass

import pytest

from src.core.services.ai.ai_courier_service import AICourierResult, AICourierService
from src.core.services.ai.provider_router import ProviderRouter
from src.core.services.ai.providers.base import BaseProvider
from src.core.services.ai.providers.base import ProviderResponse


class _DummySession:
    async def __aenter__(self):
        return object()

    async def __aexit__(self, exc_type, exc, tb):
        return False


class _FakeProviderRouter:
    providers = {"fake": object()}

    async def complete(self, messages, *, mode="chat", temperature=0.3, max_tokens=1024):
        system_text = (messages[0].get("content") or "") if messages else ""
        user_text = (messages[-1].get("content") or "").lower()
        faq_marker = "Контекст:\nFAQ answer:\n"
        if faq_marker in system_text:
            return ProviderResponse(
                text=system_text.split(faq_marker, 1)[1].strip(),
                provider="fake",
                model="fake-model",
                usage_tokens=0,
            )
        if "оштрафовать" in user_text:
            return ProviderResponse(
                text=(
                    "Суть ситуации: запрос по санкциям.\n"
                    "Кто отвечает: куратор смены.\n"
                    "Почему: санкции решаются только ответственным.\n"
                    "Что делать сейчас: эскалирую к куратору."
                ),
                provider="fake",
                model="fake-model",
                usage_tokens=0,
            )
        if "полный возврат" in user_text and "терминал" in user_text:
            return ProviderResponse(
                text=(
                    "Суть ситуации: возврат через терминал.\n"
                    "Кто отвечает: поддержка.\n"
                    "Почему: нужен доступ к платежному контуру.\n"
                    "Что делать сейчас: обратитесь в поддержку."
                ),
                provider="fake",
                model="fake-model",
                usage_tokens=0,
            )
        return ProviderResponse(
            text=(
                "Суть ситуации: стандартный кейс.\n"
                "Кто отвечает: курьер.\n"
                "Почему: есть регламент FAQ.\n"
                "Что делать сейчас: выполните шаги по инструкции."
            ),
            provider="fake",
            model="fake-model",
            usage_tokens=0,
        )

    async def close(self):
        return None


class _FailingProviderRouter:
    providers = {"fake": object()}

    async def complete(self, messages, *, mode="chat", temperature=0.3, max_tokens=1024):
        raise RuntimeError("provider unavailable")


@dataclass
class _Case:
    text: str
    expected_business_route: str
    must_contain: str


def _business_route(result: AICourierResult) -> str:
    text = (result.text or "").lower()
    if result.route in {"faq", "rule"} and not result.escalate:
        return "auto_answer"
    if "поддержк" in text:
        return "route_to_support"
    if result.escalate or "эскалир" in text:
        return "route_to_curator"
    if result.route in {"llm_reason"}:
        return "auto_answer"
    return "route_to_curator"


def _faq_knowledge():
    return [
        {
            "id": "faq_eggs",
            "q": "Яйца приехали разбитые",
            "a": (
                "Суть ситуации: товар поврежден.\n"
                "Кто отвечает: курьер и куратор смены.\n"
                "Почему: нарушение стандартов доставки.\n"
                "Что делать сейчас: зафиксировать фото и оформить кейс.\n"
                "Правильное решение / тег: Неаккуратная доставка."
            ),
            "score": 0.98,
            "tags": ["damage"],
        },
        {
            "id": "faq_door",
            "q": "оставил заказ у двери без разрешения",
            "a": (
                "Суть ситуации: заказ оставлен без согласования.\n"
                "Кто отвечает: курьер.\n"
                "Почему: это нарушение сценария вручения.\n"
                "Что делать сейчас: связаться с клиентом и куратором.\n"
                "Правильное решение / тег: Оставил заказ без разрешения."
            ),
            "score": 0.97,
            "tags": ["delivery"],
        },
        {
            "id": "faq_rude",
            "q": "курьер нагрубил",
            "a": (
                "Суть ситуации: жалоба на общение.\n"
                "Кто отвечает: куратор.\n"
                "Почему: нарушение стандарта коммуникации.\n"
                "Что делать сейчас: собрать факты и передать ответственному.\n"
                "Правильное решение / тег: Коммуникация с клиентом."
            ),
            "score": 0.96,
            "tags": ["conflict"],
        },
        {
            "id": "faq_timeout",
            "q": "Не успеваю в таймер, пробка",
            "a": "Сообщи ETA и причину задержки в комментарии.",
            "score": 0.92,
            "tags": ["late_delivery"],
        },
        {
            "id": "faq_battery",
            "q": "АКБ дымит в шкафу",
            "a": "Прекрати зарядку, обесточь и эскалируй по безопасности.",
            "score": 0.95,
            "tags": ["battery_fire"],
        },
        {
            "id": "faq_missing",
            "q": "Не хватает пакета, недовоз",
            "a": "Проверь состав, отметь МП и сообщи в канал смены.",
            "score": 0.91,
            "tags": ["missing_items"],
        },
    ]


@pytest.fixture
def ai_service(monkeypatch):
    service = AICourierService(session_factory=_DummySession, router=_FakeProviderRouter())
    service._rule_reply_fn = None
    kb = _faq_knowledge()

    async def _fake_search(session, text, tags=None, top_k=3):
        lowered = (text or "").lower()
        hits = [item for item in kb if item["q"].lower() in lowered or lowered in item["q"].lower()]
        return hits[:top_k]

    monkeypatch.setattr(service._faq_repo, "search", _fake_search)
    return service


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "case",
    [
        _Case("Яйца приехали разбитые", "auto_answer", "Неаккуратная доставка"),
        _Case("оставил заказ у двери без разрешения", "auto_answer", "Оставил заказ"),
        _Case("курьер нагрубил", "auto_answer", "Коммуникация"),
        _Case("можно оштрафовать курьера?", "route_to_curator", "куратор"),
        _Case("полный возврат на терминале", "route_to_support", "поддержк"),
        _Case("Не успеваю в таймер, пробка", "auto_answer", "ETA"),
        _Case("АКБ дымит в шкафу", "auto_answer", "обесточь"),
        _Case("Не хватает пакета, недовоз", "auto_answer", "МП"),
        _Case("Не дозвонился клиенту, домофон", "auto_answer", "инструкции"),
        _Case("Произвольный неизвестный вопрос", "auto_answer", "инструкции"),
    ],
)
async def test_ai_policy_routes_golden_cases(ai_service: AICourierService, case: _Case):
    result = await ai_service.get_answer(user_id=42, text=case.text)
    assert _business_route(result) == case.expected_business_route
    assert case.must_contain.lower() in result.text.lower()


@pytest.mark.asyncio
async def test_ai_fallback_when_provider_unavailable(monkeypatch):
    service = AICourierService(session_factory=_DummySession, router=_FailingProviderRouter())
    service._rule_reply_fn = None

    async def _empty_search(session, text, tags=None, top_k=3):
        return []

    monkeypatch.setattr(service._faq_repo, "search", _empty_search)
    result = await service.get_answer(user_id=100, text="Что делать?")

    assert result.route == "fallback"
    assert result.text


class _NamedProvider(BaseProvider):
    def __init__(self, name: str):
        self.name = name
        self.enabled = True

    async def complete(self, messages, *, temperature=0.3, max_tokens=1024):
        return ProviderResponse(
            text=f"provider={self.name}",
            provider=self.name,
            model=f"{self.name}-model",
            usage_tokens=0,
        )


@pytest.mark.asyncio
async def test_provider_fallback_without_groq(monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    monkeypatch.setenv("AI_PROVIDER_ORDER_CHAT", "groq,deepseek,openai")
    router = ProviderRouter([_NamedProvider("deepseek"), _NamedProvider("openai")])
    resp = await router.complete([{"role": "user", "content": "test"}], mode="chat")
    assert resp.provider in {"deepseek", "openai"}
    assert resp.provider == "deepseek"
