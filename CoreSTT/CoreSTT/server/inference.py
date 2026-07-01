import collections
import logging
import threading
import time
from dataclasses import dataclass
from typing import Any, Callable, Dict, Optional

from .audio import SERVER_SAMPLE_RATE, effective_device, read_wav_float32
from .settings import ServerSettings
from .stats import RunningStats


LOGGER = logging.getLogger("corestt.fastapi")


@dataclass(frozen=True)
class InferenceJob:
    request_id: str
    session_id: str
    kind: str
    audio: Any
    language: Optional[str]
    use_prompt: bool
    segment_id: int
    sequence: int
    generation: int
    created_at: float
    deadline_at: Optional[float] = None
    sample_rate: int = SERVER_SAMPLE_RATE
    initial_prompt: Any = None
    override_initial_prompt: bool = False
    engine_options: Optional[Dict[str, Any]] = None
    override_engine_options: bool = False


@dataclass(frozen=True)
class InferenceResult:
    request_id: str
    session_id: str
    kind: str
    segment_id: int
    sequence: int
    generation: int
    text: str
    error: Optional[str]
    created_at: float
    started_at: float
    completed_at: float
    queue_delay: float
    inference_duration: float
    total_latency: float


@dataclass(frozen=True)
class QueueSubmitResult:
    accepted: bool
    reason: str = ""
    coalesced: bool = False


class FairInferenceQueue:
    def __init__(self, name, settings: ServerSettings, drop_callback=None):
        self.name = name
        self.settings = settings
        self.drop_callback = drop_callback
        self._condition = threading.Condition()
        self._sessions = {}
        self._ordered_sessions = collections.deque()
        self._queued_session_ids = set()
        self._total_queued = 0
        self._closed = False
        self._coalesced_realtime = 0
        self._stale_realtime_dropped = 0
        self._rejected_jobs = 0

    def submit(self, job: InferenceJob):
        dropped_jobs = []
        with self._condition:
            if self._closed:
                return QueueSubmitResult(False, "scheduler is stopped")

            state = self._sessions.setdefault(
                job.session_id,
                {"final": collections.deque(), "realtime": None},
            )

            if job.kind == "final":
                if len(state["final"]) >= self.settings.max_final_queue_depth_per_session:
                    self._rejected_jobs += 1
                    return QueueSubmitResult(False, "session final queue is full")
                if self._total_queued >= self.settings.max_global_inference_queue_depth:
                    self._rejected_jobs += 1
                    return QueueSubmitResult(False, "global inference queue is full")
                state["final"].append(job)
                self._total_queued += 1
                self._ensure_session_locked(job.session_id)
                self._condition.notify()
                return QueueSubmitResult(True)

            if job.kind != "realtime":
                self._rejected_jobs += 1
                return QueueSubmitResult(False, f"unknown inference kind: {job.kind}")

            old_job = state["realtime"]
            if old_job is not None:
                state["realtime"] = job
                dropped_jobs.append((old_job, "coalesced"))
                self._coalesced_realtime += 1
                self._ensure_session_locked(job.session_id)
                self._condition.notify()
                result = QueueSubmitResult(True, coalesced=True)
            elif self._total_queued >= self.settings.max_global_inference_queue_depth:
                self._rejected_jobs += 1
                result = QueueSubmitResult(False, "global inference queue is full")
            else:
                state["realtime"] = job
                self._total_queued += 1
                self._ensure_session_locked(job.session_id)
                self._condition.notify()
                result = QueueSubmitResult(True)

        self._notify_drops(dropped_jobs)
        return result

    def get(self):
        while True:
            stale_jobs = []
            job = None
            with self._condition:
                while not self._closed:
                    job = None
                    now = time.monotonic()
                    while self._ordered_sessions:
                        session_id = self._ordered_sessions.popleft()
                        self._queued_session_ids.discard(session_id)
                        state = self._sessions.get(session_id)
                        if state is None:
                            continue

                        job = None
                        if state["final"]:
                            job = state["final"].popleft()
                        elif state["realtime"] is not None:
                            realtime_job = state["realtime"]
                            state["realtime"] = None
                            if (
                                realtime_job.deadline_at is not None
                                and realtime_job.deadline_at < now
                            ):
                                self._total_queued -= 1
                                self._stale_realtime_dropped += 1
                                stale_jobs.append((realtime_job, "stale"))
                                self._cleanup_session_locked(session_id)
                                continue
                            job = realtime_job

                        if job is None:
                            self._cleanup_session_locked(session_id)
                            continue

                        self._total_queued -= 1
                        if self._session_has_work_locked(session_id):
                            self._ensure_session_locked(session_id)
                        else:
                            self._cleanup_session_locked(session_id)
                        break

                    if job is not None:
                        break
                    if stale_jobs:
                        break
                    self._condition.wait(timeout=0.2)

                if self._closed:
                    return None

            self._notify_drops(stale_jobs)
            if job is not None:
                return job

    def cancel_session(self, session_id):
        dropped = []
        with self._condition:
            state = self._sessions.pop(session_id, None)
            self._queued_session_ids.discard(session_id)
            if state is None:
                return
            while state["final"]:
                dropped.append((state["final"].popleft(), "cancelled"))
                self._total_queued -= 1
            if state["realtime"] is not None:
                dropped.append((state["realtime"], "cancelled"))
                self._total_queued -= 1
                state["realtime"] = None
            self._condition.notify_all()
        self._notify_drops(dropped)

    def close(self):
        with self._condition:
            self._closed = True
            self._condition.notify_all()

    def snapshot(self):
        with self._condition:
            per_session = {
                session_id: {
                    "final": len(state["final"]),
                    "realtime": 1 if state["realtime"] is not None else 0,
                }
                for session_id, state in self._sessions.items()
            }
            return {
                "name": self.name,
                "queued": self._total_queued,
                "sessions": len(self._sessions),
                "perSession": per_session,
                "coalescedRealtime": self._coalesced_realtime,
                "staleRealtimeDropped": self._stale_realtime_dropped,
                "rejectedJobs": self._rejected_jobs,
            }

    def _ensure_session_locked(self, session_id):
        if session_id not in self._queued_session_ids:
            self._queued_session_ids.add(session_id)
            self._ordered_sessions.append(session_id)

    def _session_has_work_locked(self, session_id):
        state = self._sessions.get(session_id)
        if state is None:
            return False
        return bool(state["final"]) or state["realtime"] is not None

    def _cleanup_session_locked(self, session_id):
        if not self._session_has_work_locked(session_id):
            self._sessions.pop(session_id, None)

    def _notify_drops(self, dropped_jobs):
        if not self.drop_callback:
            return
        for job, reason in dropped_jobs:
            try:
                self.drop_callback(job, reason, self.name)
            except Exception:
                LOGGER.exception("Drop callback failed")


class SharedEngineWorker:
    def __init__(
        self,
        name,
        settings: ServerSettings,
        queue: FairInferenceQueue,
        engine_factory: Callable[[], Any],
        result_callback: Callable[[InferenceResult], None],
        error_callback: Optional[Callable[[str, Exception], None]] = None,
    ):
        self.name = name
        self.settings = settings
        self.queue = queue
        self.engine_factory = engine_factory
        self.result_callback = result_callback
        self.error_callback = error_callback
        self.ready = threading.Event()
        self.stop_event = threading.Event()
        self.thread = None
        self.engine = None
        self.load_error = None
        self.busy_seconds = 0.0
        self.started_at = time.monotonic()
        self.completed_jobs = 0
        self.failed_jobs = 0
        self.queue_delay = RunningStats()
        self.inference_duration = RunningStats()
        self.total_latency = RunningStats()

    def start(self):
        self.thread = threading.Thread(
            target=self._worker,
            name=f"CoreSTT-{self.name}-Inference",
            daemon=True,
        )
        self.thread.start()

    def stop(self):
        self.stop_event.set()
        self.queue.close()
        if self.thread is not None:
            self.thread.join(timeout=10)

    def snapshot(self):
        elapsed = max(0.001, time.monotonic() - self.started_at)
        return {
            "name": self.name,
            "ready": self.ready.is_set(),
            "healthy": self.load_error is None,
            "completedJobs": self.completed_jobs,
            "failedJobs": self.failed_jobs,
            "busyRatio": min(1.0, self.busy_seconds / elapsed),
            "queueDelay": self.queue_delay.snapshot_ms(),
            "inferenceDuration": self.inference_duration.snapshot_ms(),
            "totalLatency": self.total_latency.snapshot_ms(),
        }

    def _worker(self):
        try:
            self.engine = self.engine_factory()
            self._warmup()
        except Exception as exc:
            self.load_error = exc
            LOGGER.exception("Could not initialize %s inference engine", self.name)
            if self.error_callback:
                self.error_callback(self.name, exc)
        finally:
            self.ready.set()

        while not self.stop_event.is_set():
            job = self.queue.get()
            if job is None:
                break

            started_at = time.monotonic()
            text = ""
            error = None

            try:
                if self.engine is None:
                    raise RuntimeError(f"{self.name} inference engine is unavailable")
                result = self._transcribe(job)
                text = (getattr(result, "text", "") or "").strip()
                self.completed_jobs += 1
            except Exception as exc:
                self.failed_jobs += 1
                error = str(exc)
                LOGGER.exception("Inference job failed: %s", job.request_id)

            completed_at = time.monotonic()
            queue_delay = max(0.0, started_at - job.created_at)
            inference_duration = max(0.0, completed_at - started_at)
            total_latency = max(0.0, completed_at - job.created_at)
            self.busy_seconds += inference_duration
            self.queue_delay.record(queue_delay)
            self.inference_duration.record(inference_duration)
            self.total_latency.record(total_latency)
            self.result_callback(
                InferenceResult(
                    request_id=job.request_id,
                    session_id=job.session_id,
                    kind=job.kind,
                    segment_id=job.segment_id,
                    sequence=job.sequence,
                    generation=job.generation,
                    text=text,
                    error=error,
                    created_at=job.created_at,
                    started_at=started_at,
                    completed_at=completed_at,
                    queue_delay=queue_delay,
                    inference_duration=inference_duration,
                    total_latency=total_latency,
                )
            )

    def _warmup(self):
        if not self.settings.model_warmup or self.engine is None:
            return
        from pathlib import Path

        warmup_path = Path(__file__).resolve().parents[1] / "assets" / "warmup_audio.wav"
        try:
            audio = read_wav_float32(warmup_path).samples
            self.engine.warmup(audio)
        except Exception:
            LOGGER.debug("Warmup skipped for %s", self.name, exc_info=True)

    def _transcribe(self, job):
        config = getattr(self.engine, "config", None)
        if config is None:
            return self.engine.transcribe(
                job.audio,
                language=job.language if job.language else None,
                use_prompt=job.use_prompt,
            )

        old_prompt = getattr(config, "initial_prompt", None)
        old_options = getattr(config, "engine_options", None)
        if job.override_initial_prompt:
            config.initial_prompt = job.initial_prompt
        if job.override_engine_options:
            config.engine_options = job.engine_options
        try:
            return self.engine.transcribe(
                job.audio,
                language=job.language if job.language else None,
                use_prompt=job.use_prompt,
            )
        finally:
            config.initial_prompt = old_prompt
            config.engine_options = old_options


class InferenceScheduler:
    def __init__(
        self,
        settings: ServerSettings,
        result_callback: Callable[[InferenceResult], None],
        drop_callback: Optional[Callable[[InferenceJob, str, str], None]] = None,
        error_callback: Optional[Callable[[str, Exception], None]] = None,
    ):
        self.settings = settings
        self.result_callback = result_callback
        self.drop_callback = drop_callback
        self.error_callback = error_callback
        self.main_queue = FairInferenceQueue("main", settings, drop_callback)
        self.realtime_queue = (
            self.main_queue
            if settings.use_main_model_for_realtime
            else FairInferenceQueue("realtime", settings, drop_callback)
        )
        self.main_worker = SharedEngineWorker(
            "main",
            settings,
            self.main_queue,
            self._create_main_engine,
            result_callback,
            error_callback,
        )
        self.realtime_worker = None
        if not settings.use_main_model_for_realtime:
            self.realtime_worker = SharedEngineWorker(
                "realtime",
                settings,
                self.realtime_queue,
                self._create_realtime_engine,
                result_callback,
                error_callback,
            )

    def start(self):
        self.main_worker.start()
        if self.realtime_worker is not None:
            self.realtime_worker.start()

    def stop(self):
        self.main_worker.stop()
        if self.realtime_worker is not None:
            self.realtime_worker.stop()

    def wait_ready(self, timeout=None):
        deadline = None if timeout is None else time.monotonic() + timeout
        workers = [self.main_worker]
        if self.realtime_worker is not None:
            workers.append(self.realtime_worker)

        for worker in workers:
            remaining = None if deadline is None else max(0.0, deadline - time.monotonic())
            if not worker.ready.wait(timeout=remaining):
                return False
        return True

    def healthy(self):
        if self.main_worker.load_error is not None:
            return False
        if self.realtime_worker is not None and self.realtime_worker.load_error is not None:
            return False
        return True

    def submit(self, job: InferenceJob):
        if job.kind == "realtime" and not self.settings.use_main_model_for_realtime:
            return self.realtime_queue.submit(job)
        return self.main_queue.submit(job)

    def cancel_session(self, session_id):
        self.main_queue.cancel_session(session_id)
        if self.realtime_queue is not self.main_queue:
            self.realtime_queue.cancel_session(session_id)

    def snapshot(self):
        data = {
            "mode": (
                "low-memory-one-model"
                if self.settings.use_main_model_for_realtime
                else "balanced-main-plus-realtime"
            ),
            "queues": {"main": self.main_queue.snapshot()},
            "workers": {"main": self.main_worker.snapshot()},
        }
        if self.realtime_queue is not self.main_queue:
            data["queues"]["realtime"] = self.realtime_queue.snapshot()
        if self.realtime_worker is not None:
            data["workers"]["realtime"] = self.realtime_worker.snapshot()
        return data

    def _create_main_engine(self):
        from CoreSTT.transcription_engines import (
            TranscriptionEngineConfig,
            create_transcription_engine,
        )

        return create_transcription_engine(
            self.settings.transcription_engine,
            TranscriptionEngineConfig(
                model=self.settings.model,
                download_root=self.settings.download_root,
                compute_type=self.settings.compute_type,
                gpu_device_index=self.settings.gpu_device_index,
                device=effective_device(self.settings.device),
                beam_size=self.settings.beam_size,
                initial_prompt=self.settings.initial_prompt,
                batch_size=self.settings.batch_size,
                vad_filter=self.settings.vad_filter,
                normalize_audio=self.settings.normalize_audio,
                engine_options=self.settings.transcription_engine_options,
            ),
        )

    def _create_realtime_engine(self):
        from CoreSTT.transcription_engines import (
            TranscriptionEngineConfig,
            create_transcription_engine,
        )

        return create_transcription_engine(
            self.settings.realtime_transcription_engine
            or self.settings.transcription_engine,
            TranscriptionEngineConfig(
                model=self.settings.realtime_model or self.settings.model,
                download_root=self.settings.download_root,
                compute_type=self.settings.compute_type,
                gpu_device_index=self.settings.gpu_device_index,
                device=effective_device(self.settings.device),
                beam_size=self.settings.beam_size_realtime,
                initial_prompt=self.settings.initial_prompt_realtime,
                batch_size=self.settings.realtime_batch_size,
                vad_filter=self.settings.vad_filter,
                normalize_audio=self.settings.normalize_audio,
                engine_options=(
                    self.settings.realtime_transcription_engine_options
                    if self.settings.realtime_transcription_engine_options is not None
                    else self.settings.transcription_engine_options
                ),
            ),
        )


class SchedulerTranscriptionExecutor:
    def __init__(self, service, session_id, kind):
        self.service = service
        self.session_id = session_id
        self.kind = kind

    def transcribe(self, audio, language=None, use_prompt=True):
        return self.service.transcribe_for_recorder(
            self.session_id,
            self.kind,
            audio,
            language,
            use_prompt,
        )
