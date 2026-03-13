"""Тесты конфигурации: get_settings, парсинг ADMIN_IDS."""
import pytest

from src.config import get_settings


def test_get_settings_returns_settings() -> None:
    """get_settings() возвращает объект с ожидаемыми атрибутами."""
    s = get_settings()
    assert hasattr(s, "bot_token")
    assert hasattr(s, "admin_ids")
    assert hasattr(s, "database_url")
    assert hasattr(s, "redis_url")
    assert hasattr(s, "ai_enabled")
    assert isinstance(s.admin_ids, list)
