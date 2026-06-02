"""Routes for local LLM responses."""

import time

from fastapi import APIRouter, HTTPException, Request

from app.dependencies import create_llm_service
from app.models.schemas import LLMRespondRequest, LLMRespondResponse
from app.observability.events import log_event
from app.observability.request_id import request_id_from_state
from app.observability.safe_errors import safe_error_message
from app.services.llm.lm_studio import (
    LMStudioConfigError,
    LMStudioUnavailableError,
)


router = APIRouter(prefix="/llm", tags=["llm"])


@router.post("/respond", response_model=LLMRespondResponse)
def respond_to_llm(request: Request, payload: LLMRespondRequest) -> LLMRespondResponse:
    """Generate a response using the configured LM Studio server."""
    started = time.perf_counter()
    request_id = request_id_from_state(request)
    service = create_llm_service()

    try:
        response = service.respond(payload.text, system_prompt=payload.system_prompt)
        log_event(
            category="LLM",
            event="llm.respond",
            status="success",
            provider=response.provider,
            duration_ms=(time.perf_counter() - started) * 1000,
            request_id=request_id,
            text_length=len(payload.text.strip()),
        )
        return response
    except LMStudioConfigError as exc:
        message = safe_error_message(exc) or "LM Studio configuration is invalid"
        log_event(
            category="LLM",
            event="llm.respond",
            status="error",
            provider="lmstudio",
            duration_ms=(time.perf_counter() - started) * 1000,
            request_id=request_id,
            text_length=len(payload.text.strip()),
            error=message,
        )
        raise HTTPException(
            status_code=503,
            detail={"code": "LM_STUDIO_CONFIG_ERROR", "message": message, "request_id": request_id},
        ) from exc
    except LMStudioUnavailableError as exc:
        message = safe_error_message(exc) or "LM Studio is unavailable"
        log_event(
            category="LLM",
            event="llm.respond",
            status="error",
            provider="lmstudio",
            duration_ms=(time.perf_counter() - started) * 1000,
            request_id=request_id,
            text_length=len(payload.text.strip()),
            error=message,
        )
        raise HTTPException(
            status_code=502,
            detail={"code": "LM_STUDIO_UNAVAILABLE", "message": message, "request_id": request_id},
        ) from exc
