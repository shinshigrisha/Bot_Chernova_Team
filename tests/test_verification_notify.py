"""Тесты уведомлений верификации: текст пользователю после решения админа."""

import pytest

from src.bot.admin.admin_handlers import _verification_notify_user_text


def test_verification_notify_user_approve() -> None:
    text = _verification_notify_user_text("approve")
    assert "одобрена" in text
    assert "/start" in text


def test_verification_notify_user_reject() -> None:
    text = _verification_notify_user_text("reject")
    assert "отклонена" in text
    assert "/start" in text


def test_verification_notify_user_other() -> None:
    text = _verification_notify_user_text("other")
    assert "Статус" in text or "изменён" in text
