"""Safe structured event logging."""

import json
import logging
from typing import Any

from app.observability.safe_errors import safe_error_message

logger = logging.getLogger(__name__)


def log_event(
    *,
    category: str,
    event: str,
    status: str,
    provider: str | None = None,
    duration_ms: float | None = None,
    request_id: str | None = None,
    session_id: str | None = None,
    error: Exception | str | None = None,
    **safe_fields: Any,
) -> None:
    """Log a compact JSON event with only safe metadata."""
    payload: dict[str, Any] = {
        "category": category,
        "event": event,
        "status": status,
    }
    if provider:
        payload["provider"] = provider
    if duration_ms is not None:
        payload["duration_ms"] = round(float(duration_ms), 2)
    if request_id:
        payload["request_id"] = request_id
    if session_id:
        payload["session_id"] = session_id

    safe_error = safe_error_message(error)
    if safe_error:
        payload["error"] = safe_error

    payload.update({key: value for key, value in safe_fields.items() if value is not None})
    logger.info(json.dumps(payload, sort_keys=True))
