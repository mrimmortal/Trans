"""Routes for local text-to-speech synthesis."""

from fastapi import APIRouter, HTTPException, Response

from app.audio_config import AudioConfig
from app.models.schemas import TTSSynthesizeRequest
from app.services.supertonic_tts_client import (
    SupertonicConfigError,
    SupertonicSynthesisError,
    SupertonicTTSClient,
)


router = APIRouter(prefix="/tts", tags=["tts"])


@router.post("/synthesize")
def synthesize_tts(request: TTSSynthesizeRequest) -> Response:
    """Synthesize speech using the configured local TTS provider."""
    client = SupertonicTTSClient(AudioConfig())

    try:
        audio = client.synthesize(request.text, voice=request.voice, lang=request.lang)
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
