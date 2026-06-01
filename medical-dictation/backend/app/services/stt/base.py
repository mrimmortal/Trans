"""Generic speech-to-text provider boundary."""

from typing import Protocol


class STTConfigError(Exception):
    """Raised when speech-to-text configuration or dependency setup is invalid."""


class STTProviderError(Exception):
    """Raised when a speech-to-text provider cannot return a usable result."""


class STTProvider(Protocol):
    """Provider interface for speech detection and audio transcription."""

    def detect_speech(self, audio_bytes: bytes) -> dict:
        """Detect speech in raw PCM audio bytes."""
        ...

    def transcribe_audio_bytes(self, audio_bytes: bytes) -> dict:
        """Transcribe raw PCM audio bytes into the existing result dict contract."""
        ...
