"""Generic speech-to-text provider boundary."""

from typing import Protocol, TypedDict


class STTConfigError(Exception):
    """Raised when speech-to-text configuration or dependency setup is invalid."""


class STTProviderError(Exception):
    """Raised when a speech-to-text provider cannot return a usable result."""


class SpeechSegment(TypedDict):
    """Detected speech segment boundaries in samples."""

    start: int
    end: int


class SpeechDetectionResult(TypedDict):
    """Speech detection result returned by STT providers."""

    has_speech: bool
    speech_prob: float
    speech_segments: list[SpeechSegment]


class TranscriptionResult(TypedDict, total=False):
    """Transcription result returned by STT providers."""

    text: str
    is_final: bool
    confidence: float
    processing_time_ms: float
    language: str
    language_probability: float
    error: str | None


class STTProvider(Protocol):
    """Provider interface for speech detection and audio transcription."""

    def detect_speech(self, audio_bytes: bytes) -> SpeechDetectionResult:
        """Detect speech in raw PCM audio bytes."""
        ...

    def transcribe_audio_bytes(self, audio_bytes: bytes) -> TranscriptionResult:
        """Transcribe raw PCM audio bytes into the existing result dict contract."""
        ...
