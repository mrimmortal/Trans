"""Pydantic schemas for request/response validation"""

from pydantic import BaseModel, Field, field_validator
from typing import Optional, Dict, Any
from datetime import datetime


class ConnectionResponse(BaseModel):
    """Response when client connects to WebSocket"""
    type: str = Field(default="connection", description="Message type")
    message: str = Field(..., description="Greeting/status message")
    timestamp: float = Field(default_factory=lambda: datetime.utcnow().timestamp(), description="UTC timestamp")
    config: Dict[str, Any] = Field(
        default_factory=dict,
        description="Server configuration (sample_rate, channels, etc.)"
    )


class ErrorResponse(BaseModel):
    """Error response"""
    type: str = Field(default="error", description="Message type")
    message: str = Field(..., description="Error message")
    code: str = Field(..., description="Error code (e.g., 'INVALID_AUDIO', 'MODEL_ERROR')")
    timestamp: float = Field(default_factory=lambda: datetime.utcnow().timestamp(), description="UTC timestamp")
    details: Optional[Dict[str, Any]] = Field(default=None, description="Additional error details")


class LLMRespondRequest(BaseModel):
    """Request body for local LLM response generation."""

    text: str = Field(..., description="User text to send to the local LLM")
    system_prompt: Optional[str] = Field(default=None, description="Optional system prompt")

    @field_validator("text")
    @classmethod
    def text_must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("text must not be empty")
        return value


class LLMRespondResponse(BaseModel):
    """Response returned from the configured local LLM provider."""

    response: str = Field(..., description="Generated response text")
    model: str = Field(..., description="Configured local LLM model")
    provider: str = Field(default="lmstudio", description="LLM provider identifier")


class TTSSynthesizeRequest(BaseModel):
    """Request body for local text-to-speech synthesis."""

    text: str = Field(..., description="Text to synthesize")
    voice: Optional[str] = Field(default=None, description="Optional TTS voice identifier")
    lang: Optional[str] = Field(default=None, description="Optional language code")

    @field_validator("text")
    @classmethod
    def tts_text_must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("text must not be empty")
        return value
