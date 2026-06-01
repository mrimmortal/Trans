"""Configuration adapters for speech-to-text providers."""

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class FasterWhisperSettings:
    model_size: str
    device: str
    compute_type: str
    sample_rate: int
    language: str
    accent_support_enabled: bool


def get_faster_whisper_settings(config: Any) -> FasterWhisperSettings:
    """Build Faster-Whisper settings from central application config."""
    return FasterWhisperSettings(
        model_size=getattr(config, "MODEL_SIZE", "base.en"),
        device=getattr(config, "DEVICE", "cpu"),
        compute_type=getattr(config, "COMPUTE_TYPE", "int8"),
        sample_rate=getattr(config, "SAMPLE_RATE", 16000),
        language=getattr(config, "TRANSCRIPTION_LANGUAGE", "en"),
        accent_support_enabled=getattr(config, "ACCENT_SUPPORT_ENABLED", True),
    )
