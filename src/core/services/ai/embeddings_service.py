from __future__ import annotations

import json
import logging
from collections.abc import Sequence

from openai import AsyncOpenAI  # type: ignore[import]

from src.config import get_settings

logger = logging.getLogger(__name__)


class EmbeddingsService:
    """OpenAI embeddings wrapper with graceful fallback."""

    _MODEL = "text-embedding-3-small"

    def __init__(self) -> None:
        settings = get_settings()
        api_key = settings.openai_api_key.strip()
        self.enabled = bool(api_key)
        self._client = AsyncOpenAI(api_key=api_key) if self.enabled else None

    @property
    def model(self) -> str:
        return self._MODEL

    @staticmethod
    def build_faq_text(question: str, answer: str) -> str:
        return f"Вопрос: {question.strip()}\nОтвет: {answer.strip()}"

    @staticmethod
    def serialize_embedding(embedding: Sequence[float] | None) -> str | None:
        if not embedding:
            return None
        return json.dumps([float(value) for value in embedding], separators=(",", ":"))

    async def embed_text(self, text: str) -> list[float] | None:
        if not self.enabled or self._client is None:
            return None
        normalized_text = (text or "").strip()
        if not normalized_text:
            return None

        try:
            response = await self._client.embeddings.create(
                model=self._MODEL,
                input=normalized_text,
            )
        except Exception as exc:
            logger.warning("embeddings_disabled: %s", exc)
            return None

        if not response.data:
            return None
        return [float(value) for value in response.data[0].embedding]

    async def embed_texts(self, texts: Sequence[str]) -> list[list[float] | None]:
        if not self.enabled or self._client is None:
            return [None for _ in texts]

        normalized_texts = [str(text).strip() for text in texts]
        if not normalized_texts:
            return []

        try:
            response = await self._client.embeddings.create(
                model=self._MODEL,
                input=normalized_texts,
            )
        except Exception as exc:
            logger.warning("embeddings_batch_disabled: %s", exc)
            return [None for _ in texts]

        result: list[list[float] | None] = [None for _ in normalized_texts]
        for item in response.data:
            result[item.index] = [float(value) for value in item.embedding]
        return result

    async def close(self) -> None:
        if self._client is not None:
            await self._client.close()
