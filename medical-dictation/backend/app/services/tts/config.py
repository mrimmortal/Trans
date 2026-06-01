"""Configuration adapters for local text-to-speech providers."""

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class SupertonicSettings:
    provider: str
    voice: str
    lang: str
    output_dir: str


def get_supertonic_settings(config: Any) -> SupertonicSettings:
    """Build Supertonic settings from central application config."""
    return SupertonicSettings(
        provider=getattr(config, "TTS_PROVIDER", "supertonic"),
        voice=getattr(config, "SUPERTONIC_VOICE", "M1"),
        lang=getattr(config, "SUPERTONIC_LANG", "en"),
        output_dir=getattr(config, "TTS_OUTPUT_DIR", ""),
    )
