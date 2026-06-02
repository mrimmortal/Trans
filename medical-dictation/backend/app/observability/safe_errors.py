"""Safe error message normalization for logs and API responses."""

import re


_SECRET_PATTERNS = [
    re.compile(r"(?i)(secret|token|key|password|credential)[A-Z0-9_ -]*=[^\s,;]+"),
]
_POSIX_PATH_PATTERN = re.compile(r"/(?:Users|private|var|tmp|Volumes|home)/[^\s,;]+")
_WINDOWS_PATH_PATTERN = re.compile(r"[A-Za-z]:\\[^\s,;]+")


def safe_error_message(error: Exception | str | None) -> str | None:
    """Return a short message without stack traces, secrets, or local paths."""
    if error is None:
        return None

    message = str(error).strip()
    if not message:
        return None

    message = message.splitlines()[0]
    for pattern in _SECRET_PATTERNS:
        message = pattern.sub("[redacted]", message)
    message = _POSIX_PATH_PATTERN.sub("[path]", message)
    message = _WINDOWS_PATH_PATTERN.sub("[path]", message)
    return message[:240]
