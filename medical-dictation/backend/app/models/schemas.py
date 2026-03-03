"""Pydantic schemas for request/response validation"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from enum import Enum
from datetime import datetime


class AudioFormat(str, Enum):
    """Supported audio formats"""
    WAV = "wav"
    PCM = "pcm"
    MP3 = "mp3"


class TranscriptionRequest(BaseModel):
    """Request for transcription"""
    audio_data: bytes = Field(..., description="Audio data bytes (int16 PCM, 16kHz, mono)")
    format: AudioFormat = Field(default=AudioFormat.WAV, description="Audio format")
    language: str = Field(default="en", description="Language code")
    temperature: float = Field(default=0.0, ge=0.0, le=1.0, description="Sampling temperature")


class TranscriptionResponse(BaseModel):
    """Response containing real-time transcription results"""
    type: str = Field(default="transcription", description="Message type")
    text: str = Field(..., description="Transcribed text (may be partial)")
    is_final: bool = Field(..., description="Whether transcription is complete")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score 0-1")
    processing_time_ms: float = Field(..., description="Time to process audio (milliseconds)")
    raw_text: Optional[str] = Field(default=None, description="Raw text before formatting")
    timestamp: float = Field(default_factory=lambda: datetime.utcnow().timestamp(), description="UTC timestamp")
    language: Optional[str] = Field(default="en", description="Detected language")
    error: Optional[str] = Field(default=None, description="Error message if failed")


class AudioChunk(BaseModel):
    """Audio chunk for streaming"""
    data: bytes = Field(..., description="Audio chunk data (int16 PCM)")
    sequence_num: int = Field(..., description="Sequence number for ordering")
    is_final: bool = Field(default=False, description="Whether this is the final chunk")


class WebSocketMessage(BaseModel):
    """WebSocket message envelope"""
    type: str = Field(..., description="Message type: audio, transcription, command, error, status")
    timestamp: float = Field(default_factory=lambda: datetime.utcnow().timestamp(), description="UTC timestamp")
    data: Optional[Dict[str, Any]] = Field(default=None, description="Message data")
    error: Optional[str] = Field(default=None, description="Error message if applicable")


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


class StatsResponse(BaseModel):
    """Server statistics response"""
    type: str = Field(default="stats", description="Message type")
    timestamp: float = Field(default_factory=lambda: datetime.utcnow().timestamp(), description="UTC timestamp")
    data: Dict[str, Any] = Field(
        ...,
        description="Statistics data (active_connections, total_audio_processed, model_loaded, uptime_seconds, etc.)"
    )


class MedicalNote(BaseModel):
    """Medical note/dictation"""
    id: str = Field(..., description="Unique note ID")
    content: str = Field(..., description="Note content")
    patient_id: Optional[str] = Field(default=None, description="Associated patient ID")
    patient_name: Optional[str] = Field(default=None, description="Patient name")
    note_type: Optional[str] = Field(default=None, description="Type of note (Progress, Encounter, etc.)")
    created_at: str = Field(..., description="Creation timestamp ISO 8601")
    updated_at: str = Field(..., description="Last update timestamp ISO 8601")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Additional metadata")


class VoiceCommandRequest(BaseModel):
    """Request to execute a voice command"""
    command_text: str = Field(..., description="Command text to process")
    context: Optional[str] = Field(default=None, description="Current note context")


class VoiceCommandResponse(BaseModel):
    """Response from voice command execution"""
    recognized: bool = Field(..., description="Whether command was recognized")
    action: Optional[str] = Field(default=None, description="Action to perform")
    text_to_insert: Optional[str] = Field(default=None, description="Text to insert")
    cursor_position: Optional[int] = Field(default=None, description="Cursor position after command")


class SessionStart(BaseModel):
    """WebSocket session initialization"""
    type: str = Field(default="session_start", description="Message type")
    session_id: str = Field(..., description="Unique session ID")
    timestamp: float = Field(default_factory=lambda: datetime.utcnow().timestamp(), description="UTC timestamp")


class SessionEnd(BaseModel):
    """WebSocket session termination"""
    type: str = Field(default="session_end", description="Message type")
    session_id: str = Field(..., description="Session ID being closed")
    timestamp: float = Field(default_factory=lambda: datetime.utcnow().timestamp(), description="UTC timestamp")
    total_audio_seconds: float = Field(..., description="Total audio processed in session")
    total_words: int = Field(..., description="Total words transcribed")

