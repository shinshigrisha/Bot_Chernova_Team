from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from src.core.services.ai.provider_router import ProviderRouter


@dataclass(slots=True, frozen=True)
class DeliveryMetrics:
    """Precomputed metrics for last-mile analytics (successful deliveries only)."""

    tt_code: str
    total_deliveries: int
    median_delivery_time_min: float
    p90_delivery_time_min: float
    share_late_deliveries: float
    share_courier_issues: float
    share_client_issues: float
    share_logistics_issues: float
    additional_metrics: dict[str, Any] | None = None


class AnalyticsAssistant:
    """LLM-backed analytics explainer for CSV-based last-mile metrics.

    The assistant:
    - НЕ считает метрики: они приходят готовыми из кода/ETL.
    - Строит текстовый отчёт: объяснение, сравнение, приоритезация.
    - Работает только с успешными доставками (гарантия на уровне пайплайна).
    """

    def __init__(
        self,
        router: ProviderRouter | None,
        data_root: str | Path = "data/ai/prompts",
    ) -> None:
        self._router = router
        self._data_root = Path(data_root)
        self._system_prompt = self._load_text("last_mile_analyst_system.md")
        self._rules = self._load_text("last_mile_analyst_rules.md")
        self._report_format = self._load_text("last_mile_analyst_report_format.md")

    def _load_text(self, filename: str) -> str:
        path = self._data_root / filename
        if not path.exists():
            return ""
        return path.read_text(encoding="utf-8")

    async def build_report(
        self,
        *,
        tt_metrics: Iterable[DeliveryMetrics],
        global_summary: dict[str, Any] | None = None,
        raw_sample_notes: str | None = None,
    ) -> str:
        """Сформировать структурированный аналитический отчёт по успешным доставкам.

        Метрики уже посчитаны в коде. LLM:
        - объясняет паттерны и аномалии,
        - сравнивает ТТ между собой,
        - формирует выводы и рекомендации в строгом формате.
        """
        if self._router is None or not self._router.providers:
            return "Аналитический ассистент недоступен: нет подключённых LLM-провайдеров."

        tt_blocks: list[str] = []
        for m in tt_metrics:
            extras = m.additional_metrics or {}
            extras_lines = "\n".join(
                f"- {k}: {v}" for k, v in sorted(extras.items())
            ) if extras else ""
            tt_text = (
                f"TT: {m.tt_code}\n"
                f"- total_deliveries: {m.total_deliveries}\n"
                f"- median_delivery_time_min: {m.median_delivery_time_min:.2f}\n"
                f"- p90_delivery_time_min: {m.p90_delivery_time_min:.2f}\n"
                f"- share_late_deliveries: {m.share_late_deliveries:.4f}\n"
                f"- share_courier_issues: {m.share_courier_issues:.4f}\n"
                f"- share_client_issues: {m.share_client_issues:.4f}\n"
                f"- share_logistics_issues: {m.share_logistics_issues:.4f}\n"
            )
            if extras_lines:
                tt_text += extras_lines + "\n"
            tt_blocks.append(tt_text.strip())

        metrics_block = "\n\n".join(tt_blocks) if tt_blocks else "Нет данных по успешным доставкам."
        global_block = ""
        if global_summary:
            lines = [f"- {k}: {v}" for k, v in sorted(global_summary.items())]
            global_block = "Глобальные агрегаты по всем ТТ:\n" + "\n".join(lines)

        user_content_parts = [
            "Исходные агрегированные метрики по CSV (ТОЛЬКО успешные доставки):",
            metrics_block,
        ]
        if global_block:
            user_content_parts.append(global_block)
        if raw_sample_notes:
            user_content_parts.append(
                "Дополнительные заметки/контекст от аналитического пайплайна:\n"
                + raw_sample_notes
            )

        user_content = "\n\n".join(part for part in user_content_parts if part).strip()

        system_parts = [
            self._system_prompt.strip(),
            self._rules.strip(),
            self._report_format.strip(),
        ]
        system_text = "\n\n---\n\n".join(p for p in system_parts if p).strip()

        messages = [
            {"role": "system", "content": system_text},
            {"role": "user", "content": user_content},
        ]

        resp = await self._router.complete(
            messages,
            mode="analysis",
            temperature=0.1,
        )
        return resp.text.strip()

