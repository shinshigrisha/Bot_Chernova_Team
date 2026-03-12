"""n8n pilot: verification mirror — POST new verification application to n8n webhook.

Optional, behind N8N_VERIFICATION_MIRROR_ENABLED. Python remains source of truth;
this only notifies n8n for mirroring/notifications (e.g. admin Telegram channel).
"""

from __future__ import annotations

import logging
from typing import Any

import httpx

from src.config import get_settings
from src.core.services.verification_service import VerificationApplicationPayload

logger = logging.getLogger(__name__)

# Timeout for webhook POST so handler is not blocked
WEBHOOK_TIMEOUT = 5.0


def _build_payload(payload: VerificationApplicationPayload) -> dict[str, Any]:
    """Structured payload for n8n: event type + application data (no PII beyond what admins see)."""
    return {
        "event": "verification.pending",
        "tg_user_id": payload.tg_user_id,
        "role": payload.role.value,
        "first_name": payload.first_name,
        "last_name": payload.last_name,
        "tt_number": payload.tt_number,
        "ds_code": payload.ds_code,
        "phone": payload.phone,
    }


async def _send_webhook(url: str, body: dict[str, Any]) -> None:
    """POST to n8n webhook; log and swallow errors so caller is never broken."""
    try:
        async with httpx.AsyncClient(timeout=WEBHOOK_TIMEOUT) as client:
            resp = await client.post(url, json=body)
            if resp.status_code >= 400:
                logger.warning(
                    "n8n_verification_mirror_webhook_error",
                    status_code=resp.status_code,
                    body_preview=str(resp.text)[:200],
                )
    except Exception as exc:
        logger.warning("n8n_verification_mirror_webhook_failed", error=str(exc))


async def notify_verification_pending(payload: VerificationApplicationPayload) -> None:
    """If n8n verification mirror is enabled, POST payload to webhook.

    Call from handler after create_application_and_mark_pending. Intended to be
    run via asyncio.create_task() so the handler does not block; errors are
    logged only. Safe to call when disabled or URL empty — no-op.
    """
    settings = get_settings()
    if not settings.n8n_verification_mirror_enabled:
        return
    url = (settings.n8n_verification_webhook_url or "").strip()
    if not url:
        logger.debug("n8n_verification_mirror_skipped", reason="webhook_url_empty")
        return
    body = _build_payload(payload)
    await _send_webhook(url, body)
