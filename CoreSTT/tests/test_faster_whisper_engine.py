import unittest
from types import SimpleNamespace
from unittest.mock import patch

import numpy as np

from CoreSTT.transcription_engines.base import TranscriptionEngineConfig
from CoreSTT.transcription_engines.faster_whisper_engine import FasterWhisperEngine


class FakeFasterWhisperModel:
    def __init__(self):
        self.kwargs = None

    def transcribe(self, _audio, **kwargs):
        self.kwargs = kwargs
        return [SimpleNamespace(text=" hello")], SimpleNamespace(
            language="en",
            language_probability=1.0,
        )


class FasterWhisperEngineTest(unittest.TestCase):
    def make_engine(self, engine_options=None, initial_prompt="Domain prompt."):
        engine = FasterWhisperEngine.__new__(FasterWhisperEngine)
        engine.config = TranscriptionEngineConfig(
            model="tiny.en",
            initial_prompt=initial_prompt,
            engine_options=engine_options,
        )
        engine.model = FakeFasterWhisperModel()
        return engine

    def test_passes_hotword_list_as_transcribe_hotwords(self):
        engine = self.make_engine({"hotwords": ["hypertension", "metformin"]})

        result = engine.transcribe(np.array([0.0], dtype=np.float32), language="en", use_prompt=True)

        self.assertEqual(result.text, "hello")
        self.assertEqual(engine.model.kwargs["initial_prompt"], "Domain prompt.")
        self.assertEqual(engine.model.kwargs["hotwords"], "hypertension metformin")

    def test_passes_hotword_string_as_transcribe_hotwords(self):
        engine = self.make_engine({"hotwords": "dyspnea hemoglobin A1c"})

        engine.transcribe(np.array([0.0], dtype=np.float32), language="en", use_prompt=True)

        self.assertEqual(engine.model.kwargs["hotwords"], "dyspnea hemoglobin A1c")

    def test_omits_empty_hotwords(self):
        engine = self.make_engine({"hotwords": []})

        engine.transcribe(np.array([0.0], dtype=np.float32), language="en", use_prompt=True)

        self.assertNotIn("hotwords", engine.model.kwargs)

    def test_model_construction_passes_thread_and_worker_controls(self):
        class FakeWhisperModule:
            model_kwargs = None

            class WhisperModel:
                def __init__(self, **kwargs):
                    FakeWhisperModule.model_kwargs = kwargs

        class FakeBatchedInferencePipeline:
            def __init__(self, model):
                self.model = model

        config = TranscriptionEngineConfig(
            model="tiny.en",
            device="cpu",
            compute_type="int8",
            cpu_threads=4,
            num_workers=2,
            batch_size=0,
        )

        with patch(
            "CoreSTT.transcription_engines.faster_whisper_engine._load_faster_whisper",
            return_value=(FakeWhisperModule, FakeBatchedInferencePipeline),
        ):
            FasterWhisperEngine(config)

        self.assertEqual(FakeWhisperModule.model_kwargs["cpu_threads"], 4)
        self.assertEqual(FakeWhisperModule.model_kwargs["num_workers"], 2)
        self.assertEqual(FakeWhisperModule.model_kwargs["model_size_or_path"], "tiny.en")


if __name__ == "__main__":
    unittest.main()
