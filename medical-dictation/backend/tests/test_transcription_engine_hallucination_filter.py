import unittest
from types import SimpleNamespace

import numpy as np

from app.services.transcription_engine import TranscriptionEngine


class FakeSegment:
    def __init__(self, text, avg_logprob=-0.1, no_speech_prob=0.1):
        self.text = text
        self.avg_logprob = avg_logprob
        self.no_speech_prob = no_speech_prob


class FakeWhisperModel:
    def __init__(self, segments):
        self.segments = segments

    def transcribe(self, *args, **kwargs):
        return self.segments, SimpleNamespace(language="en", language_probability=1.0)


class WhisperHallucinationFilterTests(unittest.TestCase):
    def make_engine(self, segments):
        engine = TranscriptionEngine.__new__(TranscriptionEngine)
        engine.model = FakeWhisperModel(segments)
        engine.config = SimpleNamespace(
            BEAM_SIZE=2,
            PATIENCE=1.0,
            BEST_OF=1,
            TEMPERATURE=(0.0,),
            TRANSCRIPTION_CONTEXT_PROMPT="",
            COMPRESSION_RATIO_THRESHOLD=2.2,
            LOG_PROB_THRESHOLD=-0.7,
            NO_SPEECH_THRESHOLD=0.75,
            VAD_FILTER=True,
            VAD_PARAMETERS={},
            MIN_TRANSCRIPTION_CONFIDENCE=0.10,
            HALLUCINATION_MAX_NO_SPEECH_PROB=0.65,
        )
        return engine

    def test_run_whisper_rejects_high_no_speech_hallucination(self):
        engine = self.make_engine([
            FakeSegment("Thank you.", avg_logprob=-0.2, no_speech_prob=0.92)
        ])

        result = engine._run_whisper(np.ones(16000, dtype=np.float32))

        self.assertEqual(result["text"], "")
        self.assertEqual(result["confidence"], 0.0)

    def test_filter_hallucinations_ignores_punctuation_on_boilerplate(self):
        engine = self.make_engine([])

        self.assertEqual(engine._filter_hallucinations("Thank you."), "")
        self.assertEqual(engine._filter_hallucinations("Thanks for watching."), "")

    def test_filter_hallucinations_rejects_repeated_sentence(self):
        engine = self.make_engine([])

        self.assertEqual(
            engine._filter_hallucinations("The project is stable. The project is stable."),
            "",
        )

    def test_filter_hallucinations_rejects_instruction_leakage(self):
        engine = self.make_engine([])

        self.assertEqual(
            engine._filter_hallucinations("Transcribe only the words spoken by the speaker."),
            "",
        )

    def test_run_whisper_keeps_low_confidence_speech_when_no_speech_is_low(self):
        engine = self.make_engine([
            FakeSegment("No blockers.", avg_logprob=-2.0, no_speech_prob=0.1)
        ])

        result = engine._run_whisper(np.ones(16000, dtype=np.float32))

        self.assertEqual(result["text"], "No blockers.")
        self.assertLess(result["confidence"], 0.25)

    def test_run_whisper_keeps_confident_speech(self):
        engine = self.make_engine([
            FakeSegment("Project has momentum.", avg_logprob=-0.1, no_speech_prob=0.05)
        ])

        result = engine._run_whisper(np.ones(16000, dtype=np.float32))

        self.assertEqual(result["text"], "Project has momentum.")
        self.assertGreaterEqual(result["confidence"], 0.10)


if __name__ == "__main__":
    unittest.main()
