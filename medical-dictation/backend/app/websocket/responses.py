"""WebSocket response builders for the audio streaming protocol."""

from datetime import datetime, timezone
from typing import Any

from app.domains.registry import get_available_domains


def build_welcome_config(config: Any, engine: Any, handler: Any) -> dict:
    """Build the connection config sent immediately after WebSocket accept."""
    return {
        "sample_rate": config.SAMPLE_RATE,
        "channels": config.CHANNELS,
        "sample_width": config.SAMPLE_WIDTH,
        "min_chunk_bytes": config.MIN_CHUNK_SIZE_BYTES,
        "max_chunk_bytes": config.MAX_CHUNK_SIZE_BYTES,
        "overlap_bytes": config.OVERLAP_SIZE_BYTES,
        "model": config.MODEL_SIZE,
        "device": config.DEVICE,
        "language": config.TRANSCRIPTION_LANGUAGE,
        "accent_support_enabled": config.ACCENT_SUPPORT_ENABLED,
        "domain": handler.domain,
        "available_domains": get_available_domains(),
        "vad_enabled": engine.vad_model is not None,
        "commands_enabled": handler.domain_adapter.commands_enabled,
        "available_commands": handler.command_processor.get_available_commands(),
    }


def build_transcription_message(
    result: dict,
    fallback_domain: str,
    *,
    timestamp_format: str = "float",
) -> dict:
    """Build the transcription event sent to the frontend."""
    timestamp = datetime.now(timezone.utc)
    if timestamp_format == "iso":
        timestamp_value = timestamp.isoformat()
    else:
        timestamp_value = timestamp.timestamp()

    return {
        "type": "transcription",
        "text": result["text"],
        "domain": result.get("domain", fallback_domain),
        "commands": result.get("commands", []),
        "is_final": True,
        "confidence": 0.95,
        "processing_time_ms": result.get("processing_time_ms", 0.0),
        "audio_duration_seconds": result.get("audio_duration_seconds", 0.0),
        "flush_reason": result.get("flush_reason", "unknown"),
        "timestamp": timestamp_value,
    }
