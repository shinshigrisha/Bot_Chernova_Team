"""Channel interface for notification delivery."""
from typing import Protocol


class DeliveryResult:
    """Result of a single delivery attempt."""

    __slots__ = ("success", "retry_after", "error_code")

    def __init__(
        self,
        success: bool,
        retry_after: int | None = None,
        error_code: int | None = None,
    ) -> None:
        self.success = success
        self.retry_after = retry_after  # for 429
        self.error_code = error_code


class NotificationChannelProtocol(Protocol):
    """Protocol for notification delivery channels."""

    def send_message(
        self,
        chat_id: int,
        text: str,
        topic_id: int | None = None,
    ) -> DeliveryResult:
        """Send message; return result with success/retry_after/error_code."""
        ...
