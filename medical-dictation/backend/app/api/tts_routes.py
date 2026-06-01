"""Routes for local text-to-speech synthesis."""

from fastapi import APIRouter, HTTPException, Response

from app.dependencies import create_tts_service
from app.models.schemas import TTSSynthesizeRequest
from app.services.tts.supertonic import (
    SupertonicConfigError,
    SupertonicSynthesisError,
)


router = APIRouter(prefix="/tts", tags=["tts"])


@router.post("/synthesize")
def synthesize_tts(request: TTSSynthesizeRequest) -> Response:
    """Synthesize speech using the configured local TTS provider."""
    service = create_tts_service()

    try:
        audio = service.synthesize(request.text, voice=request.voice, lang=request.lang)
    except SupertonicConfigError as exc:
        raise HTTPException(
            status_code=503,
            detail={"code": "TTS_CONFIG_ERROR", "message": str(exc)},
        ) from exc
    except SupertonicSynthesisError as exc:
        raise HTTPException(
            status_code=502,
            detail={"code": "TTS_SYNTHESIS_ERROR", "message": str(exc)},
        ) from exc

    return Response(content=audio, media_type="audio/wav")
