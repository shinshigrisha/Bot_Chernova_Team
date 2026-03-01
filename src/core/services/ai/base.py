from __future__ import annotations

import abc
from dataclasses import dataclass


@dataclass
class LLMResponse:
    text: str
    provider: str
    model: str
    usage_tokens: int = 0


class BaseProvider(abc.ABC):
    name: str
    default_model: str

    @abc.abstractmethod
    async def complete(
        self,
        messages: list[dict[str, str]],
        *,
        temperature: float = 0.3,
        max_tokens: int = 1024,
    ) -> LLMResponse: ...

    async def close(self) -> None:
        pass
