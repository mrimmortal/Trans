import unittest
from types import SimpleNamespace

import numpy as np

from app.services.stt.faster_whisper import FasterWhisperSTTProvider


class CapturingWhisperModel:
    def __init__(self):
        self.kwargs = None

    def transcribe(self, audio, **kwargs):
        self.kwargs = kwargs
        return [], SimpleNamespace(language="en", language_probability=1.0)


class FasterWhisperSTTAccentSupportTests(unittest.TestCase):
    def test_run_whisper_uses_configured_language_and_composed_prompt(self):
        model = CapturingWhisperModel()
        engine = FasterWhisperSTTProvider.__new__(FasterWhisperSTTProvider)
        engine.model = model
        engine.config = SimpleNamespace(
            TRANSCRIPTION_LANGUAGE="en",
            get_initial_prompt=lambda: "accent aware prompt",
            BEAM_SIZE=2,
            PATIENCE=1.0,
            BEST_OF=1,
            TEMPERATURE=(0.0,),
            COMPRESSION_RATIO_THRESHOLD=2.2,
            LOG_PROB_THRESHOLD=-0.7,
            NO_SPEECH_THRESHOLD=0.75,
            VAD_FILTER=True,
            VAD_PARAMETERS={},
            MIN_TRANSCRIPTION_CONFIDENCE=0.10,
            HALLUCINATION_MAX_NO_SPEECH_PROB=0.65,
        )

        engine._run_whisper(np.ones(16000, dtype=np.float32))

        self.assertEqual(model.kwargs["language"], "en")
        self.assertEqual(model.kwargs["initial_prompt"], "accent aware prompt")


if __name__ == "__main__":
    unittest.main()
