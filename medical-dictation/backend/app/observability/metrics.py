"""Process-local lightweight metrics."""

from dataclasses import dataclass


@dataclass
class STTMetrics:
    model_size: str
    device: str
    compute_type: str
    vad_enabled: bool
    sample_rate: int
    channels: int
    chunks_received: int = 0
    silence_chunks_skipped: int = 0
    transcriptions_count: int = 0
    empty_transcription_count: int = 0
    last_audio_duration_seconds: float = 0.0
    last_processing_time_ms: float = 0.0
    last_real_time_factor: float = 0.0
    last_flush_reason: str = "unknown"
    total_processing_time_ms: float = 0.0
    total_real_time_factor: float = 0.0

    @classmethod
    def from_config(cls, config, *, vad_enabled: bool) -> "STTMetrics":
        return cls(
            model_size=getattr(config, "MODEL_SIZE", "unknown"),
            device=getattr(config, "DEVICE", "unknown"),
            compute_type=getattr(config, "COMPUTE_TYPE", "unknown"),
            vad_enabled=vad_enabled,
            sample_rate=getattr(config, "SAMPLE_RATE", 16000),
            channels=getattr(config, "CHANNELS", 1),
        )

    def record_chunk(self) -> None:
        self.chunks_received += 1

    def record_silence_skipped(self) -> None:
        self.silence_chunks_skipped += 1

    def record_empty_transcription(self) -> None:
        self.empty_transcription_count += 1

    def record_transcription(
        self,
        *,
        audio_duration_seconds: float,
        processing_time_ms: float,
        flush_reason: str,
    ) -> None:
        real_time_factor = 0.0
        if audio_duration_seconds > 0:
            real_time_factor = processing_time_ms / (audio_duration_seconds * 1000)

        self.transcriptions_count += 1
        self.last_audio_duration_seconds = round(audio_duration_seconds, 3)
        self.last_processing_time_ms = round(processing_time_ms, 3)
        self.last_real_time_factor = round(real_time_factor, 3)
        self.last_flush_reason = flush_reason
        self.total_processing_time_ms += processing_time_ms
        self.total_real_time_factor += real_time_factor

    def snapshot(self) -> dict:
        avg_processing = 0.0
        avg_rtf = 0.0
        if self.transcriptions_count > 0:
            avg_processing = self.total_processing_time_ms / self.transcriptions_count
            avg_rtf = self.total_real_time_factor / self.transcriptions_count

        silence_percent = (self.silence_chunks_skipped / max(self.chunks_received, 1)) * 100

        return {
            "model_size": self.model_size,
            "device": self.device,
            "compute_type": self.compute_type,
            "vad_enabled": self.vad_enabled,
            "sample_rate": self.sample_rate,
            "channels": self.channels,
            "chunks_received": self.chunks_received,
            "silence_chunks_skipped": self.silence_chunks_skipped,
            "silence_skipped_percent": round(silence_percent, 2),
            "transcriptions_count": self.transcriptions_count,
            "empty_transcription_count": self.empty_transcription_count,
            "last_audio_duration_seconds": self.last_audio_duration_seconds,
            "last_processing_time_ms": self.last_processing_time_ms,
            "last_real_time_factor": self.last_real_time_factor,
            "last_flush_reason": self.last_flush_reason,
            "average_processing_time_ms": round(avg_processing, 3),
            "average_real_time_factor": round(avg_rtf, 3),
        }
