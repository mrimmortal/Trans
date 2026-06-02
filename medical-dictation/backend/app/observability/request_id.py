"""Request ID helpers for HTTP request correlation."""

from uuid import uuid4

from fastapi import Request

REQUEST_ID_HEADER = "x-request-id"


def get_or_create_request_id(request: Request) -> str:
    """Return client-provided request ID or generate a new one."""
    request_id = request.headers.get(REQUEST_ID_HEADER, "").strip()
    if request_id:
        return request_id
    return str(uuid4())


def request_id_from_state(request: Request) -> str:
    """Read request ID set by middleware, falling back to a generated value."""
    request_id = getattr(request.state, "request_id", "")
    if request_id:
        return request_id
    return get_or_create_request_id(request)
