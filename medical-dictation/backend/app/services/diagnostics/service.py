"""Provider-neutral diagnostics aggregation."""

from typing import Any

from app.audio_config import AudioConfig
from app.observability.metrics import STTMetrics
from app.observability.safe_errors import safe_error_message
from app.services.llm.config import get_lm_studio_settings
from app.services.llm.lm_studio import LMStudioProvider
from app.services.tts.config import get_supertonic_settings
from app.services.tts.supertonic import SupertonicProvider


def aggregate_status(*statuses: str) -> str:
    if any(status == "unhealthy" for status in statuses):
        return "unhealthy"
    if any(status == "degraded" for status in statuses):
        return "degraded"
    return "healthy"


class DiagnosticsService:
    """Build safe diagnostic snapshots for backend providers."""

    def __init__(self, config: AudioConfig, stt_service: Any, stt_metrics: STTMetrics | None = None):
        self._config = config
        self._stt_service = stt_service
        self._stt_metrics = stt_metrics

    def backend(self) -> dict:
        return {
            "status": "healthy",
            "service": "Transcription Template API",
            "environment": getattr(self._config, "ENVIRONMENT", "development"),
        }

    def stt(self) -> dict:
        model_loaded = getattr(self._stt_service, "model", None) is not None
        vad_enabled = getattr(self._stt_service, "vad_model", None) is not None
        metrics = self._metrics_snapshot(vad_enabled)

        return {
            "status": "healthy" if model_loaded else "unhealthy",
            "provider": "faster_whisper",
            "configured": True,
            "loaded": model_loaded,
            "model_size": getattr(self._config, "MODEL_SIZE", "unknown"),
            "device": getattr(self._config, "DEVICE", "unknown"),
            "compute_type": getattr(self._config, "COMPUTE_TYPE", "unknown"),
            "vad_enabled": vad_enabled,
            "sample_rate": getattr(self._config, "SAMPLE_RATE", 16000),
            "channels": getattr(self._config, "CHANNELS", 1),
            "metrics": metrics,
            "last_error": None,
        }

    def llm(self) -> dict:
        settings = get_lm_studio_settings(self._config)
        provider = LMStudioProvider(settings)
        model_configured = bool(settings.model.strip())
        base_url_configured = bool(settings.base_url.strip())
        configured = model_configured and base_url_configured

        if not model_configured:
            health = {
                "status": "unhealthy",
                "reachable": False,
                "last_error": "LM_STUDIO_MODEL is required",
            }
        elif not base_url_configured:
            health = {
                "status": "unhealthy",
                "reachable": False,
                "last_error": "LM_STUDIO_BASE_URL is required",
            }
        else:
            health = provider.check_health()

        return {
            "status": health["status"],
            "provider": "lmstudio",
            "configured": configured,
            "reachable": bool(health.get("reachable", False)),
            "model_configured": model_configured,
            "model": settings.model.strip() if model_configured else "",
            "metrics": {},
            "last_error": health.get("last_error"),
        }

    def tts(self) -> dict:
        settings = get_supertonic_settings(self._config)
        provider = SupertonicProvider(settings)

        try:
            health = provider.check_health()
        except Exception as exc:
            health = {
                "status": "unhealthy",
                "available": False,
                "last_error": safe_error_message(exc),
            }

        configured = settings.provider.strip().lower() == "supertonic"
        return {
            "status": health["status"],
            "provider": settings.provider.strip() or "unknown",
            "configured": configured,
            "available": bool(health.get("available", False)),
            "voice": settings.voice,
            "lang": settings.lang,
            "metrics": {},
            "last_error": health.get("last_error"),
        }

    def aggregate(self) -> dict:
        backend = self.backend()
        stt = self.stt()
        llm = self.llm()
        tts = self.tts()

        return {
            "status": aggregate_status(
                backend["status"],
                stt["status"],
                llm["status"],
                tts["status"],
            ),
            "backend": backend,
            "stt": stt,
            "llm": llm,
            "tts": tts,
        }

    def _metrics_snapshot(self, vad_enabled: bool) -> dict:
        if self._stt_metrics is not None:
            return self._stt_metrics.snapshot()
        return STTMetrics.from_config(self._config, vad_enabled=vad_enabled).snapshot()
