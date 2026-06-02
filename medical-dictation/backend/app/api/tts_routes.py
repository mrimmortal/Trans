"""Routes for local text-to-speech synthesis."""

import time

from fastapi import APIRouter, HTTPException, Request, Response

from app.dependencies import create_tts_service
from app.models.schemas import TTSSynthesizeRequest
from app.observability.events import log_event
from app.observability.request_id import request_id_from_state
from app.observability.safe_errors import safe_error_message
from app.services.tts.supertonic import (
    SupertonicConfigError,
    SupertonicSynthesisError,
)


router = APIRouter(prefix="/tts", tags=["tts"])


@router.post("/synthesize")
def synthesize_tts(request: Request, payload: TTSSynthesizeRequest) -> Response:
    """Synthesize speech using the configured local TTS provider."""
    started = time.perf_counter()
    request_id = request_id_from_state(request)
    service = create_tts_service()

    try:
        audio = service.synthesize(payload.text, voice=payload.voice, lang=payload.lang)
        log_event(
            category="TTS",
            event="tts.synthesize",
            status="success",
            provider="supertonic",
            duration_ms=(time.perf_counter() - started) * 1000,
            request_id=request_id,
            text_length=len(payload.text.strip()),
        )
    except SupertonicConfigError as exc:
        message = safe_error_message(exc) or "TTS configuration is invalid"
        log_event(
            category="TTS",
            event="tts.synthesize",
            status="error",
            provider="supertonic",
            duration_ms=(time.perf_counter() - started) * 1000,
            request_id=request_id,
            text_length=len(payload.text.strip()),
            error=message,
        )
        raise HTTPException(
            status_code=503,
            detail={"code": "TTS_CONFIG_ERROR", "message": message, "request_id": request_id},
        ) from exc
    except SupertonicSynthesisError as exc:
        message = safe_error_message(exc) or "TTS synthesis failed"
        log_event(
            category="TTS",
            event="tts.synthesize",
            status="error",
            provider="supertonic",
            duration_ms=(time.perf_counter() - started) * 1000,
            request_id=request_id,
            text_length=len(payload.text.strip()),
            error=message,
        )
        raise HTTPException(
            status_code=502,
            detail={"code": "TTS_SYNTHESIS_ERROR", "message": message, "request_id": request_id},
        ) from exc

    return Response(content=audio, media_type="audio/wav")
