"""Routes for local LLM responses."""

from fastapi import APIRouter, HTTPException

from app.audio_config import AudioConfig
from app.models.schemas import LLMRespondRequest, LLMRespondResponse
from app.services.llm.config import get_lm_studio_settings
from app.services.llm.lm_studio import (
    LMStudioProvider,
    LMStudioConfigError,
    LMStudioUnavailableError,
)
from app.services.llm.service import LLMService


router = APIRouter(prefix="/llm", tags=["llm"])


@router.post("/respond", response_model=LLMRespondResponse)
def respond_to_llm(request: LLMRespondRequest) -> LLMRespondResponse:
    """Generate a response using the configured LM Studio server."""
    provider = LMStudioProvider(get_lm_studio_settings(AudioConfig()))
    service = LLMService(provider)

    try:
        return service.respond(request.text, system_prompt=request.system_prompt)
    except LMStudioConfigError as exc:
        raise HTTPException(
            status_code=503,
            detail={"code": "LM_STUDIO_CONFIG_ERROR", "message": str(exc)},
        ) from exc
    except LMStudioUnavailableError as exc:
        raise HTTPException(
            status_code=502,
            detail={"code": "LM_STUDIO_UNAVAILABLE", "message": str(exc)},
        ) from exc
