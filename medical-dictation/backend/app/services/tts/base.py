"""Generic local text-to-speech provider boundary."""

from typing import Protocol


class TTSConfigError(Exception):
    """Raised when local TTS configuration or dependency setup is invalid."""


class TTSProviderError(Exception):
    """Raised when a local TTS provider cannot synthesize usable audio."""


class TTSProvider(Protocol):
    """Provider interface for local text-to-speech synthesis."""

    def synthesize(self, text: str, voice: str | None = None, lang: str | None = None) -> bytes:
        """Synthesize text into playable audio bytes."""
        ...
