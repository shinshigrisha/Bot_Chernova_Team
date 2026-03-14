"""Canonical embeddings backend: config-driven provider (local SentenceTransformer or OpenAI).

Single implementation used by: FAQ semantic search, rebuild_faq_embeddings,
rebuild_case_embeddings, CaseClassifier, AICourierService, RAGService.
Config: EMBEDDING_PROVIDER=local|openai, EMBEDDING_MODEL (e.g. sentence-transformers/all-MiniLM-L6-v2).
"""

from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import Sequence

from src.config import get_settings

logger = logging.getLogger(__name__)

_backend_logged: bool = False


def _log_backend_once(provider: str, model: str, enabled: bool) -> None:
    global _backend_logged
    if _backend_logged:
        return
    _backend_logged = True
    logger.info(
        "embedding_backend: provider=%s model=%s enabled=%s",
        provider,
        model,
        enabled,
    )


class _LocalBackend:
    """Local SentenceTransformer backend. Lazy-loads model on first use."""

    def __init__(self, model_name: str) -> None:
        self._model_name = model_name
        self._model = None

    def _get_model(self):
        if self._model is None:
            from sentence_transformers import SentenceTransformer

            self._model = SentenceTransformer(self._model_name)
        return self._model

    def embed_sync(self, text: str) -> list[float] | None:
        text = (text or "").strip()
        if not text:
            return None
        try:
            model = self._get_model()
            vec = model.encode(text, convert_to_numpy=True)
            return [float(x) for x in vec]
        except Exception as exc:
            logger.warning("local_embedding_error: %s", exc)
            return None

    def embed_many_sync(self, texts: Sequence[str]) -> list[list[float] | None]:
        if not texts:
            return []
        normalized = [str(t).strip() for t in texts]
        if not normalized:
            return []
        try:
            model = self._get_model()
            matrix = model.encode(normalized, convert_to_numpy=True)
            return [[float(x) for x in row] for row in matrix]
        except Exception as exc:
            logger.warning("local_embedding_batch_error: %s", exc)
            return [None for _ in normalized]


class EmbeddingsService:
    """Config-driven embeddings: local (SentenceTransformer) or openai."""

    def __init__(self) -> None:
        settings = get_settings()
        self._provider = (settings.embedding_provider or "local").strip().lower()
        self._model = (settings.embedding_model or "").strip() or "sentence-transformers/all-MiniLM-L6-v2"

        self._local: _LocalBackend | None = None
        self._openai_client = None
        self.enabled = True

        if self._provider == "local":
            self._local = _LocalBackend(self._model)
            _log_backend_once(self._provider, self._model, True)
        else:
            try:
                from openai import AsyncOpenAI  # type: ignore[import]

                api_key = (getattr(settings, "openai_api_key", None) or "").strip()
                self.enabled = bool(api_key)
                self._openai_client = AsyncOpenAI(api_key=api_key) if self.enabled else None
                _log_backend_once(self._provider, self._model, self.enabled)
            except Exception as exc:
                logger.warning("embedding_openai_init: %s", exc)
                self.enabled = False
                _log_backend_once(self._provider, self._model, False)

    @property
    def model(self) -> str:
        return self._model

    @property
    def provider(self) -> str:
        """Current embedding provider (local | openai) for runtime logs."""
        return self._provider

    @staticmethod
    def build_faq_text(question: str, answer: str) -> str:
        return f"Вопрос: {question.strip()}\nОтвет: {answer.strip()}"

    @staticmethod
    def serialize_embedding(embedding: Sequence[float] | None) -> str | None:
        if not embedding:
            return None
        return json.dumps([float(value) for value in embedding], separators=(",", ":"))

    async def embed_text(self, text: str) -> list[float] | None:
        if self._local is not None:
            return await asyncio.to_thread(self._local.embed_sync, text)
        if not self.enabled or self._openai_client is None:
            return None
        normalized_text = (text or "").strip()
        if not normalized_text:
            return None
        try:
            response = await self._openai_client.embeddings.create(
                model=self._model,
                input=normalized_text,
            )
        except Exception as exc:
            logger.warning("embeddings_disabled: %s", exc)
            return None
        if not response.data:
            return None
        return [float(value) for value in response.data[0].embedding]

    async def embed_texts(self, texts: Sequence[str]) -> list[list[float] | None]:
        if self._local is not None:
            return await asyncio.to_thread(
                self._local.embed_many_sync,
                list(texts),
            )
        if not self.enabled or self._openai_client is None:
            return [None for _ in texts]
        normalized_texts = [str(text).strip() for text in texts]
        if not normalized_texts:
            return []
        try:
            response = await self._openai_client.embeddings.create(
                model=self._model,
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
        if self._openai_client is not None:
            await self._openai_client.close()
