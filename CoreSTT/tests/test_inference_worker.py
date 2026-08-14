import threading
import time
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from CoreSTT.server.inference import (
    FairInferenceQueue,
    InferenceExecutionGate,
    InferenceJob,
    InferenceScheduler,
    SharedEngineWorker,
)
from CoreSTT.server.settings import ServerSettings


class FakeEngine:
    def __init__(self):
        self.config = SimpleNamespace(
            initial_prompt="global prompt",
            engine_options={"hotwords": "global"},
            model="small.en",
            device="cpu",
            compute_type="int8",
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
    @staticmethod
    def _job(kind, session_id, segment_id):
        return InferenceJob(
            request_id=f"{kind}-{session_id}-{segment_id}",
            session_id=session_id,
            kind=kind,
            audio=[0.0],
            language="en",
            use_prompt=True,
            segment_id=segment_id,
            sequence=0,
            generation=0,
            created_at=0.0,
        )

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

    def test_fair_queue_prioritizes_final_jobs_across_sessions(self):
        queue = FairInferenceQueue("test", ServerSettings())
        realtime = self._job("realtime", "session-a", 1)
        final = self._job("final", "session-b", 2)

        queue.submit(realtime)
        queue.submit(final)

        self.assertEqual(queue.get(), final)
        self.assertEqual(queue.get(), realtime)

    def test_cancel_realtime_only_removes_matching_segment(self):
        dropped = []
        queue = FairInferenceQueue(
            "test",
            ServerSettings(),
            lambda job, reason, lane: dropped.append((job, reason, lane)),
        )
        realtime = self._job("realtime", "session-a", 1)
        queue.submit(realtime)

        self.assertEqual(queue.cancel_realtime("session-a", 2), 0)
        self.assertEqual(queue.cancel_realtime("session-a", 1), 1)
        self.assertEqual(queue.snapshot()["queued"], 0)
        self.assertEqual(dropped, [(realtime, "superseded_by_final", "test")])

    def _resource_snapshot(self):
        return {
            "process": {
                "cpuPercent": 11,
                "rssMb": 222,
                "threadCount": 3,
            },
            "system": {
                "cpuPercent": 44,
                "memoryPercent": 55,
            },
            "cuda": {
                "available": False,
                "allocatedMb": None,
                "reservedMb": None,
                "freeMb": None,
                "totalMb": None,
                "memoryPressure": None,
            },
        }

    def test_worker_does_not_log_job_performance_fields_by_default(self):
        class OneJobQueue:
            def __init__(self, job):
                self.job = job

            def get(self):
                job, self.job = self.job, None
                return job

        results = []
        worker = SharedEngineWorker(
            "main",
            ServerSettings(model_warmup=False, device="cpu", compute_type="int8"),
            OneJobQueue(self._job("final", "session-a", 1)),
            FakeEngine,
            results.append,
            resource_snapshot_provider=self._resource_snapshot,
        )

        with patch("CoreSTT.server.inference.LOGGER.info") as log_info:
            worker._worker()

        log_info.assert_not_called()
        self.assertEqual(len(results), 1)
        self.assertIn("gateWait", worker.snapshot())

    def test_worker_logs_resource_fields_when_diagnostic_logging_enabled(self):
        class OneJobQueue:
            def __init__(self, job):
                self.job = job

            def get(self):
                job, self.job = self.job, None
                return job

        results = []
        worker = SharedEngineWorker(
            "main",
            ServerSettings(
                model_warmup=False,
                device="cpu",
                compute_type="int8",
                diagnostic_logging_enabled=True,
            ),
            OneJobQueue(self._job("final", "session-a", 1)),
            FakeEngine,
            results.append,
            resource_snapshot_provider=self._resource_snapshot,
        )

        with self.assertLogs("corestt.fastapi", level="INFO") as logs:
            worker._worker()

        log = "\n".join(logs.output)
        for field in (
            "kind=final",
            "model=small.en",
            "device=cpu",
            "compute_type=int8",
            "audio_duration=",
            "queue_delay=",
            "inference_duration=",
            "total_latency=",
            "gate_wait=",
            "cpu_percent=44",
            "process_cpu_percent=11",
            "rss_mb=222",
            "system_memory_percent=55",
            "thread_count=3",
            "cuda_available=False",
        ):
            self.assertIn(field, log)
        self.assertEqual(len(results), 1)

    def test_final_submission_cancels_matching_queued_realtime_job(self):
        dropped = []
        scheduler = InferenceScheduler(
            ServerSettings(model_warmup=False),
            lambda _result: None,
            lambda job, reason, lane: dropped.append((job, reason, lane)),
        )
        realtime = self._job("realtime", "session-a", 1)
        final = self._job("final", "session-a", 1)

        scheduler.submit(realtime)
        result = scheduler.submit(final)

        self.assertTrue(result.accepted)
        self.assertEqual(scheduler.realtime_queue.snapshot()["queued"], 0)
        self.assertEqual(scheduler.main_queue.snapshot()["queued"], 1)
        self.assertEqual(
            dropped,
            [(realtime, "superseded_by_final", "realtime")],
        )

    def test_scheduler_omits_realtime_resources_when_disabled(self):
        results = []
        result_ready = threading.Event()

        def capture_result(result):
            results.append(result)
            result_ready.set()

        scheduler = InferenceScheduler(
            ServerSettings(
                model_warmup=False,
                device="cpu",
                realtime_transcription_enabled=False,
            ),
            capture_result,
        )

        with patch(
            "CoreSTT.transcription_engines.create_transcription_engine",
            return_value=FakeEngine(),
        ) as create_engine:
            scheduler.start()
            try:
                self.assertTrue(scheduler.wait_ready(timeout=1))
                self.assertTrue(
                    scheduler.submit(self._job("final", "session-a", 1)).accepted
                )
                self.assertTrue(result_ready.wait(timeout=1))
            finally:
                scheduler.stop()

        self.assertEqual(create_engine.call_count, 1)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].kind, "final")
        self.assertEqual(results[0].text, "ok")
        self.assertIsNone(scheduler.realtime_queue)
        self.assertIsNone(scheduler.realtime_worker)
        self.assertIsNone(scheduler.execution_gate)

        snapshot = scheduler.snapshot()
        self.assertEqual(snapshot["mode"], "final-only")
        self.assertNotIn("realtime", snapshot["queues"])
        self.assertNotIn("realtime", snapshot["workers"])

    def test_scheduler_rejects_realtime_jobs_when_disabled(self):
        scheduler = InferenceScheduler(
            ServerSettings(
                model_warmup=False,
                realtime_transcription_enabled=False,
            ),
            lambda _result: None,
        )

        realtime_result = scheduler.submit(self._job("realtime", "session-a", 1))
        final_result = scheduler.submit(self._job("final", "session-a", 1))

        self.assertFalse(realtime_result.accepted)
        self.assertEqual(
            realtime_result.reason,
            "realtime transcription is disabled",
        )
        self.assertTrue(final_result.accepted)
        self.assertEqual(scheduler.main_queue.snapshot()["queued"], 1)

    def test_scheduler_routes_fixed_models_and_split_vad_settings(self):
        scheduler = InferenceScheduler(
            ServerSettings(
                model_warmup=False,
                compute_type="int8",
                cpu_threads=4,
                num_workers=2,
                vad_filter_final=True,
                vad_filter_realtime=False,
            ),
            lambda _result: None,
        )
        captured = []

        def capture(_engine_name, config):
            captured.append(config)
            return object()

        with patch(
            "CoreSTT.transcription_engines.create_transcription_engine",
            side_effect=capture,
        ):
            scheduler._create_main_engine()
            scheduler._create_realtime_engine()

        self.assertEqual(captured[0].model, "small.en")
        self.assertEqual(captured[0].compute_type, "int8")
        self.assertEqual(captured[0].cpu_threads, 4)
        self.assertEqual(captured[0].num_workers, 2)
        self.assertTrue(captured[0].vad_filter)
        self.assertEqual(captured[1].model, "tiny.en")
        self.assertEqual(captured[1].compute_type, "int8")
        self.assertEqual(captured[1].cpu_threads, 4)
        self.assertEqual(captured[1].num_workers, 2)
        self.assertFalse(captured[1].vad_filter)

    def test_scheduler_enables_single_gpu_gate_only_for_cuda(self):
        with patch("CoreSTT.server.inference.effective_device", return_value="cuda"):
            scheduler = InferenceScheduler(
                ServerSettings(model_warmup=False),
                lambda _result: None,
            )
            disabled = InferenceScheduler(
                ServerSettings(model_warmup=False, single_gpu_inference_gate=False),
                lambda _result: None,
            )

        self.assertIsNotNone(scheduler.execution_gate)
        self.assertTrue(scheduler.snapshot()["singleGpuInferenceGate"])
        self.assertIsNone(disabled.execution_gate)
        self.assertFalse(disabled.snapshot()["singleGpuInferenceGate"])

        with patch("CoreSTT.server.inference.effective_device", return_value="cpu"):
            cpu_scheduler = InferenceScheduler(
                ServerSettings(model_warmup=False, device="cpu"),
                lambda _result: None,
            )
        self.assertIsNone(cpu_scheduler.execution_gate)

    def test_execution_gate_waits_for_queued_final_before_realtime(self):
        final_pending = True
        gate = InferenceExecutionGate(lambda: final_pending)
        realtime_started = threading.Event()

        def run_realtime():
            gate.acquire("realtime")
            try:
                realtime_started.set()
            finally:
                gate.release("realtime")

        thread = threading.Thread(target=run_realtime)
        thread.start()

        self.assertFalse(realtime_started.wait(timeout=0.05))
        final_pending = False
        self.assertTrue(realtime_started.wait(timeout=0.3))
        thread.join(timeout=1)
        self.assertFalse(thread.is_alive())

    def test_execution_gate_waiting_final_blocks_new_realtime(self):
        gate = InferenceExecutionGate(lambda: False)
        self.assertTrue(gate.acquire("realtime"))
        final_started = threading.Event()
        second_realtime_started = threading.Event()

        def run_final():
            gate.acquire("final")
            try:
                final_started.set()
                time.sleep(0.05)
            finally:
                gate.release("final")

        def run_second_realtime():
            gate.acquire("realtime")
            try:
                second_realtime_started.set()
            finally:
                gate.release("realtime")

        final_thread = threading.Thread(target=run_final)
        realtime_thread = threading.Thread(target=run_second_realtime)
        final_thread.start()
        time.sleep(0.05)
        realtime_thread.start()

        self.assertFalse(second_realtime_started.wait(timeout=0.05))
        gate.release("realtime")
        self.assertTrue(final_started.wait(timeout=0.3))
        self.assertFalse(second_realtime_started.is_set())
        final_thread.join(timeout=1)
        self.assertTrue(second_realtime_started.wait(timeout=0.3))
        realtime_thread.join(timeout=1)
        self.assertFalse(final_thread.is_alive())
        self.assertFalse(realtime_thread.is_alive())


if __name__ == "__main__":
    unittest.main()
