"""Application service for local LLM response generation."""

from app.models.schemas import LLMRespondResponse
from app.services.llm.base import LLMProvider


class LLMService:
    """Use-case boundary for generating local LLM responses."""

    def __init__(self, provider: LLMProvider):
        self._provider = provider

    def respond(self, text: str, system_prompt: str | None = None) -> LLMRespondResponse:
        clean_text = text.strip()
        if not clean_text:
            raise ValueError("text must not be empty")

        clean_prompt = system_prompt.strip() if system_prompt else None
        return self._provider.respond(clean_text, system_prompt=clean_prompt)
