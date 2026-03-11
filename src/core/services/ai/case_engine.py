from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class CaseEngineResult:
    route: str
    answer: str
    need_clarify: bool
    clarify_question: str
    escalate: bool


class CaseEngine:
    _SUPPORTED_CASES = {
        "damaged_goods",
        "contact_customer",
        "missing_items",
        "late_delivery",
        "battery_fire",
        "payment_terminal",
        "payment_hyperlink",
        "rude_communication",
        "leave_at_door",
        "return_order",
    }

    _CASE_STEPS: dict[str, tuple[str, ...]] = {
        "damaged_goods": (
            "Фото повреждения.",
            "Сообщи клиенту, отметь в приложении.",
            "Без согласования повреждённую позицию не передавай.",
            "Спор — куратору.",
        ),
        "contact_customer": (
            "2–3 звонка с интервалом 1–2 мин.",
            "Проверь комментарий к адресу, код домофона, чат.",
            "Напиши клиенту, что на месте.",
            "Выжди регламент; нет ответа — недозвон и куратору.",
        ),
        "missing_items": (
            "Проверь по местам и позициям, термосумку, багажник.",
            "Отметь недовоз по регламенту.",
            "Куратору: номер заказа и чего не хватает.",
        ),
        "late_delivery": (
            "Оцени ETA, сообщи куратору номер заказа, ETA и причину.",
            "Причину в комментарии к заказу.",
            "Не гони ради таймера.",
        ),
        "battery_fire": (
            "Прекрати зарядку, обесточь АКБ.",
            "Отойди от дыма, убери людей.",
            "Сразу куратору/ответственному. АКБ не используй.",
        ),
        "payment_terminal": (
            "Проверь терминал, связь, пин.",
            "Если не пробивает — куратору, альтернативная оплата по регламенту.",
        ),
        "payment_hyperlink": (
            "Отправь ссылку на оплату из приложения/чата.",
            "Если ссылки нет или не открывается — куратору.",
        ),
        "rude_communication": (
            "Не переходи на тон клиента.",
            "Коротко по делу; при угрозах — куратору и выход из контакта.",
        ),
        "leave_at_door": (
            "Оставь у двери по запросу, зафиксируй в приложении.",
            "Фото по регламенту, если требуется.",
        ),
        "return_order": (
            "Оформи возврат по регламенту в приложении.",
            "Сообщи куратору причину и номер заказа.",
        ),
    }

    _ALWAYS_ESCALATE = {"battery_fire"}

    @staticmethod
    def _format_answer(steps: tuple[str, ...]) -> str:
        return " ".join(f"{idx}) {step}" for idx, step in enumerate(steps, start=1))

    def resolve(
        self,
        *,
        intent: str,
        confidence: float,
        clarify_question: str = "",
    ) -> CaseEngineResult | None:
        if intent not in self._SUPPORTED_CASES:
            return None
        if confidence < 0.50:
            return None

        need_clarify = bool(clarify_question) and confidence < 0.72 and intent not in self._ALWAYS_ESCALATE
        steps = self._CASE_STEPS[intent]
        answer = self._format_answer(steps)

        return CaseEngineResult(
            route="case_engine",
            answer=answer,
            need_clarify=need_clarify,
            clarify_question=clarify_question if need_clarify else "",
            escalate=intent in self._ALWAYS_ESCALATE,
        )
