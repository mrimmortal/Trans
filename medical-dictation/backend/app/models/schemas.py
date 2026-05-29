"""Pydantic schemas for request/response validation"""

from pydantic import BaseModel, Field
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
