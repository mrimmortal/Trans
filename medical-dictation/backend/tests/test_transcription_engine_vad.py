import unittest
from types import SimpleNamespace

import numpy as np

from app.services.transcription_engine import TranscriptionEngine


class FakeVadModel:
    def __init__(self):
        self.frame_lengths = []

    def __call__(self, audio_tensor, sample_rate):
        frame_length = audio_tensor.shape[-1]
        self.frame_lengths.append(frame_length)
        if frame_length != 512:
            raise ValueError(f"Provided number of samples is {frame_length}")
        return SimpleNamespace(item=lambda: 0.75)


class SileroVadFrameTests(unittest.TestCase):
    def test_detect_speech_scores_large_chunks_in_silero_frame_sizes(self):
        engine = TranscriptionEngine.__new__(TranscriptionEngine)
        engine.config = SimpleNamespace(
            SAMPLE_RATE=16000,
            SILERO_VAD_THRESHOLD=0.5,
            SILERO_MIN_SPEECH_MS=200,
            SILERO_MIN_SILENCE_MS=300,
            SILERO_SPEECH_PAD_MS=200,
            SILENCE_RMS_THRESHOLD=0.003,
        )
        engine.vad_model = FakeVadModel()
        engine.get_speech_timestamps = lambda *args, **kwargs: []

        audio = np.ones(4096, dtype=np.int16).tobytes()

        result = engine.detect_speech(audio)

        self.assertTrue(result["has_speech"])
        self.assertEqual(result["speech_prob"], 0.75)
        self.assertEqual(engine.vad_model.frame_lengths, [512] * 8)


if __name__ == "__main__":
    unittest.main()
