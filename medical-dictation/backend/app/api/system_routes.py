"""System REST routes for health, root metadata, and runtime config."""

import logging

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from app.domains.registry import get_available_domains

router = APIRouter(tags=["system"])
logger = logging.getLogger(__name__)


@router.get("/")
async def root(request: Request):
    """Root endpoint with API overview."""
    return {
        "status": "online",
        "service": "Transcription Template API",
        "version": "1.0.0",
        "active_connections": getattr(request.app.state, "active_connections", 0),
        "endpoints": {
            "docs": "/docs",
            "health": "/health",
            "config": "/config",
            "websocket": "/ws/audio",
        },
    }


@router.get("/health")
async def health(request: Request):
    """Detailed health check with model status."""
    try:
        stt_service = request.app.state.stt_service
        config = request.app.state.config
        vad_status = "enabled" if stt_service.vad_model is not None else "disabled (fallback to RMS)"

        return JSONResponse(
            content={
                "status": "healthy",
                "model": {
                    "loaded": stt_service.model is not None,
                    "size": config.MODEL_SIZE,
                    "device": config.DEVICE,
                },
                "vad_status": vad_status,
                "active_connections": getattr(request.app.state, "active_connections", 0),
            },
            status_code=200,
        )
    except Exception as e:
        logger.error("Health check failed: %s", e)
        return JSONResponse(
            content={"status": "unhealthy", "error": str(e)},
            status_code=503,
        )


@router.get("/config")
async def get_config(request: Request):
    """Get current audio and system configuration."""
    try:
        config = request.app.state.config
        return {
            "audio": {
                "sample_rate": config.SAMPLE_RATE,
                "channels": config.CHANNELS,
                "sample_width": config.SAMPLE_WIDTH,
                "min_chunk_bytes": config.MIN_CHUNK_SIZE_BYTES,
                "max_chunk_bytes": config.MAX_CHUNK_SIZE_BYTES,
                "overlap_bytes": config.OVERLAP_SIZE_BYTES,
            },
            "model": {
                "size": config.MODEL_SIZE,
                "device": config.DEVICE,
                "language": config.TRANSCRIPTION_LANGUAGE,
                "accent_support_enabled": config.ACCENT_SUPPORT_ENABLED,
            },
            "domains": {
                "default": config.DEFAULT_TRANSCRIPTION_DOMAIN,
                "available": get_available_domains(),
            },
            "vad_enabled": request.app.state.stt_service.vad_model is not None,
        }
    except Exception as e:
        logger.error("Get config failed: %s", e)
        return JSONResponse(
            content={"error": str(e)},
            status_code=500,
        )
