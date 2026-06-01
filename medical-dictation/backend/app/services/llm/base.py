"""Generic local LLM provider boundary."""

from typing import Protocol

from app.models.schemas import LLMRespondResponse


class LLMConfigError(Exception):
    """Raised when local LLM configuration is incomplete or invalid."""


class LLMProviderError(Exception):
    """Raised when a local LLM provider cannot return a usable response."""


class LLMProvider(Protocol):
    """Provider interface for local LLM response generation."""

    def respond(self, text: str, system_prompt: str | None = None) -> LLMRespondResponse:
        """Generate a response for user text."""
        ...
