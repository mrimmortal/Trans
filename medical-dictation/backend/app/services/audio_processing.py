"""Audio conversion, validation, and preprocessing helpers."""

import logging
from typing import Optional

import numpy as np

try:
    import noisereduce as nr

    NOISEREDUCE_AVAILABLE = True
except ImportError:
    NOISEREDUCE_AVAILABLE = False
    logging.warning("noisereduce not installed - noise reduction disabled")

try:
    from scipy import signal

    SCIPY_AVAILABLE = True
except ImportError:
    SCIPY_AVAILABLE = False
    logging.warning("scipy not installed - high-pass filtering disabled")

logger = logging.getLogger(__name__)


def bytes_to_float32(audio_bytes: bytes) -> Optional[np.ndarray]:
    """Convert raw int16 PCM bytes to float32 audio in [-1.0, 1.0]."""
    try:
        audio_int16 = np.frombuffer(audio_bytes, dtype=np.int16)
        return audio_int16.astype(np.float32) / 32768.0

    except ValueError:
        try:
            truncated_bytes = audio_bytes[: (len(audio_bytes) // 2) * 2]
            audio_int16 = np.frombuffer(truncated_bytes, dtype=np.int16)
            audio_float32 = audio_int16.astype(np.float32) / 32768.0
            logger.warning(
                "Truncated audio from %s to %s bytes",
                len(audio_bytes),
                len(truncated_bytes),
            )
            return audio_float32
        except Exception as exc:
            logger.error("Failed to convert bytes to float32: %s", exc)
            return None


def validate_audio(audio: np.ndarray, config) -> dict:
    """Validate length, energy, and clipping for a float32 audio buffer."""
    if len(audio) < config.MIN_AUDIO_SAMPLES:
        return {
            "is_valid": False,
            "reason": f"Audio too short: {len(audio)} < {config.MIN_AUDIO_SAMPLES} samples",
            "rms": 0.0,
        }

    rms = np.sqrt(np.mean(audio**2))
    if rms < config.SILENCE_RMS_THRESHOLD:
        return {
            "is_valid": False,
            "reason": f"Audio is silence (RMS {rms:.6f} < {config.SILENCE_RMS_THRESHOLD})",
            "rms": rms,
        }

    clipping_ratio = np.sum(np.abs(audio) > 0.95) / len(audio)
    if clipping_ratio > 0.05:
        logger.warning(
            "Audio clipping detected: %.1f%% of samples exceed 0.95. "
            "Microphone may be distorting.",
            clipping_ratio * 100,
        )

    return {
        "is_valid": True,
        "reason": "OK",
        "rms": float(rms),
    }


def preprocess_audio(audio: np.ndarray, sample_rate: int) -> np.ndarray:
    """Apply DC offset removal, optional filtering/noise reduction, compression, and normalization."""
    audio = audio - np.mean(audio)

    if SCIPY_AVAILABLE:
        try:
            sos = signal.butter(4, 80, "hp", fs=sample_rate, output="sos")
            audio = signal.sosfilt(sos, audio)
        except Exception as exc:
            logger.warning("High-pass filter failed: %s", exc)

    if NOISEREDUCE_AVAILABLE:
        try:
            audio = nr.reduce_noise(
                y=audio,
                sr=sample_rate,
                stationary=True,
                prop_decrease=0.8,
            )
        except Exception as exc:
            logger.warning("Noise reduction failed: %s", exc)

    try:
        threshold = 0.3
        ratio = 2.0
        audio_abs = np.abs(audio)
        audio = np.where(
            audio_abs > threshold,
            np.sign(audio) * (threshold + (audio_abs - threshold) / ratio),
            audio,
        )
    except Exception as exc:
        logger.warning("Compression failed: %s", exc)

    peak = np.max(np.abs(audio))
    if peak > 0.1:
        audio = audio * (0.8 / peak)

    return audio.astype(np.float32)
