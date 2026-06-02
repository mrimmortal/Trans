"""LM Studio OpenAI-compatible chat completions provider."""

import httpx

from app.models.schemas import LLMRespondResponse
from app.services.llm.base import LLMConfigError, LLMProviderError
from app.services.llm.config import LMStudioSettings


class LMStudioConfigError(LLMConfigError):
    """Raised when LM Studio configuration is incomplete."""


class LMStudioUnavailableError(LLMProviderError):
    """Raised when LM Studio cannot return a usable response."""


class LMStudioProvider:
    """Provider for LM Studio's OpenAI-compatible chat completions API."""

    def __init__(
        self,
        settings: LMStudioSettings,
        transport: httpx.BaseTransport | None = None,
    ):
        self._settings = settings
        self._transport = transport

    def respond(self, text: str, system_prompt: str | None = None) -> LLMRespondResponse:
        base_url = self._require_config_value("LM_STUDIO_BASE_URL", self._settings.base_url)
        model = self._require_config_value("LM_STUDIO_MODEL", self._settings.model)

        user_text = text.strip()
        if not user_text:
            raise ValueError("text must not be empty")

        payload = {
            "model": model,
            "messages": self._build_messages(user_text, system_prompt),
            "temperature": 0.2,
        }
        url = f"{base_url.rstrip('/')}/chat/completions"

        try:
            with httpx.Client(timeout=self._settings.timeout_seconds, transport=self._transport) as client:
                response = client.post(url, json=payload)
                response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            status_code = exc.response.status_code
            raise LMStudioUnavailableError(f"LM Studio returned HTTP {status_code}") from exc
        except (httpx.TimeoutException, httpx.RequestError) as exc:
            raise LMStudioUnavailableError("LM Studio is unavailable") from exc

        content = self._extract_response_content(response)
        return LLMRespondResponse(response=content, model=model)

    def check_health(self) -> dict:
        """Check LM Studio configuration and reachability without generating text."""
        try:
            base_url = self._require_config_value("LM_STUDIO_BASE_URL", self._settings.base_url)
            self._require_config_value("LM_STUDIO_MODEL", self._settings.model)
            url = f"{base_url.rstrip('/')}/models"

            with httpx.Client(timeout=self._settings.timeout_seconds, transport=self._transport) as client:
                response = client.get(url)
                response.raise_for_status()

            return {"status": "healthy", "reachable": True, "last_error": None}
        except LMStudioConfigError as exc:
            return {"status": "unhealthy", "reachable": False, "last_error": str(exc)}
        except httpx.HTTPStatusError as exc:
            return {
                "status": "unhealthy",
                "reachable": False,
                "last_error": f"LM Studio returned HTTP {exc.response.status_code}",
            }
        except (httpx.TimeoutException, httpx.RequestError):
            return {
                "status": "unhealthy",
                "reachable": False,
                "last_error": "LM Studio is unavailable",
            }

    def _require_config_value(self, name: str, value: str) -> str:
        if not isinstance(value, str) or not value.strip():
            raise LMStudioConfigError(f"{name} is required")
        return value.strip()

    def _build_messages(self, text: str, system_prompt: str | None) -> list[dict[str, str]]:
        messages: list[dict[str, str]] = []
        prompt = system_prompt.strip() if system_prompt else ""

        if prompt:
            messages.append({"role": "system", "content": prompt})

        messages.append({"role": "user", "content": text})
        return messages

    def _extract_response_content(self, response: httpx.Response) -> str:
        try:
            body = response.json()
            content = body["choices"][0]["message"]["content"]
        except (ValueError, KeyError, IndexError, TypeError) as exc:
            raise LMStudioUnavailableError("LM Studio returned a malformed response") from exc

        if not isinstance(content, str):
            raise LMStudioUnavailableError("LM Studio returned a malformed response")

        return content
