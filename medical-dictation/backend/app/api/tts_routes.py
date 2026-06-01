"""Routes for local text-to-speech synthesis."""

from fastapi import APIRouter, HTTPException, Response

from app.audio_config import AudioConfig
from app.models.schemas import TTSSynthesizeRequest
from app.services.tts.config import get_supertonic_settings
from app.services.tts.service import TTSService
from app.services.tts.supertonic import (
    SupertonicProvider,
    SupertonicConfigError,
    SupertonicSynthesisError,
)


router = APIRouter(prefix="/tts", tags=["tts"])


@router.post("/synthesize")
def synthesize_tts(request: TTSSynthesizeRequest) -> Response:
    """Synthesize speech using the configured local TTS provider."""
    provider = SupertonicProvider(get_supertonic_settings(AudioConfig()))
    service = TTSService(provider)

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
