"""Application composition helpers for backend services."""

from app.audio_config import AudioConfig
from app.services.llm.config import get_lm_studio_settings
from app.services.llm.lm_studio import LMStudioProvider
from app.services.llm.service import LLMService
from app.services.stt.faster_whisper import FasterWhisperSTTProvider
from app.services.stt.service import STTService
from app.services.tts.config import get_supertonic_settings
from app.services.tts.service import TTSService
from app.services.tts.supertonic import SupertonicProvider


def create_stt_service(config: AudioConfig) -> STTService:
    """Create the speech-to-text service with the configured provider."""
    return STTService(FasterWhisperSTTProvider(config))


def create_llm_service(config: AudioConfig | None = None) -> LLMService:
    """Create the local LLM service with the configured provider."""
    audio_config = config or AudioConfig()
    return LLMService(LMStudioProvider(get_lm_studio_settings(audio_config)))


def create_tts_service(config: AudioConfig | None = None) -> TTSService:
    """Create the local TTS service with the configured provider."""
    audio_config = config or AudioConfig()
    return TTSService(SupertonicProvider(get_supertonic_settings(audio_config)))
