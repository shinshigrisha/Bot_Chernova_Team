"""Telegram channel for notification delivery (sync for Celery worker)."""
import asyncio
from typing import Any

import httpx

from src.config import get_settings
from src.infra.notifications.channels import DeliveryResult


class TelegramChannel:
    """Sync Telegram sender for use from Celery worker. Handles 429 with retry_after."""

    def __init__(self) -> None:
        self._token = get_settings().bot_token
        self._base = f"https://api.telegram.org/bot{self._token}"

    def send_message(
        self,
        chat_id: int,
        text: str,
        topic_id: int | None = None,
    ) -> DeliveryResult:
        """Send message via Bot API. Returns DeliveryResult with retry_after on 429."""
        payload: dict[str, Any] = {"chat_id": chat_id, "text": text}
        if topic_id is not None:
            payload["message_thread_id"] = topic_id
        with httpx.Client(timeout=30.0) as client:
            resp = client.post(f"{self._base}/sendMessage", json=payload)
        if resp.status_code == 200:
            return DeliveryResult(success=True)
        if resp.status_code == 429:
            data = resp.json()
            retry_after = data.get("parameters", {}).get("retry_after", 60)
            return DeliveryResult(success=False, retry_after=retry_after, error_code=429)
        return DeliveryResult(success=False, error_code=resp.status_code)
