"""Audio configuration and constants"""

import os
from typing import Any


def parse_cors_origins(value: str | None) -> list[str]:
    """Parse comma-separated CORS origins from environment configuration."""
    if not value:
        return ["http://localhost:3000", "http://127.0.0.1:3000"]

    origins = [origin.strip().rstrip("/") for origin in value.split(",") if origin.strip()]
    return origins or ["http://localhost:3000", "http://127.0.0.1:3000"]


def env_float(name: str, default: float) -> float:
    """Read a float environment override with a safe fallback."""
    try:
        return float(os.getenv(name, str(default)))
    except ValueError:
        return default


def env_int(name: str, default: int) -> int:
    """Read an integer environment override with a safe fallback."""
    try:
        return int(os.getenv(name, str(default)))
    except ValueError:
        return default


def env_bool(name: str, default: bool) -> bool:
    """Read a boolean environment override with a safe fallback."""
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


TRANSCRIPTION_PROFILE_DEFAULT = "balanced_realtime"
BALANCED_PROFILE_DEFAULTS: dict[str, Any] = {
    "min_chunk_duration_seconds": 0.6,
    "max_chunk_duration_seconds": 6.0,
    "overlap_duration_seconds": 0.5,
    "silence_timeout_seconds": 0.7,
    "silero_vad_threshold": 0.5,
    "silero_min_speech_ms": 200,
    "silero_min_silence_ms": 300,
    "silero_speech_pad_ms": 200,
    "beam_size": 2,
    "model_size": None,
    "device": "cpu",
    "compute_type": "int8",
}
TRANSCRIPTION_PROFILES: dict[str, dict[str, Any]] = {
    "balanced": BALANCED_PROFILE_DEFAULTS,
    "balanced_realtime": BALANCED_PROFILE_DEFAULTS,
    "low_latency": {
        **BALANCED_PROFILE_DEFAULTS,
        "min_chunk_duration_seconds": 0.5,
        "max_chunk_duration_seconds": 5.0,
        "overlap_duration_seconds": 0.4,
        "silence_timeout_seconds": 0.5,
        "beam_size": 1,
    },
    "high_accuracy": {
        **BALANCED_PROFILE_DEFAULTS,
        "max_chunk_duration_seconds": 8.0,
        "overlap_duration_seconds": 0.7,
        "silence_timeout_seconds": 0.9,
        "beam_size": 5,
    },
    "pi_cpu": {
        **BALANCED_PROFILE_DEFAULTS,
        "model_size": "tiny",
        "device": "cpu",
        "compute_type": "int8",
        "min_chunk_duration_seconds": 0.5,
        "max_chunk_duration_seconds": 5.0,
        "overlap_duration_seconds": 0.4,
        "silence_timeout_seconds": 0.5,
        "beam_size": 1,
    },
    "gpu": {
        **BALANCED_PROFILE_DEFAULTS,
        "model_size": "small",
        "device": "cuda",
        "compute_type": "float16",
    },
}


def resolve_transcription_profile(value: str | None) -> str:
    """Return a supported transcription profile, falling back to balanced behavior."""
    profile = (value or TRANSCRIPTION_PROFILE_DEFAULT).strip().lower()
    if profile in TRANSCRIPTION_PROFILES:
        return profile
    return TRANSCRIPTION_PROFILE_DEFAULT


def get_transcription_profile_defaults(profile: str | None) -> dict[str, Any]:
    """Return profile defaults without exposing mutable shared state."""
    resolved_profile = resolve_transcription_profile(profile)
    return dict(TRANSCRIPTION_PROFILES[resolved_profile])


def env_temperature(name: str, default: float) -> tuple[float, ...]:
    """Read a Whisper temperature override as the tuple Faster-Whisper expects."""
    value = os.getenv(name)
    if value is None:
        return (default,)
    try:
        temperatures = tuple(
            float(part.strip())
            for part in value.split(",")
            if part.strip()
        )
    except ValueError:
        return (default,)
    return temperatures or (default,)


class AudioConfig:
    """Audio pipeline configuration tuned for real-time transcription."""

    # ─── AUDIO FORMAT (What the frontend MUST send) ───
    SAMPLE_RATE: int = 16000            # Whisper requires 16kHz
    CHANNELS: int = 1                    # Mono audio only
    SAMPLE_WIDTH: int = 2                # 16-bit PCM = 2 bytes per sample
    DTYPE: str = "int16"                 # numpy dtype for incoming audio
    HOST: str = os.getenv("HOST", "0.0.0.0")  # Server host address
    PORT: int = int(os.getenv("PORT", "8000"))  # Server port
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    CORS_ORIGINS: list[str] = parse_cors_origins(os.getenv("CORS_ORIGINS"))
    DEFAULT_TRANSCRIPTION_DOMAIN: str = os.getenv("DEFAULT_TRANSCRIPTION_DOMAIN", "general")
    LM_STUDIO_BASE_URL: str = os.getenv("LM_STUDIO_BASE_URL", "")
    LM_STUDIO_MODEL: str = os.getenv("LM_STUDIO_MODEL", "")
    LM_STUDIO_TIMEOUT_SECONDS: float = env_float("LM_STUDIO_TIMEOUT_SECONDS", 30.0)
    TTS_PROVIDER: str = os.getenv("TTS_PROVIDER", "supertonic")
    SUPERTONIC_VOICE: str = os.getenv("SUPERTONIC_VOICE", "M1")
    SUPERTONIC_LANG: str = os.getenv("SUPERTONIC_LANG", "en")
    TTS_OUTPUT_DIR: str = os.getenv("TTS_OUTPUT_DIR", "")

    # ─── BUFFERING STRATEGY ───
    TRANSCRIPTION_PROFILE: str = resolve_transcription_profile(os.getenv("TRANSCRIPTION_PROFILE"))
    TRANSCRIPTION_PROFILE_DEFAULTS: dict[str, Any] = get_transcription_profile_defaults(
        TRANSCRIPTION_PROFILE
    )

    # Dynamic buffering based on speech detection (VAD-driven)
    # These are now MAXIMUM thresholds, actual transcription happens on pauses
    MIN_CHUNK_DURATION_SECONDS: float = env_float(
        "MIN_CHUNK_DURATION_SECONDS",
        TRANSCRIPTION_PROFILE_DEFAULTS["min_chunk_duration_seconds"],
    )
    MAX_CHUNK_DURATION_SECONDS: float = env_float(
        "MAX_CHUNK_DURATION_SECONDS",
        TRANSCRIPTION_PROFILE_DEFAULTS["max_chunk_duration_seconds"],
    )
    
    MIN_CHUNK_SIZE_BYTES: int = int(SAMPLE_RATE * SAMPLE_WIDTH * MIN_CHUNK_DURATION_SECONDS)
    MAX_CHUNK_SIZE_BYTES: int = int(SAMPLE_RATE * SAMPLE_WIDTH * MAX_CHUNK_DURATION_SECONDS)

    # Overlap: Keep the last 0.5s of previous chunk and prepend to next chunk.
    # Prevents words at chunk boundaries from being cut in half.
    OVERLAP_DURATION_SECONDS: float = env_float(
        "OVERLAP_DURATION_SECONDS",
        TRANSCRIPTION_PROFILE_DEFAULTS["overlap_duration_seconds"],
    )
    OVERLAP_SIZE_BYTES: int = int(SAMPLE_RATE * SAMPLE_WIDTH * OVERLAP_DURATION_SECONDS)

    # ─── SILENCE / VOICE ACTIVITY DETECTION ───
    SILENCE_RMS_THRESHOLD: float = 0.003  # Below this = silence
    MIN_AUDIO_DURATION_SECONDS: float = 0.5
    MIN_AUDIO_SAMPLES: int = int(16000 * 0.5)
    
    # Pause-based transcription trigger
    SILENCE_TIMEOUT_SECONDS: float = env_float(
        "SILENCE_TIMEOUT_SECONDS",
        TRANSCRIPTION_PROFILE_DEFAULTS["silence_timeout_seconds"],
    )
    
    # Silero VAD settings (real-time speech detection)
    SILERO_VAD_THRESHOLD: float = env_float(
        "SILERO_VAD_THRESHOLD",
        TRANSCRIPTION_PROFILE_DEFAULTS["silero_vad_threshold"],
    )
    SILERO_REQUIRE_SEGMENT: bool = os.getenv("SILERO_REQUIRE_SEGMENT", "false").lower() == "true"
    SILERO_MIN_SPEECH_MS: int = env_int(
        "SILERO_MIN_SPEECH_MS",
        TRANSCRIPTION_PROFILE_DEFAULTS["silero_min_speech_ms"],
    )
    SILERO_MIN_SILENCE_MS: int = env_int(
        "SILERO_MIN_SILENCE_MS",
        TRANSCRIPTION_PROFILE_DEFAULTS["silero_min_silence_ms"],
    )
    SILERO_SPEECH_PAD_MS: int = env_int(
        "SILERO_SPEECH_PAD_MS",
        TRANSCRIPTION_PROFILE_DEFAULTS["silero_speech_pad_ms"],
    )

    # ─── WHISPER MODEL SETTINGS ───
    ACCENT_SUPPORT_ENABLED: bool = env_bool("ACCENT_SUPPORT_ENABLED", True)
    DEFAULT_ACCENT_MODEL_SIZE: str = os.getenv("DEFAULT_ACCENT_MODEL_SIZE", "base")
    DEFAULT_STANDARD_MODEL_SIZE: str = os.getenv("DEFAULT_STANDARD_MODEL_SIZE", "base.en")
    PROFILE_MODEL_SIZE: str | None = TRANSCRIPTION_PROFILE_DEFAULTS["model_size"]
    MODEL_SIZE: str = os.getenv("MODEL_SIZE") or PROFILE_MODEL_SIZE or (
        DEFAULT_ACCENT_MODEL_SIZE if ACCENT_SUPPORT_ENABLED else DEFAULT_STANDARD_MODEL_SIZE
    )
    TRANSCRIPTION_LANGUAGE: str = os.getenv("TRANSCRIPTION_LANGUAGE", "en")
    DEVICE: str = os.getenv("DEVICE", TRANSCRIPTION_PROFILE_DEFAULTS["device"])
    COMPUTE_TYPE: str = os.getenv("COMPUTE_TYPE", TRANSCRIPTION_PROFILE_DEFAULTS["compute_type"])
    BEAM_SIZE: int = env_int("BEAM_SIZE", TRANSCRIPTION_PROFILE_DEFAULTS["beam_size"])
    TEMPERATURE: tuple = env_temperature("TEMPERATURE", 0.0)
    BEST_OF: int = 1
    PATIENCE: float = 1.0
    COMPRESSION_RATIO_THRESHOLD: float = env_float("COMPRESSION_RATIO_THRESHOLD", 2.2)
    LOG_PROB_THRESHOLD: float = env_float("LOG_PROB_THRESHOLD", -0.7)
    NO_SPEECH_THRESHOLD: float = env_float("NO_SPEECH_THRESHOLD", 0.75)
    MIN_TRANSCRIPTION_CONFIDENCE: float = env_float("MIN_TRANSCRIPTION_CONFIDENCE", 0.10)
    HALLUCINATION_MAX_NO_SPEECH_PROB: float = env_float("HALLUCINATION_MAX_NO_SPEECH_PROB", 0.65)

    # ─── VAD SETTINGS (for Whisper internal VAD) ───
    VAD_FILTER: bool = env_bool("VAD_FILTER", True)
    VAD_PARAMETERS: dict = {
        "threshold": SILERO_VAD_THRESHOLD,
        "min_speech_duration_ms": SILERO_MIN_SPEECH_MS,
        "max_speech_duration_s": 30,
        "min_silence_duration_ms": SILERO_MIN_SILENCE_MS,
        "speech_pad_ms": SILERO_SPEECH_PAD_MS,
    }

    # ─── TRANSCRIPTION CONTEXT PROMPT ───
    TRANSCRIPTION_CONTEXT_PROMPT: str = (
        "Transcribe only the words spoken by the speaker. Do not invent names, numbers, "
        "tasks, decisions, dates, plans, or follow-up details. Prefer silence over guessing "
        "when audio is unclear. Preserve dictated wording, punctuation commands, and units "
        "exactly as spoken."
    )

    ACCENT_CONTEXT_PROMPT: str = (
        "This is English dictation. The speaker may use multiple English accents, "
        "including Indian, American, British, Australian, African, Middle Eastern, or other "
        "regional English pronunciations. Preserve the intended English words."
    )

    @classmethod
    def get_initial_prompt(cls) -> str:
        """Return Whisper prompt context with optional accent guidance."""
        if cls.ACCENT_SUPPORT_ENABLED:
            return f"{cls.ACCENT_CONTEXT_PROMPT} {cls.TRANSCRIPTION_CONTEXT_PROMPT}"
        return cls.TRANSCRIPTION_CONTEXT_PROMPT

    def safe_stt_settings(self) -> dict:
        """Return safe STT configuration metadata for diagnostics and config APIs."""
        return {
            "transcription_profile": self.TRANSCRIPTION_PROFILE,
            "model_size": self.MODEL_SIZE,
            "device": self.DEVICE,
            "compute_type": self.COMPUTE_TYPE,
            "language": self.TRANSCRIPTION_LANGUAGE,
            "sample_rate": self.SAMPLE_RATE,
            "channels": self.CHANNELS,
            "sample_width": self.SAMPLE_WIDTH,
            "min_chunk_duration_seconds": self.MIN_CHUNK_DURATION_SECONDS,
            "max_chunk_duration_seconds": self.MAX_CHUNK_DURATION_SECONDS,
            "overlap_duration_seconds": self.OVERLAP_DURATION_SECONDS,
            "silence_timeout_seconds": self.SILENCE_TIMEOUT_SECONDS,
            "beam_size": self.BEAM_SIZE,
            "temperature": list(self.TEMPERATURE),
            "compression_ratio_threshold": self.COMPRESSION_RATIO_THRESHOLD,
            "log_prob_threshold": self.LOG_PROB_THRESHOLD,
            "no_speech_threshold": self.NO_SPEECH_THRESHOLD,
            "vad_filter": self.VAD_FILTER,
            "vad_parameters": dict(self.VAD_PARAMETERS),
            "hallucination_silence_threshold_enabled": False,
        }

    # ─── HALLUCINATION FILTER ───
    # FIXED: Removed common words like "the", "a", "um", "uh" - these are legitimate!
    HALLUCINATION_PHRASES: list = [
        "thank you", "thanks for watching", "subscribe",
        "like and subscribe", "thank you for watching", "the end",
        "bye", "goodbye", "see you next time", "please subscribe",
        "MobyDick", "www.", ".com", "copyright",
        "all rights reserved", "subtitles by", "captions by", "translated by",
        "music", "applause", "laughter", "http", ".org",
    ]


# Global config instance
config = AudioConfig()
