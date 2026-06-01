"""Application service for speech-to-text operations."""

from app.services.stt.base import STTProvider


class STTService:
    """Use-case boundary for speech detection and transcription."""

    def __init__(self, provider: STTProvider):
        self._provider = provider

    def detect_speech(self, audio_bytes: bytes) -> dict:
        return self._provider.detect_speech(audio_bytes)

    def transcribe_audio_bytes(self, audio_bytes: bytes) -> dict:
        return self._provider.transcribe_audio_bytes(audio_bytes)

    @property
    def model(self):
        return getattr(self._provider, "model", None)

    @property
    def vad_model(self):
        return getattr(self._provider, "vad_model", None)

    def get_device_info(self) -> dict:
        if hasattr(self._provider, "get_device_info"):
            return self._provider.get_device_info()
        return {}
