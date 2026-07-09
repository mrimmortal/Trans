import unittest
from types import SimpleNamespace

from CoreSTT.server.inference import InferenceJob, SharedEngineWorker


class FakeEngine:
    def __init__(self):
        self.config = SimpleNamespace(
            initial_prompt="global prompt",
            engine_options={"hotwords": "global"},
        )
        self.calls = []

    def transcribe(self, _audio, language=None, use_prompt=True):
        self.calls.append(
            {
                "language": language,
                "use_prompt": use_prompt,
                "initial_prompt": self.config.initial_prompt,
                "engine_options": self.config.engine_options,
            }
        )
        return SimpleNamespace(text="ok")


class SharedEngineWorkerTest(unittest.TestCase):
    def test_transcribe_applies_and_restores_job_prompt_and_engine_options(self):
        worker = SharedEngineWorker.__new__(SharedEngineWorker)
        worker.engine = FakeEngine()
        job = InferenceJob(
            request_id="request",
            session_id="session",
            kind="final",
            audio=[0.0],
            language="en",
            use_prompt=True,
            segment_id=1,
            sequence=0,
            generation=0,
            created_at=0.0,
            initial_prompt=None,
            override_initial_prompt=True,
            engine_options=None,
            override_engine_options=True,
        )

        result = worker._transcribe(job)

        self.assertEqual(result.text, "ok")
        self.assertEqual(
            worker.engine.calls,
            [
                {
                    "language": "en",
                    "use_prompt": True,
                    "initial_prompt": None,
                    "engine_options": None,
                }
            ],
        )
        self.assertEqual(worker.engine.config.initial_prompt, "global prompt")
        self.assertEqual(worker.engine.config.engine_options, {"hotwords": "global"})


if __name__ == "__main__":
    unittest.main()
