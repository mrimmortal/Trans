"""Audio configuration and constants"""

import os


class AudioConfig:
    """Audio pipeline configuration tuned for real-time medical dictation."""

    # ─── AUDIO FORMAT (What the frontend MUST send) ───
    SAMPLE_RATE: int = 16000            # Whisper requires 16kHz
    CHANNELS: int = 1                    # Mono audio only
    SAMPLE_WIDTH: int = 2                # 16-bit PCM = 2 bytes per sample
    DTYPE: str = "int16"                 # numpy dtype for incoming audio
    HOST: str = os.getenv("HOST", "0.0.0.0")  # Server host address
    PORT: int = int(os.getenv("PORT", "8000"))  # Server port

    # ─── BUFFERING STRATEGY ───
    # Dynamic buffering based on speech detection (VAD-driven)
    # These are now MAXIMUM thresholds, actual transcription happens on pauses
    MIN_CHUNK_DURATION_SECONDS: float = 1.0  # Minimum before transcribing
    MAX_CHUNK_DURATION_SECONDS: float = 10.0  # Force transcription if too long
    
    MIN_CHUNK_SIZE_BYTES: int = int(16000 * 2 * 1.0)  # 32,000 bytes (1 second)
    MAX_CHUNK_SIZE_BYTES: int = int(16000 * 2 * 10.0)  # 320,000 bytes (10 seconds)

    # Overlap: Keep the last 0.5s of previous chunk and prepend to next chunk.
    # Prevents words at chunk boundaries from being cut in half.
    OVERLAP_DURATION_SECONDS: float = 0.5
    OVERLAP_SIZE_BYTES: int = int(16000 * 2 * 0.5)  # 16,000 bytes

    # ─── SILENCE / VOICE ACTIVITY DETECTION ───
    SILENCE_RMS_THRESHOLD: float = 0.003  # Below this = silence
    MIN_AUDIO_DURATION_SECONDS: float = 0.5
    MIN_AUDIO_SAMPLES: int = int(16000 * 0.5)
    
    # Pause-based transcription trigger
    SILENCE_TIMEOUT_SECONDS: float = 1.5  # Transcribe after 1.5s of silence
    
    # Silero VAD settings (real-time speech detection)
    SILERO_VAD_THRESHOLD: float = 0.5  # 0.0-1.0, lower = more sensitive
    SILERO_MIN_SPEECH_MS: int = 200  # Minimum speech duration (catch short words)
    SILERO_MIN_SILENCE_MS: int = 300  # Minimum silence to split segments
    SILERO_SPEECH_PAD_MS: int = 200  # Padding around speech segments

    # ─── WHISPER MODEL SETTINGS ───
    MODEL_SIZE: str = os.getenv("MODEL_SIZE", "base.en")
    DEVICE: str = os.getenv("DEVICE", "cpu")
    COMPUTE_TYPE: str = os.getenv("COMPUTE_TYPE", "int8")
    BEAM_SIZE: int = 5
    TEMPERATURE: tuple = (0.0,)  # Single temp for accuracy
    BEST_OF: int = 1
    PATIENCE: float = 1.0
    COMPRESSION_RATIO_THRESHOLD: float = 2.2
    LOG_PROB_THRESHOLD: float = -0.7
    NO_SPEECH_THRESHOLD: float = 0.75

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
        "Patient presents with hypertension, type 2 diabetes mellitus, "
        "and hyperlipidemia. Current medications include Metformin 500mg "
        "twice daily, Lisinopril 10mg daily, and Atorvastatin 20mg at bedtime. "
        "Blood pressure is 130/85 mmHg. Heart rate 72 bpm. SpO2 98%. "
        "CBC shows WBC 7.2, hemoglobin 14.1, platelets 250. "
        "CMP within normal limits. HbA1c 7.2%. LDL 110 mg/dL. "
        "ECG shows normal sinus rhythm. No ST changes. "
        "Assessment: COPD exacerbation. CHF stable. DVT ruled out. "
        "Plan: Continue Aspirin 81mg, Omeprazole 20mg, Amlodipine 5mg. "
        "Prescribe Amoxicillin 500mg TID for 7 days. "
        "Follow up in 2 weeks. Refer to cardiology for echocardiogram. "
        "Ibuprofen 400mg PRN for pain. Gabapentin 300mg QHS for neuropathy."
    )

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