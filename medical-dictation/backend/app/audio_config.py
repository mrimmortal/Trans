"""Audio configuration and constants"""

import os


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


class AudioConfig:
    """Audio pipeline configuration tuned for real-time medical dictation."""

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

    # ─── BUFFERING STRATEGY ───
    TRANSCRIPTION_PROFILE: str = os.getenv("TRANSCRIPTION_PROFILE", "balanced_realtime")

    # Dynamic buffering based on speech detection (VAD-driven)
    # These are now MAXIMUM thresholds, actual transcription happens on pauses
    MIN_CHUNK_DURATION_SECONDS: float = env_float("MIN_CHUNK_DURATION_SECONDS", 0.6)
    MAX_CHUNK_DURATION_SECONDS: float = env_float("MAX_CHUNK_DURATION_SECONDS", 6.0)
    
    MIN_CHUNK_SIZE_BYTES: int = int(SAMPLE_RATE * SAMPLE_WIDTH * MIN_CHUNK_DURATION_SECONDS)
    MAX_CHUNK_SIZE_BYTES: int = int(SAMPLE_RATE * SAMPLE_WIDTH * MAX_CHUNK_DURATION_SECONDS)

    # Overlap: Keep the last 0.5s of previous chunk and prepend to next chunk.
    # Prevents words at chunk boundaries from being cut in half.
    OVERLAP_DURATION_SECONDS: float = 0.5
    OVERLAP_SIZE_BYTES: int = int(16000 * 2 * 0.5)  # 16,000 bytes

    # ─── SILENCE / VOICE ACTIVITY DETECTION ───
    SILENCE_RMS_THRESHOLD: float = 0.003  # Below this = silence
    MIN_AUDIO_DURATION_SECONDS: float = 0.5
    MIN_AUDIO_SAMPLES: int = int(16000 * 0.5)
    
    # Pause-based transcription trigger
    SILENCE_TIMEOUT_SECONDS: float = env_float("SILENCE_TIMEOUT_SECONDS", 0.7)
    
    # Silero VAD settings (real-time speech detection)
    SILERO_VAD_THRESHOLD: float = 0.5  # 0.0-1.0, lower = more sensitive
    SILERO_REQUIRE_SEGMENT: bool = os.getenv("SILERO_REQUIRE_SEGMENT", "false").lower() == "true"
    SILERO_MIN_SPEECH_MS: int = 200  # Minimum speech duration (catch short words)
    SILERO_MIN_SILENCE_MS: int = 300  # Minimum silence to split segments
    SILERO_SPEECH_PAD_MS: int = 200  # Padding around speech segments

    # ─── WHISPER MODEL SETTINGS ───
    ACCENT_SUPPORT_ENABLED: bool = env_bool("ACCENT_SUPPORT_ENABLED", True)
    DEFAULT_ACCENT_MODEL_SIZE: str = os.getenv("DEFAULT_ACCENT_MODEL_SIZE", "base")
    DEFAULT_STANDARD_MODEL_SIZE: str = os.getenv("DEFAULT_STANDARD_MODEL_SIZE", "base.en")
    MODEL_SIZE: str = os.getenv(
        "MODEL_SIZE",
        DEFAULT_ACCENT_MODEL_SIZE if ACCENT_SUPPORT_ENABLED else DEFAULT_STANDARD_MODEL_SIZE,
    )
    TRANSCRIPTION_LANGUAGE: str = os.getenv("TRANSCRIPTION_LANGUAGE", "en")
    DEVICE: str = os.getenv("DEVICE", "cpu")
    COMPUTE_TYPE: str = os.getenv("COMPUTE_TYPE", "int8")
    BEAM_SIZE: int = env_int("BEAM_SIZE", 2)
    TEMPERATURE: tuple = (0.0,)  # Single temp for accuracy
    BEST_OF: int = 1
    PATIENCE: float = 1.0
    COMPRESSION_RATIO_THRESHOLD: float = 2.2
    LOG_PROB_THRESHOLD: float = -0.7
    NO_SPEECH_THRESHOLD: float = 0.75
    MIN_TRANSCRIPTION_CONFIDENCE: float = env_float("MIN_TRANSCRIPTION_CONFIDENCE", 0.10)
    HALLUCINATION_MAX_NO_SPEECH_PROB: float = env_float("HALLUCINATION_MAX_NO_SPEECH_PROB", 0.65)

    # ─── VAD SETTINGS (for Whisper internal VAD) ───
    VAD_FILTER: bool = True
    VAD_PARAMETERS: dict = {
        "threshold": 0.5,  # FIXED: Reduced from 0.65 (less aggressive)
        "min_speech_duration_ms": 200,  # FIXED: Reduced from 350 (catch short words)
        "max_speech_duration_s": 30,
        "min_silence_duration_ms": 300,  # FIXED: Reduced from 700 (natural pauses)
        "speech_pad_ms": 200,  # FIXED: Increased from 100 (more context)
    }

    # ─── MEDICAL CONTEXT PROMPT ───
    MEDICAL_CONTEXT_PROMPT: str = (
        "Transcribe only the words spoken by the clinician. Do not invent symptoms, "
        "diagnoses, medications, doses, lab results, vitals, plans, or follow-up details. "
        "Prefer silence over guessing when audio is unclear. Preserve medical terminology, "
        "abbreviations, punctuation commands, and clinical units exactly as dictated."
    )

    ACCENT_CONTEXT_PROMPT: str = (
        "This is English medical dictation. The speaker may use multiple English accents, "
        "including Indian, American, British, Australian, African, Middle Eastern, or other "
        "regional English pronunciations. Preserve the intended English medical terms."
    )

    @classmethod
    def get_initial_prompt(cls) -> str:
        """Return Whisper prompt context with optional accent guidance."""
        if cls.ACCENT_SUPPORT_ENABLED:
            return f"{cls.ACCENT_CONTEXT_PROMPT} {cls.MEDICAL_CONTEXT_PROMPT}"
        return cls.MEDICAL_CONTEXT_PROMPT

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
