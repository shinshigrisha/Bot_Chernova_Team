from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from src.config import get_settings


class AIModeCapability(str, Enum):
    """Canonical capability classes for LLM routing."""

    DEFAULT = "default"
    FAST_CHAT = "fast_chat"
    REASONING = "reasoning"
    ANALYTICS = "analytics"
    FALLBACK = "fallback"


@dataclass(frozen=True)
class ModelConfig:
    """Provider + model pair for a given capability."""

    provider: str
    model: str


def _normalize_mode(mode: str | AIModeCapability | None) -> AIModeCapability:
    """Map arbitrary mode strings used in code to canonical capability classes."""
    if mode is None:
        return AIModeCapability.DEFAULT
    if isinstance(mode, AIModeCapability):
        return mode

    name = mode.strip().lower()
    if name in {"fast", "fast_chat", "chat"}:
        return AIModeCapability.FAST_CHAT
    if name in {"reason", "reasoning"}:
        return AIModeCapability.REASONING
    if name in {"analysis", "analytics"}:
        return AIModeCapability.ANALYTICS
    if name in {"fallback"}:
        return AIModeCapability.FALLBACK
    return AIModeCapability.DEFAULT


def get_model_config(mode: str | AIModeCapability | None) -> ModelConfig:
    """Return provider+model for given logical mode.

    All concrete model names are stored here and come from env via Settings.
    Runtime code should not hardcode model identifiers.
    """
    settings = get_settings()
    capability = _normalize_mode(mode)

    if capability is AIModeCapability.FAST_CHAT:
        return ModelConfig(
            provider=settings.ai_fast_provider,
            model=settings.ai_fast_model,
        )
    if capability is AIModeCapability.REASONING:
        return ModelConfig(
            provider=settings.ai_reasoning_provider,
            model=settings.ai_reasoning_model,
        )
    if capability is AIModeCapability.ANALYTICS:
        return ModelConfig(
            provider=settings.ai_analytics_provider,
            model=settings.ai_analytics_model,
        )
    if capability is AIModeCapability.FALLBACK:
        return ModelConfig(
            provider=settings.ai_fallback_provider,
            model=settings.ai_fallback_model,
        )

    # DEFAULT
    return ModelConfig(
        provider=settings.ai_default_provider,
        model=settings.ai_default_model,
    )

