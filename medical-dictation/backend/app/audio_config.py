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
    # We accumulate audio and transcribe in chunks.
    # Too small = choppy, cuts words mid-syllable.
    # Too large = high latency, doctor waits too long.
    # 2 seconds is the sweet spot for medical dictation.
    CHUNK_DURATION_SECONDS: float = 2.0
    CHUNK_SIZE_BYTES: int = int(16000 * 2 * 2.0)
    # = 16000 * 2 * 2.0 = 64000 bytes per chunk

    # Overlap: Keep the last 0.5s of previous chunk and prepend to next chunk.
    # Prevents words at chunk boundaries from being cut in half.
    # Example: "cardio-" | "-vascular" becomes "cardiovascular" with overlap.
    OVERLAP_DURATION_SECONDS: float = 0.5
    OVERLAP_SIZE_BYTES: int = int(16000 * 2 * 0.5)

    # ─── SILENCE / VOICE ACTIVITY DETECTION ───
    SILENCE_RMS_THRESHOLD: float = 0.003  # Below this = silence (TUNED: was 0.008)
    MIN_AUDIO_DURATION_SECONDS: float = 0.5  # TUNED: was 0.3
    MIN_AUDIO_SAMPLES: int = int(16000 * 0.5)  # Recalculated
    MAX_SILENCE_DURATION_SECONDS: float = 3.0
    MAX_SILENCE_CHUNKS: int = int(3.0 / 2.0)

    # ─── WHISPER MODEL SETTINGS ───
    MODEL_SIZE: str = os.getenv("MODEL_SIZE", "base.en")
    DEVICE: str = os.getenv("DEVICE", "cpu")
    COMPUTE_TYPE: str = os.getenv("COMPUTE_TYPE", "int8")
    BEAM_SIZE: int = 5
    TEMPERATURE: tuple = (0.0,)  # CRITICAL: Single temp for accuracy (was 6 temps)
    BEST_OF: int = 1  # TUNED: was 5 (only needed with multiple temps)
    PATIENCE: float = 1.0  # TUNED: was 1.2
    COMPRESSION_RATIO_THRESHOLD: float = 2.2  # TUNED: was 2.4
    LOG_PROB_THRESHOLD: float = -0.7  # TUNED: was -1.0
    NO_SPEECH_THRESHOLD: float = 0.75  # TUNED: was 0.6

    # ─── VAD SETTINGS ───
    VAD_FILTER: bool = True
    VAD_PARAMETERS: dict = {
        "threshold": 0.65,  # TUNED: was 0.5
        "min_speech_duration_ms": 350,  # TUNED: was 250
        "max_speech_duration_s": 30,
        "min_silence_duration_ms": 700,  # TUNED: was 500
        "speech_pad_ms": 100,  # TUNED: was 200
    }

    # ─── MEDICAL CONTEXT PROMPT ───
    # Written as a fake "previous transcription" to prime Whisper for medical terms.
    # Must be under 224 tokens.
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
    # Whisper hallucinates these phrases on silence/short audio. Filter them.
    HALLUCINATION_PHRASES: list = [
        "thank you", "thanks for watching", "subscribe",
        "like and subscribe", "thank you for watching", "the end",
        "bye", "goodbye", "see you next time", "please subscribe",
        "you", "...", "MobyDick", "www.", ".com", "copyright",
        "all rights reserved", "subtitles by", "captions by", "translated by",
        # Additional common hallucinations
        ".", "the", "a", "um", "uh", "hmm", "huh",
        "music", "applause", "laughter", "http", ".org",
    ]


# Global config instance
config = AudioConfig()