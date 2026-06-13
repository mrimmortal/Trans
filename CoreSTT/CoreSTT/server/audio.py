import math
import wave
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np


SERVER_SAMPLE_RATE = 16000
INT16_MAX_ABS_VALUE = 32768.0


@dataclass(frozen=True)
class AudioData:
    samples: Any
    sample_rate: int


def read_wav_float32(path: Path):
    with wave.open(str(path), "rb") as wav:
        channels = wav.getnchannels()
        sample_width = wav.getsampwidth()
        sample_rate = wav.getframerate()
        frames = wav.readframes(wav.getnframes())

    if sample_width != 2:
        raise ValueError(f"{path} must be 16-bit PCM WAV")
    samples = np.frombuffer(frames, dtype=np.int16)
    if channels > 1:
        usable = len(samples) - (len(samples) % channels)
        samples = samples[:usable].reshape(-1, channels).mean(axis=1).astype(np.int16)
    samples = resample_int16(samples, sample_rate, SERVER_SAMPLE_RATE)
    return AudioData(samples=samples.astype(np.float32) / INT16_MAX_ABS_VALUE, sample_rate=SERVER_SAMPLE_RATE)


def resample_int16(samples, source_rate, target_rate):
    samples = np.asarray(samples, dtype=np.int16)
    if source_rate == target_rate or samples.size == 0:
        return samples.copy()

    try:
        from scipy.signal import resample_poly

        divisor = math.gcd(int(source_rate), int(target_rate))
        up = int(target_rate // divisor)
        down = int(source_rate // divisor)
        resampled = resample_poly(samples.astype(np.float32), up, down)
    except Exception:
        duration = samples.size / float(source_rate)
        target_size = max(1, int(round(duration * target_rate)))
        source_positions = np.linspace(0.0, 1.0, num=samples.size, endpoint=False)
        target_positions = np.linspace(0.0, 1.0, num=target_size, endpoint=False)
        resampled = np.interp(target_positions, source_positions, samples.astype(np.float32))

    return np.clip(np.rint(resampled), -32768, 32767).astype(np.int16)


def effective_device(device):
    if str(device).lower() != "cuda":
        return device
    try:
        import torch

        return "cuda" if torch.cuda.is_available() else "cpu"
    except Exception:
        return "cpu"
