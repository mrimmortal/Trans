"""Configuration adapters for local LLM providers."""

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class LMStudioSettings:
    base_url: str
    model: str
    timeout_seconds: float


def get_lm_studio_settings(config: Any) -> LMStudioSettings:
    """Build LM Studio settings from central application config."""
    return LMStudioSettings(
        base_url=getattr(config, "LM_STUDIO_BASE_URL", ""),
        model=getattr(config, "LM_STUDIO_MODEL", ""),
        timeout_seconds=getattr(config, "LM_STUDIO_TIMEOUT_SECONDS", 30.0),
    )
