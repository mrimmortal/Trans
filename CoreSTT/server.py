import argparse
import asyncio
import collections
import json
import logging
import threading
import time
import uuid
from dataclasses import asdict, dataclass, replace
from pathlib import Path
from typing import Any, Callable, Deque, Dict, List, Optional, Tuple

try:
    import numpy as np
except ModuleNotFoundError as exc:  # pragma: no cover - numpy is a core dependency
    raise RuntimeError(
        "The FastAPI server requires numpy. Install project dependencies first."
    ) from exc

try:
    from .protocol import (
        AudioPacketError,
        decode_audio_packet,
        normalize_engine_name,
        parse_json_object,
        require_positive_int,
    )
except ImportError:
    from protocol import (
        AudioPacketError,
        decode_audio_packet,
        normalize_engine_name,
        parse_json_object,
        require_positive_int,
    )

from CoreSTT.server.settings import (
    ACTIVE_RUNTIME_SETTINGS,
    BASE_TUNING_DEFAULTS,
    BOOL_SETTINGS,
    DICT_SETTINGS,
    FLOAT_SETTINGS,
    INT_SETTINGS,
    NEW_SESSION_RUNTIME_SETTINGS,
    OPTIONAL_STRING_SETTINGS,
    STARTUP_ONLY_SETTINGS,
    TUNING_PROFILES,
    TUPLE_FLOAT_SETTINGS,
    ServerSettings,
    coerce_setting_value,
    runtime_settings_contract,
)
from CoreSTT.server.audio import (
    INT16_MAX_ABS_VALUE,
    SERVER_SAMPLE_RATE,
    AudioData,
    effective_device,
    read_wav_float32,
    resample_int16,
)
from CoreSTT.server.cli import parse_args, parse_float_tuple, settings_from_args
from CoreSTT.server.connection import ConnectionManager
from CoreSTT.server.domain_profiles import (
    DomainProfileError,
    compose_domain_profile,
    load_domain_profiles,
    save_domain_profiles,
)
from CoreSTT.server.inference import (
    FairInferenceQueue,
    InferenceExecutionGate,
    InferenceJob,
    InferenceResult,
    InferenceScheduler,
    QueueSubmitResult,
    SchedulerTranscriptionExecutor,
    SharedEngineWorker,
)
from CoreSTT.server.monitoring import (
    DIAGNOSTIC_THRESHOLDS,
    ResourceMonitor,
    diagnose_bottleneck,
)
from CoreSTT.server.stats import RunningStats
from CoreSTT.server.timeline import (
    SegmentState,
    SegmentTimelineTracker,
    segment_text_fields,
    timestamp_iso,
)


LOGGER = logging.getLogger("corestt.fastapi")
TERMINAL_LOGGER = logging.getLogger("uvicorn.error")
STATIC_DIR = Path(__file__).resolve().parent / "static"
INDEX_PATH = STATIC_DIR / "index.html"


def _domain_engine_options(options, hotwords):
    merged = dict(options or {})
    if hotwords:
        merged["hotwords"] = hotwords
    else:
        merged.pop("hotwords", None)
    return merged or None


def _log_stream_started(session_id, domain_name):
    active_domain = domain_name or "default"
    message = "session %s streaming started domain=%s"
    LOGGER.info(message, session_id, active_domain)
    if TERMINAL_LOGGER is not LOGGER:
        TERMINAL_LOGGER.info(message, session_id, active_domain)


class VoiceActivityDetector:
    def __init__(self, settings: ServerSettings):
        self.settings = settings
        self.vad = None
        try:
            import webrtcvad

            self.vad = webrtcvad.Vad()
            self.vad.set_mode(int(settings.webrtc_sensitivity))
        except Exception:
            self.vad = None

    def is_speech(self, samples):
        if samples is None or samples.size == 0:
            return False

        if self.vad is not None and samples.size >= 160:
            try:
                frame_samples = 320
                usable = samples.size - (samples.size % frame_samples)
                speech_frames = 0
                checked_frames = 0
                for start in range(0, usable, frame_samples):
                    frame = samples[start:start + frame_samples]
                    checked_frames += 1
                    if self.vad.is_speech(
                        np.asarray(frame, dtype=np.int16).tobytes(),
                        SERVER_SAMPLE_RATE,
                    ):
                        speech_frames += 1
                if checked_frames:
                    return speech_frames / checked_frames >= 0.25
            except Exception:
                LOGGER.debug("webrtcvad failed; falling back to energy VAD", exc_info=True)

        rms = float(np.sqrt(np.mean(samples.astype(np.float32) ** 2)))
        return rms >= float(self.settings.vad_energy_threshold)


class RealtimeSession:
    def __init__(self, service, session_id):
        self.service = service
        self.settings = replace(service.settings)
        self.session_id = session_id
        self.segment_state = SegmentState()
        self.timeline = SegmentTimelineTracker(self.settings)
        self.vad = VoiceActivityDetector(self.settings)
        self.lock = threading.RLock()
        self.streaming = False
        self.recording = False
        self.status = "idle"
        self.generation = 0
        self.active_segment_id = None
        self.latest_realtime_sequence = 0
        self.last_realtime_submit_at = 0.0
        self.last_speech_at = 0.0
        self.recording_started_at = 0.0
        self.recording_frames: List[Any] = []
        self.recording_sample_count = 0
        self.realtime_frames: Deque[Any] = collections.deque()
        self.realtime_sample_count = 0
        self.prebuffer = collections.deque()
        self.prebuffer_sample_count = 0
        self.domain_name = None
        self.domain_profile_applied = False
        self.finalizing_segment_ids = set()
        self.finalized_segment_ids = set()
        self.dropped_audio_chunks = 0
        self.rejected_audio_chunks = 0
        self.coalesced_realtime = 0
        self.stale_realtime_discarded = 0
        self.cancelled_jobs = 0
        self.realtime_submitted = 0
        self.final_submitted = 0
        self.realtime_completed = 0
        self.final_completed = 0
        self.realtime_rejected = 0
        self.final_rejected = 0
        self.final_queue_full = 0
        self.queue_delay = {"realtime": RunningStats(), "final": RunningStats()}
        self.inference_duration = {"realtime": RunningStats(), "final": RunningStats()}
        self.total_latency = {"realtime": RunningStats(), "final": RunningStats()}

    def start_streaming(self, domain_profile=None, domain_name=None):
        if domain_profile is not None or domain_name is not None:
            self.apply_domain_profile(domain_profile, domain_name)
        with self.lock:
            self.streaming = True
            self.status = (
                "wakeword_wait"
                if self.settings.wake_word_enabled()
                and self.settings.wake_word_activation_delay <= 0
                else "listening"
            )
            active_domain = self.domain_name or "default"
        _log_stream_started(self.session_id, active_domain)
        self.publish_status(self.status)

    def apply_domain_profile(self, profile, domain_name):
        with self.lock:
            if self.streaming:
                raise ValueError("Domain can only be changed before streaming starts.")
            profile_applied = profile is not None
            if self.domain_name == domain_name and self.domain_profile_applied == profile_applied:
                return
            self.generation += 1
            if profile is not None:
                self.settings.initial_prompt = profile.initial_prompt
                self.settings.initial_prompt_realtime = profile.initial_prompt_realtime
                self.settings.transcription_engine_options = _domain_engine_options(
                    self.settings.transcription_engine_options,
                    profile.hotwords,
                )
                self.settings.realtime_transcription_engine_options = _domain_engine_options(
                    self.settings.realtime_transcription_engine_options,
                    getattr(profile, "realtime_hotwords", profile.hotwords),
                )
            self.domain_name = domain_name
            self.domain_profile_applied = profile_applied

    def stop_streaming(self):
        jobs = []
        with self.lock:
            self.streaming = False
            final_job = self._finish_recording_locked("stop")
            if final_job is not None:
                jobs.append(final_job)
            self.status = "idle"
        for job in jobs:
            self.service.submit_inference_job(job)
        self.service.deactivate_speaker(self.session_id)
        self.publish_status("idle")

    def close(self):
        with self.lock:
            self.generation += 1
            self.streaming = False
            self.recording = False
            self.recording_frames = []
            self.recording_sample_count = 0
            self.realtime_frames.clear()
            self.realtime_sample_count = 0
            self.prebuffer.clear()
            self.prebuffer_sample_count = 0
            self.finalizing_segment_ids.clear()
            self.finalized_segment_ids.clear()
            self.timeline.reset()
        self.service.scheduler.cancel_session(self.session_id)
        self.service.deactivate_speaker(self.session_id)

    def clear(self):
        with self.lock:
            self.generation += 1
            self.recording = False
            self.recording_frames = []
            self.recording_sample_count = 0
            self.realtime_frames.clear()
            self.realtime_sample_count = 0
            self.prebuffer.clear()
            self.prebuffer_sample_count = 0
            self.finalizing_segment_ids.clear()
            self.finalized_segment_ids.clear()
            self.active_segment_id = None
            self.latest_realtime_sequence = 0
            next_segment = self.segment_state.reset()
            self.timeline.reset()
            self.status = self._waiting_state_locked()
        self.service.scheduler.cancel_session(self.session_id)
        self.service.deactivate_speaker(self.session_id)
        self.service.manager.publish_session(
            self.session_id,
            {
                "type": "clear",
                "sessionId": self.session_id,
                "nextSegmentId": next_segment,
            },
        )
        self.publish_status(self.status)

    def ingest_audio_packet(self, packet):
        samples = self.service.packet_to_server_samples(packet)
        now = time.monotonic()
        jobs = []
        warnings = []

        with self.lock:
            self.streaming = True
            speech = self.vad.is_speech(samples)

            if not self.recording:
                if not speech:
                    self._append_prebuffer_locked(samples)
                    return True, None
                if not self.service.try_activate_speaker(self.session_id):
                    self.rejected_audio_chunks += 1
                    return False, "Server active speaker limit reached; audio chunk was ignored."
                self._start_recording_locked(now)
                self._append_recording_samples_locked(samples)
                self.last_speech_at = now
                self.status = "recording"
                warnings.append(None)
            else:
                self._append_recording_samples_locked(samples)
                if speech:
                    self.last_speech_at = now

            if self.recording:
                realtime_job = self._maybe_create_realtime_job_locked(now)
                if realtime_job is not None:
                    jobs.append(realtime_job)

                recording_seconds = self.recording_sample_count / float(SERVER_SAMPLE_RATE)
                silence_seconds = now - self.last_speech_at if self.last_speech_at else 0.0
                if (
                    recording_seconds >= self.settings.min_length_of_recording
                    and silence_seconds >= self.settings.post_speech_silence_duration
                ):
                    final_job = self._finish_recording_locked("silence")
                    if final_job is not None:
                        jobs.append(final_job)
                elif recording_seconds >= self.settings.max_audio_queue_seconds_per_session:
                    final_job = self._finish_recording_locked("max_duration")
                    if final_job is not None:
                        jobs.append(final_job)
                    warnings.append("Maximum per-session audio buffer reached; finalized the current segment.")

        for job in jobs:
            self.service.submit_inference_job(job)
        for warning in warnings:
            if warning:
                self.service.manager.publish_session(
                    self.session_id,
                    {"type": "warning", "sessionId": self.session_id, "message": warning},
                )
        self.publish_status(self.status)
        return True, None

    def handle_inference_result(self, result: InferenceResult):
        with self.lock:
            if result.generation != self.generation:
                if result.kind == "realtime":
                    self.stale_realtime_discarded += 1
                return

            if result.kind == "realtime":
                if (
                    result.segment_id in self.finalizing_segment_ids
                    or result.segment_id in self.finalized_segment_ids
                    or not self.recording
                    or result.segment_id != self.active_segment_id
                    or result.sequence < self.latest_realtime_sequence
                ):
                    self.stale_realtime_discarded += 1
                    return
                self.realtime_completed += 1
            else:
                self.finalizing_segment_ids.discard(result.segment_id)
                self.finalized_segment_ids.add(result.segment_id)
                self.final_completed += 1

            self.queue_delay[result.kind].record(result.queue_delay)
            self.inference_duration[result.kind].record(result.inference_duration)
            self.total_latency[result.kind].record(result.total_latency)

        if result.error:
            self.service.manager.publish_session(
                self.session_id,
                {
                    "type": "error",
                    "sessionId": self.session_id,
                    "message": result.error,
                    "where": result.kind,
                    "requestId": result.request_id,
                },
            )
            return

        if not result.text:
            return

        event_timestamp = time.time()
        event = {
            "type": result.kind,
            "sessionId": self.session_id,
            "segmentId": result.segment_id,
            "sequence": result.sequence,
            "text": result.text,
            "timestamp": event_timestamp,
            "timestampIso": timestamp_iso(event_timestamp),
            "requestId": result.request_id,
            "queueDelayMs": result.queue_delay * 1000.0,
            "inferenceMs": result.inference_duration * 1000.0,
            "latencyMs": result.total_latency * 1000.0,
        }
        segment = self.timeline.snapshot(result.segment_id)
        if segment is not None:
            event["segment"] = segment
            event.update(segment_text_fields(segment))
        self.service.manager.publish_session(self.session_id, event)
        if result.kind == "final":
            self.publish_status("listening" if self.streaming else "idle")

    def on_job_dropped(self, job: InferenceJob, reason: str):
        with self.lock:
            if reason == "coalesced" and job.kind == "realtime":
                self.coalesced_realtime += 1
            elif reason == "stale" and job.kind == "realtime":
                self.stale_realtime_discarded += 1
            elif reason in ("cancelled", "superseded_by_final"):
                self.cancelled_jobs += 1

    def on_submit_result(self, job: InferenceJob, result: QueueSubmitResult):
        with self.lock:
            if result.accepted:
                if job.kind == "realtime":
                    self.realtime_submitted += 1
                    if result.coalesced:
                        self.coalesced_realtime += 1
                else:
                    self.final_submitted += 1
                return

            if job.kind == "realtime":
                self.realtime_rejected += 1
            else:
                self.final_rejected += 1
                self.finalizing_segment_ids.discard(job.segment_id)
                self.finalized_segment_ids.add(job.segment_id)
                if "final queue" in result.reason:
                    self.final_queue_full += 1

        message = (
            "Realtime transcription is overloaded; interim update was dropped."
            if job.kind == "realtime"
            else f"Final transcription was rejected: {result.reason}"
        )
        self.service.manager.publish_session(
            self.session_id,
            {
                "type": "warning" if job.kind == "realtime" else "error",
                "sessionId": self.session_id,
                "message": message,
                "where": "scheduler",
            },
        )

    def publish_status(self, state=None):
        with self.lock:
            state = state or self.status
            queue_depth = self.recording_sample_count / float(SERVER_SAMPLE_RATE)
            message = {
                "type": "status",
                "sessionId": self.session_id,
                "domain": self.domain_name,
                "state": state,
                "activeClientId": self.session_id if self.streaming else None,
                "queueDepth": round(queue_depth, 3),
                "droppedChunks": self.dropped_audio_chunks,
                "coalescedRealtime": self.coalesced_realtime,
                "staleRealtimeDiscarded": self.stale_realtime_discarded,
                "activeSessions": self.service.session_count(),
                "activeSpeakers": self.service.active_speaker_count(),
                "wakeWordEnabled": self.settings.wake_word_enabled(),
            }
        self.service.manager.publish_session(self.session_id, message)

    def snapshot(self):
        with self.lock:
            return {
                "sessionId": self.session_id,
                "domain": self.domain_name,
                "streaming": self.streaming,
                "recording": self.recording,
                "state": self.status,
                "currentSegmentId": self.segment_state.current(),
                "recordingSeconds": self.recording_sample_count / float(SERVER_SAMPLE_RATE),
                "droppedAudioChunks": self.dropped_audio_chunks,
                "rejectedAudioChunks": self.rejected_audio_chunks,
                "coalescedRealtime": self.coalesced_realtime,
                "staleRealtimeDiscarded": self.stale_realtime_discarded,
                "cancelledJobs": self.cancelled_jobs,
                "realtimeSubmitted": self.realtime_submitted,
                "finalSubmitted": self.final_submitted,
                "realtimeCompleted": self.realtime_completed,
                "finalCompleted": self.final_completed,
                "realtimeRejected": self.realtime_rejected,
                "finalRejected": self.final_rejected,
                "finalQueueFull": self.final_queue_full,
                "queueDelay": {
                    "realtime": self.queue_delay["realtime"].snapshot_ms(),
                    "final": self.queue_delay["final"].snapshot_ms(),
                },
                "inferenceDuration": {
                    "realtime": self.inference_duration["realtime"].snapshot_ms(),
                    "final": self.inference_duration["final"].snapshot_ms(),
                },
                "totalLatency": {
                    "realtime": self.total_latency["realtime"].snapshot_ms(),
                    "final": self.total_latency["final"].snapshot_ms(),
                },
            }

    def _start_recording_locked(self, now):
        self.recording = True
        self.active_segment_id = self.segment_state.realtime()
        self.recording_started_at = now
        self.last_speech_at = now
        self.last_realtime_submit_at = 0.0
        self.recording_frames = list(self.prebuffer)
        self.recording_sample_count = sum(int(frame.size) for frame in self.recording_frames)
        if self.settings.realtime_transcription_enabled:
            self.realtime_frames = collections.deque(self.prebuffer)
            self.realtime_sample_count = self.recording_sample_count
            self._trim_realtime_buffer_locked()
        else:
            self.realtime_frames.clear()
            self.realtime_sample_count = 0
        self.timeline.mark_recording_started(
            self.active_segment_id,
            actual_preroll_seconds=self.prebuffer_sample_count / float(SERVER_SAMPLE_RATE),
            timestamp=time.time(),
        )
        self.prebuffer.clear()
        self.prebuffer_sample_count = 0

    def _finish_recording_locked(self, reason):
        if not self.recording and not self.recording_frames:
            return None
        segment_id = self.active_segment_id
        if segment_id is not None:
            self.finalizing_segment_ids.add(segment_id)
        audio = self._frames_to_float32(self.recording_frames)
        recording_seconds = audio.size / float(SERVER_SAMPLE_RATE) if audio is not None else 0.0
        self.timeline.mark_recording_ended(
            reason,
            segment_id=segment_id,
            actual_duration_seconds=recording_seconds,
            timestamp=time.time(),
        )
        self.recording = False
        self.recording_frames = []
        self.recording_sample_count = 0
        self.realtime_frames.clear()
        self.realtime_sample_count = 0
        self.active_segment_id = None
        self.last_realtime_submit_at = 0.0
        self.status = self._waiting_state_locked()
        self.service.deactivate_speaker(self.session_id)
        if audio is None or recording_seconds < self.settings.min_length_of_recording:
            if segment_id is not None:
                self.finalizing_segment_ids.discard(segment_id)
                self.finalized_segment_ids.add(segment_id)
            return None
        final_segment_id = self.segment_state.final()
        return InferenceJob(
            request_id=uuid.uuid4().hex,
            session_id=self.session_id,
            kind="final",
            audio=audio,
            language=self.settings.language,
            use_prompt=True,
            segment_id=final_segment_id,
            sequence=0,
            generation=self.generation,
            created_at=time.monotonic(),
            initial_prompt=self.settings.initial_prompt,
            override_initial_prompt=self.domain_profile_applied,
            engine_options=self.settings.transcription_engine_options,
            override_engine_options=self.domain_profile_applied,
        )

    def _maybe_create_realtime_job_locked(self, now):
        if not self.settings.realtime_transcription_enabled:
            return None
        pause = max(0.0, float(self.settings.realtime_processing_pause))
        if pause > 0 and now - self.last_realtime_submit_at < pause:
            return None
        if self.recording_sample_count < int(self.settings.realtime_min_audio_seconds * SERVER_SAMPLE_RATE):
            return None
        segment_id = self.active_segment_id or self.segment_state.realtime()
        if segment_id in self.finalizing_segment_ids or segment_id in self.finalized_segment_ids:
            return None
        audio = self._frames_to_float32(self.realtime_frames)
        if audio is None or audio.size == 0:
            return None
        self.latest_realtime_sequence += 1
        self.last_realtime_submit_at = now
        return InferenceJob(
            request_id=uuid.uuid4().hex,
            session_id=self.session_id,
            kind="realtime",
            audio=audio,
            language=self.settings.language,
            use_prompt=True,
            segment_id=segment_id,
            sequence=self.latest_realtime_sequence,
            generation=self.generation,
            created_at=time.monotonic(),
            deadline_at=time.monotonic() + (self.settings.max_realtime_queue_age_ms / 1000.0),
            initial_prompt=self.settings.initial_prompt_realtime,
            override_initial_prompt=self.domain_profile_applied,
            engine_options=(
                self.settings.realtime_transcription_engine_options
                if self.settings.realtime_transcription_engine_options is not None
                else self.settings.transcription_engine_options
            ),
            override_engine_options=self.domain_profile_applied,
        )

    def _append_prebuffer_locked(self, samples):
        if samples is None or samples.size == 0:
            return
        self.prebuffer.append(samples)
        self.prebuffer_sample_count += int(samples.size)
        max_samples = int(self.settings.pre_recording_buffer_duration * SERVER_SAMPLE_RATE)
        while max_samples >= 0 and self.prebuffer_sample_count > max_samples and self.prebuffer:
            dropped = self.prebuffer.popleft()
            self.prebuffer_sample_count -= int(dropped.size)

    def _append_recording_samples_locked(self, samples):
        if samples is None or samples.size == 0:
            return
        self.recording_frames.append(samples)
        self.recording_sample_count += int(samples.size)
        if not self.settings.realtime_transcription_enabled:
            return
        self.realtime_frames.append(samples)
        self.realtime_sample_count += int(samples.size)
        self._trim_realtime_buffer_locked()

    def _trim_realtime_buffer_locked(self):
        max_samples = max(0, int(self.settings.realtime_max_audio_seconds * SERVER_SAMPLE_RATE))
        while self.realtime_sample_count > max_samples and self.realtime_frames:
            overflow = self.realtime_sample_count - max_samples
            oldest = self.realtime_frames[0]
            if int(oldest.size) <= overflow:
                self.realtime_frames.popleft()
                self.realtime_sample_count -= int(oldest.size)
                continue
            self.realtime_frames[0] = oldest[overflow:]
            self.realtime_sample_count -= overflow

    @staticmethod
    def _frames_to_float32(frames):
        if not frames:
            return None
        audio_int16 = (
            np.asarray(frames[0], dtype=np.int16)
            if len(frames) == 1
            else np.concatenate(tuple(frames))
        )
        return audio_int16.astype(np.float32) / INT16_MAX_ABS_VALUE

    def _waiting_state_locked(self, streaming=None):
        if streaming is None:
            streaming = self.streaming
        if not streaming:
            return "idle"
        if self.settings.wake_word_enabled():
            return "wakeword_wait"
        return "listening"


class RecorderBackedRealtimeSession:
    def __init__(self, service, session_id):
        self.service = service
        self.settings = replace(service.settings)
        self.session_id = session_id
        self.segment_state = SegmentState()
        self.timeline = SegmentTimelineTracker(self.settings)
        self.lock = threading.RLock()
        self.streaming = False
        self.status = "idle"
        self.generation = 0
        self.reject_current_recording = False
        self.dropped_audio_chunks = 0
        self.rejected_audio_chunks = 0
        self.coalesced_realtime = 0
        self.stale_realtime_discarded = 0
        self.cancelled_jobs = 0
        self.realtime_submitted = 0
        self.final_submitted = 0
        self.realtime_completed = 0
        self.final_completed = 0
        self.realtime_rejected = 0
        self.final_rejected = 0
        self.forced_finalizations = 0
        self.dropped_recorded_segments = 0
        self.recording_sample_count = 0
        self._recorded_chunk_callback_seen = False
        self._force_finalize_in_progress = False
        self._wakeword_voice_window = False
        self._wakeword_followup_generation = 0
        self._recorder_wake_word_timeout_before_followup = None
        self._recorder_start_recording_before_followup = None
        self._recorder_stop_recording_before_followup = None
        self.queue_delay = {"realtime": RunningStats(), "final": RunningStats()}
        self.inference_duration = {"realtime": RunningStats(), "final": RunningStats()}
        self.total_latency = {"realtime": RunningStats(), "final": RunningStats()}
        self.domain_name = None
        self.domain_profile_applied = False
        self.recorder = self._create_recorder()
        self.text_thread = threading.Thread(
            target=self._text_worker,
            name=f"CoreSTTSessionText-{session_id}",
            daemon=True,
        )
        self.text_thread.start()

    def _create_recorder(self):
        recorder_factory = self.service.recorder_factory
        use_structured_stabilization = recorder_factory is None
        if recorder_factory is None:
            from CoreSTT import AudioToTextRecorder

            recorder_factory = AudioToTextRecorder

        callback_key = (
            "on_realtime_transcription_stabilized"
            if self.settings.realtime_callback == "stabilized"
            else "on_realtime_transcription_update"
        )
        realtime_engine = self.settings.realtime_transcription_engine
        config = {
            "spinner": False,
            "use_microphone": False,
            "model": self.settings.model,
            "realtime_model_type": self.settings.realtime_model,
            "language": self.settings.language,
            "transcription_engine": self.settings.transcription_engine,
            "realtime_transcription_engine": realtime_engine,
            "transcription_engine_options": self.settings.transcription_engine_options,
            "realtime_transcription_engine_options": (
                self.settings.realtime_transcription_engine_options
            ),
            "download_root": self.settings.download_root,
            "compute_type": self.settings.compute_type,
            "device": self.settings.device,
            "gpu_device_index": self.settings.gpu_device_index,
            "beam_size": self.settings.beam_size,
            "beam_size_realtime": self.settings.beam_size_realtime,
            "batch_size": self.settings.batch_size,
            "realtime_batch_size": self.settings.realtime_batch_size,
            "faster_whisper_vad_filter": self.settings.vad_filter_final,
            "normalize_audio": self.settings.normalize_audio,
            "enable_realtime_transcription": self.settings.realtime_transcription_enabled,
            "use_main_model_for_realtime": self.settings.use_main_model_for_realtime,
            "realtime_processing_pause": self.settings.realtime_processing_pause,
            "realtime_transcription_use_syllable_boundaries": (
                self.settings.realtime_transcription_use_syllable_boundaries
            ),
            "realtime_boundary_detector_sensitivity": (
                self.settings.realtime_boundary_detector_sensitivity
            ),
            "realtime_boundary_followup_delays": (
                self.settings.realtime_boundary_followup_delays
            ),
            "silero_sensitivity": self.settings.silero_sensitivity,
            "webrtc_sensitivity": self.settings.webrtc_sensitivity,
            "warmup_vad": self.settings.model_warmup,
            "post_speech_silence_duration": self.settings.post_speech_silence_duration,
            "min_length_of_recording": self.settings.min_length_of_recording,
            "min_gap_between_recordings": self.settings.min_gap_between_recordings,
            "early_transcription_on_silence": self.settings.early_transcription_on_silence,
            "initial_prompt": self.settings.initial_prompt,
            "initial_prompt_realtime": self.settings.initial_prompt_realtime,
            "wakeword_backend": self.settings.wakeword_backend,
            "openwakeword_model_paths": self.settings.openwakeword_model_paths,
            "openwakeword_inference_framework": self.settings.openwakeword_inference_framework,
            "wake_words": self.settings.wake_words,
            "wake_words_sensitivity": self.settings.wake_words_sensitivity,
            "wake_word_activation_delay": self.settings.wake_word_activation_delay,
            "wake_word_timeout": self.settings.wake_word_timeout,
            "wake_word_buffer_duration": self.settings.wake_word_buffer_duration,
            "pre_recording_buffer_duration": self.settings.pre_recording_buffer_duration,
            "allowed_latency_limit": self.settings.audio_queue_size,
            "handle_buffer_overflow": True,
            "on_recording_start": self._on_recording_start,
            "on_recording_stop": self._on_recording_stop,
            "on_transcription_start": self._on_transcription_start,
            "on_wakeword_detected": self._on_wakeword_detected,
            "on_wakeword_timeout": self._on_wakeword_timeout,
            "on_wakeword_detection_start": self._on_wakeword_detection_start,
            "on_wakeword_detection_end": self._on_wakeword_detection_end,
            "on_vad_start": self._on_vad_start,
            "on_vad_stop": self._on_vad_stop,
            "on_vad_detect_start": self._on_vad_detect_start,
            "on_vad_detect_stop": self._on_vad_detect_stop,
            "on_recorded_chunk": self._on_recorded_chunk,
            "no_log_file": True,
            "transcription_executor": SchedulerTranscriptionExecutor(
                self.service,
                self.session_id,
                "final",
            ),
            "realtime_transcription_executor": SchedulerTranscriptionExecutor(
                self.service,
                self.session_id,
                "realtime",
            ),
        }
        if use_structured_stabilization:
            config["on_realtime_text_stabilization_update"] = (
                self._on_realtime_stabilization_event
            )
        else:
            config[callback_key] = self._on_realtime_text
        return recorder_factory(**config)

    def start_streaming(self, domain_profile=None, domain_name=None):
        if domain_profile is not None or domain_name is not None:
            self.apply_domain_profile(domain_profile, domain_name)
        with self.lock:
            self.streaming = True
            active_domain = self.domain_name or "default"
            self.status = (
                "wakeword_wait"
                if self.settings.wake_word_enabled()
                and self.settings.wake_word_activation_delay <= 0
                else "listening"
            )
        _log_stream_started(self.session_id, active_domain)
        self.publish_status(self.status)

    def apply_domain_profile(self, profile, domain_name):
        with self.lock:
            if self.streaming:
                raise ValueError("Domain can only be changed before streaming starts.")
            profile_applied = profile is not None
            if self.domain_name == domain_name and self.domain_profile_applied == profile_applied:
                return
            self.generation += 1
            self.settings.initial_prompt = profile.initial_prompt if profile else self.settings.initial_prompt
            self.settings.initial_prompt_realtime = (
                profile.initial_prompt_realtime if profile else self.settings.initial_prompt_realtime
            )
            if profile is not None:
                self.settings.transcription_engine_options = _domain_engine_options(
                    self.settings.transcription_engine_options,
                    profile.hotwords,
                )
                self.settings.realtime_transcription_engine_options = _domain_engine_options(
                    self.settings.realtime_transcription_engine_options,
                    getattr(profile, "realtime_hotwords", profile.hotwords),
                )
            self.domain_name = domain_name
            self.domain_profile_applied = profile_applied

        old_recorder = self.recorder
        try:
            old_recorder.shutdown()
        except Exception:
            LOGGER.debug("Recorder shutdown failed during domain switch for %s", self.session_id, exc_info=True)
        if self.text_thread is not None:
            self.text_thread.join(timeout=3)
        self.recorder = self._create_recorder()
        self.text_thread = threading.Thread(
            target=self._text_worker,
            name=f"CoreSTTSessionText-{self.session_id}",
            daemon=True,
        )
        self.text_thread.start()

    def stop_streaming(self):
        with self.lock:
            self.streaming = False
            self.status = "idle"
        try:
            self.recorder.flush_buffered_audio()
            self._trim_recorded_audio_queue()
        except Exception:
            LOGGER.debug("Could not flush buffered audio for %s", self.session_id, exc_info=True)
        finally:
            self.service.deactivate_speaker(self.session_id)
        self.publish_status("idle")

    def close(self):
        with self.lock:
            self.generation += 1
            self.streaming = False
            self.status = "closed"
            self.timeline.reset()
            self._wakeword_voice_window = False
            self._wakeword_followup_generation += 1
            self._clear_recorder_followup_gate_locked()
        self.service.scheduler.cancel_session(self.session_id)
        self.service.cancel_pending_recorder_transcriptions(self.session_id)
        self.service.deactivate_speaker(self.session_id)
        try:
            self.recorder.shutdown()
        except Exception:
            LOGGER.debug("Recorder shutdown failed for %s", self.session_id, exc_info=True)
        if self.text_thread is not None:
            self.text_thread.join(timeout=3)

    def clear(self):
        with self.lock:
            self.generation += 1
            next_segment = self.segment_state.reset()
            self.timeline.reset()
            self.reject_current_recording = True
            self.recording_sample_count = 0
            self._wakeword_voice_window = False
            self._wakeword_followup_generation += 1
            self._clear_recorder_followup_gate_locked()
            self.status = self._waiting_state_locked()
        self.service.scheduler.cancel_session(self.session_id)
        self.service.cancel_pending_recorder_transcriptions(self.session_id)
        self.service.deactivate_speaker(self.session_id)
        try:
            self.recorder.abort()
        except Exception:
            LOGGER.debug("Recorder abort failed during clear for %s", self.session_id, exc_info=True)
        self.service.manager.publish_session(
            self.session_id,
            {
                "type": "clear",
                "sessionId": self.session_id,
                "nextSegmentId": next_segment,
            },
        )
        self.publish_status(self.status)

    def ingest_audio_packet(self, packet):
        samples = self.service.packet_to_server_samples(packet)
        if samples.size == 0:
            return True, None
        with self.lock:
            if not self.streaming:
                self.rejected_audio_chunks += 1
                return False, "Audio stream is stopped; send a start command before audio packets."
        try:
            self.recorder.feed_audio(samples, original_sample_rate=SERVER_SAMPLE_RATE)
        except Exception as exc:
            LOGGER.exception("Could not feed recorder audio")
            self.dropped_audio_chunks += 1
            return False, str(exc)
        warning = self._enforce_recording_duration(samples)
        if warning:
            self.service.manager.publish_session(
                self.session_id,
                {"type": "warning", "sessionId": self.session_id, "message": warning},
            )
        return True, None

    def handle_inference_result(self, result: InferenceResult):
        # Recorder-backed sessions consume scheduler results through
        # transcribe_for_recorder(); direct event routing is only used by the
        # older inline session tests.
        self.service.complete_pending_recorder_transcription(result)

    def on_job_dropped(self, job: InferenceJob, reason: str):
        if reason == "coalesced" and job.kind == "realtime":
            self.coalesced_realtime += 1
        elif reason == "stale" and job.kind == "realtime":
            self.stale_realtime_discarded += 1
        elif reason in ("cancelled", "superseded_by_final"):
            self.cancelled_jobs += 1
        self.service.fail_pending_recorder_transcription(
            job.request_id,
            f"{job.kind} transcription was {reason}",
        )

    def on_submit_result(self, job: InferenceJob, result: QueueSubmitResult):
        if result.accepted:
            if job.kind == "realtime":
                self.realtime_submitted += 1
                if result.coalesced:
                    self.coalesced_realtime += 1
            else:
                self.final_submitted += 1
            return

        if job.kind == "realtime":
            self.realtime_rejected += 1
        else:
            self.final_rejected += 1
        self.service.fail_pending_recorder_transcription(job.request_id, result.reason)

    def record_executor_result(self, result: InferenceResult):
        self.queue_delay[result.kind].record(result.queue_delay)
        self.inference_duration[result.kind].record(result.inference_duration)
        self.total_latency[result.kind].record(result.total_latency)
        if result.kind == "realtime":
            self.realtime_completed += 1
        else:
            self.final_completed += 1

    def publish_status(self, state=None):
        with self.lock:
            state = state or self.status
            self.status = state
            message = {
                "type": "status",
                "sessionId": self.session_id,
                "domain": self.domain_name,
                "state": state,
                "timestamp": time.time(),
                "activeClientId": self.session_id if self.streaming else None,
                "queueDepth": self._recorder_queue_depth(),
                "droppedChunks": self.dropped_audio_chunks,
                "coalescedRealtime": self.coalesced_realtime,
                "staleRealtimeDiscarded": self.stale_realtime_discarded,
                "activeSessions": self.service.session_count(),
                "activeSpeakers": self.service.active_speaker_count(),
                "wakeWordEnabled": self.settings.wake_word_enabled(),
                "wakeWord": {
                    "enabled": self.settings.wake_word_enabled(),
                    "backend": self.settings.wakeword_backend,
                    "wakeWords": self.settings.wake_words,
                    "state": state if str(state).startswith("wakeword") else None,
                },
            }
            message["timestampIso"] = timestamp_iso(message["timestamp"])
        self.service.manager.publish_session(self.session_id, message)

    def snapshot(self):
        with self.lock:
            state = self.status
            streaming = self.streaming
            recording = bool(getattr(self.recorder, "is_recording", False))
        return {
            "sessionId": self.session_id,
            "domain": self.domain_name,
            "streaming": streaming,
            "recording": recording,
            "state": state,
            "wakeWordEnabled": self.settings.wake_word_enabled(),
            "currentSegmentId": self.segment_state.current(),
            "currentSegment": self.timeline.snapshot(self.segment_state.current()),
            "queueDepth": self._recorder_queue_depth(),
            "recordingSeconds": self.recording_sample_count / float(SERVER_SAMPLE_RATE),
            "droppedAudioChunks": self.dropped_audio_chunks,
            "rejectedAudioChunks": self.rejected_audio_chunks,
            "coalescedRealtime": self.coalesced_realtime,
            "staleRealtimeDiscarded": self.stale_realtime_discarded,
            "cancelledJobs": self.cancelled_jobs,
            "realtimeSubmitted": self.realtime_submitted,
            "finalSubmitted": self.final_submitted,
            "realtimeCompleted": self.realtime_completed,
            "finalCompleted": self.final_completed,
            "realtimeRejected": self.realtime_rejected,
            "finalRejected": self.final_rejected,
            "forcedFinalizations": self.forced_finalizations,
            "droppedRecordedSegments": self.dropped_recorded_segments,
            "queueDelay": {
                "realtime": self.queue_delay["realtime"].snapshot_ms(),
                "final": self.queue_delay["final"].snapshot_ms(),
            },
            "inferenceDuration": {
                "realtime": self.inference_duration["realtime"].snapshot_ms(),
                "final": self.inference_duration["final"].snapshot_ms(),
            },
            "totalLatency": {
                "realtime": self.total_latency["realtime"].snapshot_ms(),
                "final": self.total_latency["final"].snapshot_ms(),
            },
        }

    def _text_worker(self):
        while not self.service.stop_event.is_set():
            with self.lock:
                text_generation = self.generation
            try:
                text = self.recorder.text()
            except Exception as exc:
                if getattr(self.recorder, "is_shut_down", False):
                    break
                LOGGER.exception("Session recorder text loop failed")
                self.service.manager.publish_session(
                    self.session_id,
                    {
                        "type": "error",
                        "sessionId": self.session_id,
                        "message": str(exc),
                        "where": "recorder",
                    },
                )
                time.sleep(0.1)
                continue

            if getattr(self.recorder, "is_shut_down", False):
                break
            text = (text or "").strip()
            if not text:
                continue
            self._publish_final_text(text, text_generation)

    def _publish_final_text(self, text, text_generation):
        with self.lock:
            if text_generation != self.generation:
                return False
            segment_id = self.segment_state.final()
            streaming = self.streaming
            segment = self._timeline_snapshot(segment_id)
        timestamp = time.time()
        payload = {
            "type": "final",
            "sessionId": self.session_id,
            "segmentId": segment_id,
            "text": text,
            "timestamp": timestamp,
            "timestampIso": timestamp_iso(timestamp),
        }
        if segment is not None:
            payload["segment"] = segment
            payload.update(segment_text_fields(segment))
        self.service.manager.publish_session(
            self.session_id,
            payload,
        )
        self._publish_timeline_event(
            "final_transcript",
            timestamp=timestamp,
            segment_id=segment_id,
            segment=segment,
            text=text,
        )
        self.publish_status(self._waiting_state_locked(streaming))
        return True

    def _on_realtime_text(self, text):
        with self.lock:
            if not self.settings.realtime_transcription_enabled:
                return
            if self.reject_current_recording:
                return
            segment_id = self.segment_state.realtime()
            segment = self._timeline_snapshot(segment_id)
        text = (text or "").strip()
        if not text:
            return
        timestamp = time.time()
        payload = {
            "type": "realtime",
            "sessionId": self.session_id,
            "segmentId": segment_id,
            "text": text,
            "timestamp": timestamp,
            "timestampIso": timestamp_iso(timestamp),
        }
        if segment is not None:
            payload["segment"] = segment
            payload.update(segment_text_fields(segment))
        self.service.manager.publish_session(
            self.session_id,
            payload,
        )
        self._publish_timeline_event(
            "realtime_transcript",
            timestamp=timestamp,
            segment_id=segment_id,
            segment=segment,
            text=text,
        )

    def _on_realtime_stabilization_event(self, event):
        with self.lock:
            if not self.settings.realtime_transcription_enabled:
                return
            if self.reject_current_recording:
                return

        raw_text = (getattr(event, "raw_observation_text", "") or "").strip()
        committed_stable_text = getattr(event, "stable_text", "") or ""
        unstable_text = getattr(event, "unstable_text", "") or ""
        display_text = (getattr(event, "display_text", "") or "").strip()
        consensus_text = getattr(event, "consensus_text", "") or committed_stable_text
        consensus_unstable_text = getattr(event, "consensus_unstable_text", "") or ""
        consensus_display_text = (
            getattr(event, "consensus_display_text", "") or display_text
        ).strip()
        if (
            not raw_text
            and not display_text
            and not committed_stable_text
            and not unstable_text
        ):
            return

        segment_id = getattr(event, "segment_id", None)
        if segment_id is None:
            segment_id = self.segment_state.realtime()

        text = (
            display_text
            if self.settings.realtime_callback == "stabilized"
            else raw_text or display_text
        )
        timing = getattr(event, "timing", None)
        timestamp = time.time()
        segment = self._timeline_snapshot(segment_id)
        payload = {
            "type": "realtime",
            "sessionId": self.session_id,
            "segmentId": segment_id,
            "recordingId": getattr(event, "recording_id", None),
            "sequence": getattr(event, "sequence", None),
            "text": text,
            "rawText": raw_text,
            "displayText": display_text or raw_text,
            "stableText": committed_stable_text,
            "stableDelta": getattr(event, "stable_delta", "") or "",
            "unstableText": unstable_text,
            "committedStableText": committed_stable_text,
            "committedStableDelta": getattr(event, "stable_delta", "") or "",
            "visualStableText": committed_stable_text,
            "visualUnstableText": unstable_text,
            "consensusText": consensus_text,
            "consensusUnstableText": consensus_unstable_text,
            "consensusDisplayText": consensus_display_text,
            "publicConsensusAligned": bool(
                getattr(event, "public_consensus_aligned", True)
            ),
            "internalRevision": bool(getattr(event, "internal_revision", False)),
            "isOutlier": bool(getattr(event, "is_outlier", False)),
            "stablePrefixConflict": bool(
                getattr(event, "stable_prefix_conflict", False)
            ),
            "commitReason": getattr(event, "commit_reason", None),
            "stableNormalizedOffset": getattr(
                event,
                "stable_normalized_offset",
                None,
            ),
            "timestamp": timestamp,
            "timestampIso": timestamp_iso(timestamp),
        }
        if timing is not None:
            payload["timing"] = asdict(timing)
        if segment is not None:
            payload["segment"] = segment
            payload.update(segment_text_fields(segment))

        self.service.manager.publish_session(self.session_id, payload)
        self._publish_timeline_event(
            "realtime_transcript",
            timestamp=timestamp,
            segment_id=segment_id,
            segment=segment,
            text=text,
            sequence=payload.get("sequence"),
        )

    def _on_recording_start(self):
        segment = None
        segment_id = None
        with self.lock:
            self._wakeword_followup_generation += 1
            self._clear_recorder_followup_gate_locked()
            if not self.service.try_activate_speaker(self.session_id):
                self.reject_current_recording = True
                self.recording_sample_count = 0
                self._force_finalize_in_progress = False
                self._wakeword_voice_window = False
                self.rejected_audio_chunks += 1
                self.service.manager.publish_session(
                    self.session_id,
                    {
                        "type": "warning",
                        "sessionId": self.session_id,
                        "message": "Server active speaker limit reached; recording will be ignored.",
                    },
                )
            else:
                self.reject_current_recording = False
                self.recording_sample_count = 0
                self._force_finalize_in_progress = False
                self._wakeword_voice_window = False
                segment_id = self.segment_state.current()
                segment = self.timeline.mark_recording_started(segment_id)
        if segment is not None:
            self._publish_timeline_event(
                "recording_started",
                timestamp=segment.get("recordingStartedAt"),
                segment_id=segment_id,
                segment=segment,
                preRecordingBuffer=segment.get("preRecordingBuffer"),
            )
        self.publish_status("recording")

    def _on_recording_stop(self):
        self._trim_recorded_audio_queue()
        segment = None
        segment_id = None
        with self.lock:
            segment_id = self.segment_state.current()
            duration_seconds = (
                self.recording_sample_count / float(SERVER_SAMPLE_RATE)
                if self.recording_sample_count
                else None
            )
            segment = self.timeline.mark_recording_ended(
                "recording_stop",
                segment_id=segment_id,
                actual_duration_seconds=duration_seconds,
            )
            self.recording_sample_count = 0
            self._force_finalize_in_progress = False
            self._wakeword_voice_window = False
        self.service.deactivate_speaker(self.session_id)
        if segment is not None:
            self._publish_timeline_event(
                "recording_ended",
                timestamp=segment.get("recordingEndedAt"),
                segment_id=segment_id,
                segment=segment,
                durationSeconds=segment.get("durationSeconds"),
                reason=segment.get("endReason"),
            )
        self._start_wakeword_followup_window()
        self.publish_status(self._waiting_state_locked())

    def _on_transcription_start(self, *_):
        segment_id = self.segment_state.current()
        self._publish_timeline_event(
            "transcription_started",
            segment_id=segment_id,
            segment=self._timeline_snapshot(segment_id),
        )
        self.publish_status("transcribing")
        with self.lock:
            return True if self.reject_current_recording else False

    def _waiting_state_locked(self, streaming=None):
        if streaming is None:
            streaming = self.streaming
        if not streaming:
            return "idle"
        if self.settings.wake_word_enabled():
            if self._wakeword_voice_window:
                return "wakeword_detected"
            return "wakeword_wait"
        return "listening"

    def _start_wakeword_followup_window(self):
        try:
            window = max(0.0, float(self.settings.wake_word_followup_window))
        except (TypeError, ValueError):
            window = 0.0
        if not self.settings.wake_word_enabled() or window <= 0:
            return False

        with self.lock:
            if not self.streaming or self.reject_current_recording:
                return False
            self._wakeword_voice_window = True
            self._wakeword_followup_generation += 1
            generation = self._wakeword_followup_generation
            recorder = self.recorder
            try:
                if self._recorder_wake_word_timeout_before_followup is None:
                    self._recorder_wake_word_timeout_before_followup = getattr(
                        recorder,
                        "wake_word_timeout",
                        None,
                    )
                if self._recorder_start_recording_before_followup is None:
                    self._recorder_start_recording_before_followup = getattr(
                        recorder,
                        "start_recording_on_voice_activity",
                        None,
                    )
                if self._recorder_stop_recording_before_followup is None:
                    self._recorder_stop_recording_before_followup = getattr(
                        recorder,
                        "stop_recording_on_voice_deactivity",
                        None,
                    )
                recorder.wakeword_detected = True
                recorder.wake_word_detect_time = time.time()
                recorder.wake_word_timeout = window
                recorder.start_recording_on_voice_activity = True
                recorder.stop_recording_on_voice_deactivity = True
            except Exception:
                self._wakeword_voice_window = False
                self._clear_recorder_followup_gate_locked()
                LOGGER.debug(
                    "Could not arm wake-word follow-up window for %s",
                    self.session_id,
                    exc_info=True,
                )
                return False

        self._publish_timeline_event(
            "wakeword_followup_started",
            durationSeconds=window,
        )
        threading.Thread(
            target=self._wakeword_followup_timeout_worker,
            args=(generation, window),
            name=f"CoreSTTSessionWakeFollowup-{self.session_id}",
            daemon=True,
        ).start()
        return True

    def _wakeword_followup_timeout_worker(self, generation, window):
        time.sleep(window)
        self._finish_wakeword_followup(generation)

    def _finish_wakeword_followup(self, generation=None):
        with self.lock:
            if generation is not None and generation != self._wakeword_followup_generation:
                return False
            if not self._wakeword_voice_window:
                return False
            if bool(getattr(self.recorder, "is_recording", False)):
                return False
            self._wakeword_voice_window = False
            self._wakeword_followup_generation += 1
            self._clear_recorder_followup_gate_locked()
            streaming = self.streaming

        self._publish_timeline_event("wakeword_followup_timeout")
        self.publish_status("wakeword_wait" if streaming else "idle")
        return True

    def _clear_recorder_followup_gate_locked(self):
        recorder = self.recorder
        try:
            recorder.wakeword_detected = False
            recorder.wake_word_detect_time = 0
            if self._recorder_wake_word_timeout_before_followup is not None:
                recorder.wake_word_timeout = self._recorder_wake_word_timeout_before_followup
            if self._recorder_start_recording_before_followup is not None:
                recorder.start_recording_on_voice_activity = (
                    self._recorder_start_recording_before_followup
                )
            if self._recorder_stop_recording_before_followup is not None:
                recorder.stop_recording_on_voice_deactivity = (
                    self._recorder_stop_recording_before_followup
                )
        except Exception:
            LOGGER.debug(
                "Could not clear wake-word follow-up gate for %s",
                self.session_id,
                exc_info=True,
            )
        self._recorder_wake_word_timeout_before_followup = None
        self._recorder_start_recording_before_followup = None
        self._recorder_stop_recording_before_followup = None

    def _on_vad_start(self):
        self.publish_status(self._voice_or_waiting_state())

    def _on_vad_stop(self):
        self.publish_status(self._silence_or_waiting_state())

    def _on_vad_detect_start(self):
        self.publish_status(self._voice_or_waiting_state())

    def _on_vad_detect_stop(self):
        self.publish_status(self._silence_or_waiting_state())

    def _voice_or_waiting_state(self):
        with self.lock:
            if not self.settings.wake_word_enabled():
                return "voice"
            if self._wakeword_voice_window:
                return "voice"
            return self._waiting_state_locked()

    def _silence_or_waiting_state(self):
        with self.lock:
            if not self.settings.wake_word_enabled():
                return "silence"
            if self._wakeword_voice_window:
                return "silence"
            return self._waiting_state_locked()

    def _on_wakeword_detection_start(self):
        with self.lock:
            self._wakeword_voice_window = False
            self._wakeword_followup_generation += 1
            self._clear_recorder_followup_gate_locked()
        event = self.timeline.mark_wakeword_wait_started()
        self._publish_timeline_event(
            "wakeword_wait_started",
            wakeWord=event.get("wakeWord"),
        )
        self.publish_status("wakeword_wait")

    def _on_wakeword_detection_end(self):
        event = self.timeline.mark_wakeword_wait_ended()
        self._publish_timeline_event(
            "wakeword_wait_ended",
            wakeWord=event.get("wakeWord"),
        )

    def _on_wakeword_detected(self):
        with self.lock:
            self._wakeword_voice_window = True
            self._wakeword_followup_generation += 1
        event = self.timeline.mark_wakeword_detected()
        self._publish_timeline_event(
            "wakeword_detected",
            wakeWord=event.get("wakeWord"),
        )
        self.publish_status("wakeword_detected")

    def _on_wakeword_timeout(self):
        with self.lock:
            self._wakeword_voice_window = False
            self._wakeword_followup_generation += 1
            self._clear_recorder_followup_gate_locked()
        event = self.timeline.mark_wakeword_timeout()
        self._publish_timeline_event(
            "wakeword_timeout",
            wakeWord=event.get("wakeWord"),
        )
        self.publish_status("wakeword_timeout")

    def _publish_timeline_event(
        self,
        event,
        *,
        timestamp=None,
        segment_id=None,
        segment=None,
        **fields,
    ):
        if not hasattr(self, "timeline"):
            return
        timestamp = time.time() if timestamp is None else float(timestamp)
        payload = {
            "type": "timeline",
            "sessionId": self.session_id,
            "domain": self.domain_name,
            "event": event,
            "timestamp": timestamp,
            "timestampIso": timestamp_iso(timestamp),
        }
        if segment_id is not None:
            payload["segmentId"] = segment_id
        if segment is not None:
            payload["segment"] = segment
        for key, value in fields.items():
            if value is not None:
                payload[key] = value
        self.service.manager.publish_session(self.session_id, payload)

    def _timeline_snapshot(self, segment_id=None):
        timeline = getattr(self, "timeline", None)
        if timeline is None:
            return None
        return timeline.snapshot(segment_id)

    def _recorder_queue_depth(self):
        depth = 0
        try:
            depth += int(self.recorder.audio_queue.qsize())
        except Exception:
            pass
        try:
            depth += int(self.recorder.recorded_audio_queue.qsize())
        except Exception:
            pass
        return depth

    def _enforce_recording_duration(self, samples):
        if self._recorded_chunk_callback_seen:
            return None

        max_samples = int(self.settings.max_audio_queue_seconds_per_session * SERVER_SAMPLE_RATE)
        if max_samples <= 0:
            return None

        should_finalize = False
        with self.lock:
            if bool(getattr(self.recorder, "is_recording", False)):
                self.recording_sample_count += int(samples.size)
                should_finalize = self.recording_sample_count >= max_samples

        if not should_finalize:
            return None

        self._force_finalize_after_limit()
        return None

    def _on_recorded_chunk(self, data):
        self._recorded_chunk_callback_seen = True
        max_samples = int(self.settings.max_audio_queue_seconds_per_session * SERVER_SAMPLE_RATE)
        if max_samples <= 0:
            return
        if not bool(getattr(self.recorder, "is_recording", False)):
            return

        try:
            sample_count = len(data) // 2
        except Exception:
            return

        should_finalize = False
        with self.lock:
            self.recording_sample_count += int(sample_count)
            if (
                self.recording_sample_count >= max_samples
                and not self._force_finalize_in_progress
            ):
                self._force_finalize_in_progress = True
                should_finalize = True

        if should_finalize:
            threading.Thread(
                target=self._force_finalize_after_limit,
                name=f"CoreSTTSessionForceFinalize-{self.session_id}",
                daemon=True,
            ).start()

    def _force_finalize_after_limit(self):
        finalized = False
        try:
            finalized = bool(self.recorder.flush_buffered_audio())
            self._trim_recorded_audio_queue()
        except Exception:
            LOGGER.debug("Could not force-finalize long recording for %s", self.session_id, exc_info=True)
        finally:
            with self.lock:
                self.recording_sample_count = 0
                self._force_finalize_in_progress = False
                if finalized:
                    self.forced_finalizations += 1

        if not finalized:
            return
        self.service.deactivate_speaker(self.session_id)
        self.service.manager.publish_session(
            self.session_id,
            {
                "type": "warning",
                "sessionId": self.session_id,
                "message": "Maximum per-session audio buffer reached; finalized the current segment.",
            },
        )

    def _trim_recorded_audio_queue(self):
        queue_obj = getattr(self.recorder, "recorded_audio_queue", None)
        if queue_obj is None:
            return 0

        max_pending = max(0, int(self.settings.max_final_queue_depth_per_session))
        dropped = 0
        while True:
            try:
                if queue_obj.qsize() <= max_pending:
                    break
                queue_obj.get_nowait()
                dropped += 1
            except Exception:
                break

        if dropped:
            with self.lock:
                self.dropped_recorded_segments += dropped
                self.final_rejected += dropped
            self.service.manager.publish_session(
                self.session_id,
                {
                    "type": "warning",
                    "sessionId": self.session_id,
                    "message": (
                        "Final transcription backlog exceeded the per-session limit; "
                        f"dropped {dropped} queued recorded segment(s)."
                    ),
                },
            )
        return dropped


class SessionStore:
    def __init__(self, settings: ServerSettings):
        self.settings = settings
        self._lock = threading.Lock()
        self._sessions: Dict[str, RealtimeSession] = {}
        self._reserved_session_ids = set()
        self._active_speakers = set()
        self.rejected_sessions = 0

    def reserve(self, session_id):
        with self._lock:
            if session_id in self._sessions or session_id in self._reserved_session_ids:
                self.rejected_sessions += 1
                return False
            if self._session_slots_used_locked() >= self.settings.max_sessions:
                self.rejected_sessions += 1
                return False
            self._reserved_session_ids.add(session_id)
            return True

    def add(self, session):
        with self._lock:
            reserved = session.session_id in self._reserved_session_ids
            if session.session_id in self._sessions:
                self._reserved_session_ids.discard(session.session_id)
                self.rejected_sessions += 1
                return False
            if not reserved and self._session_slots_used_locked() >= self.settings.max_sessions:
                self.rejected_sessions += 1
                return False
            self._reserved_session_ids.discard(session.session_id)
            self._sessions[session.session_id] = session
            return True

    def can_accept(self):
        with self._lock:
            if self._session_slots_used_locked() >= self.settings.max_sessions:
                self.rejected_sessions += 1
                return False
            return True

    def release_reservation(self, session_id):
        with self._lock:
            self._reserved_session_ids.discard(session_id)

    def remove(self, session_id):
        with self._lock:
            session = self._sessions.pop(session_id, None)
            self._reserved_session_ids.discard(session_id)
            self._active_speakers.discard(session_id)
            return session

    def remove_all(self):
        with self._lock:
            sessions = list(self._sessions.values())
            self._sessions.clear()
            self._reserved_session_ids.clear()
            self._active_speakers.clear()
            return sessions

    def get(self, session_id):
        with self._lock:
            return self._sessions.get(session_id)

    def try_activate_speaker(self, session_id):
        with self._lock:
            if session_id in self._active_speakers:
                return True
            if len(self._active_speakers) >= self.settings.max_active_speakers:
                return False
            self._active_speakers.add(session_id)
            return True

    def deactivate_speaker(self, session_id):
        with self._lock:
            self._active_speakers.discard(session_id)

    def count(self):
        with self._lock:
            return len(self._sessions)

    def active_speaker_count(self):
        with self._lock:
            return len(self._active_speakers)

    def snapshots(self):
        with self._lock:
            sessions = list(self._sessions.values())
            rejected = self.rejected_sessions
            active_speakers = len(self._active_speakers)
            reserved_sessions = len(self._reserved_session_ids)
        return {
            "activeSessions": len(sessions),
            "activeSpeakers": active_speakers,
            "pendingSessionAdmissions": reserved_sessions,
            "rejectedSessions": rejected,
            "sessions": {session.session_id: session.snapshot() for session in sessions},
        }

    def _session_slots_used_locked(self):
        return len(self._sessions) + len(self._reserved_session_ids)


class CoreSTTService:
    def __init__(
        self,
        settings: ServerSettings,
        manager: ConnectionManager,
        scheduler_factory: Optional[Callable[..., Any]] = None,
        recorder_factory: Optional[Callable[..., Any]] = None,
    ):
        self.settings = settings
        self.manager = manager
        self.ready = threading.Event()
        self.stop_event = threading.Event()
        self.sessions = SessionStore(settings)
        self.startup_errors = []
        self._pending_recorder_results = {}
        self._pending_recorder_lock = threading.Lock()
        self.recorder_factory = recorder_factory
        self.resource_monitor = ResourceMonitor(settings)
        self.resource_thread = None
        self.domain_profiles_path = self._resolve_domain_profiles_path(
            settings.domain_profiles_path
        )
        self.domain_profiles_lock = threading.RLock()
        self.domain_profiles = load_domain_profiles(
            self.domain_profiles_path
        )
        factory = scheduler_factory or InferenceScheduler
        if factory is InferenceScheduler:
            self.scheduler = factory(
                settings,
                self._on_inference_result,
                self._on_scheduler_drop,
                self._on_scheduler_error,
                self.resource_snapshot,
            )
        else:
            self.scheduler = factory(
                settings,
                self._on_inference_result,
                self._on_scheduler_drop,
                self._on_scheduler_error,
            )
        self.ready_thread = None

    @staticmethod
    def _resolve_domain_profiles_path(path):
        if not path:
            return None
        profile_path = Path(path)
        if profile_path.is_absolute():
            return profile_path
        return Path(__file__).resolve().parent / profile_path

    def start(self, loop):
        self.manager.bind_loop(loop)
        self.scheduler.start()
        self.ready_thread = threading.Thread(
            target=self._ready_worker,
            name="CoreSTTServerReady",
            daemon=True,
        )
        self.ready_thread.start()
        if self.settings.resource_monitoring_enabled:
            self.resource_thread = threading.Thread(
                target=self._resource_log_worker,
                name="CoreSTTResourceMonitor",
                daemon=True,
            )
            self.resource_thread.start()

    def stop(self):
        self.stop_event.set()
        for session in self.sessions.remove_all():
            session.close()
        self.scheduler.stop()
        if self.ready_thread is not None:
            self.ready_thread.join(timeout=5)
        if self.resource_thread is not None:
            self.resource_thread.join(timeout=5)

    def admit_session(self, session_id):
        if not self.sessions.reserve(session_id):
            return None
        session = None
        try:
            use_recorder_backed = (
                self.settings.use_recorder_backed_realtime_session
                or self.recorder_factory is not None
            )
            session_type = (
                RecorderBackedRealtimeSession if use_recorder_backed else RealtimeSession
            )
            session = session_type(self, session_id)
            if not self.sessions.add(session):
                session.close()
                return None
            return session
        except Exception:
            self.sessions.release_reservation(session_id)
            if session is not None:
                session.close()
            raise

    def remove_session(self, session_id):
        session = self.sessions.remove(session_id)
        if session is not None:
            session.close()

    def submit_inference_job(self, job: InferenceJob):
        result = self.scheduler.submit(job)
        session = self.sessions.get(job.session_id)
        if session is not None:
            session.on_submit_result(job, result)
        return result

    def try_activate_speaker(self, session_id):
        return self.sessions.try_activate_speaker(session_id)

    def deactivate_speaker(self, session_id):
        self.sessions.deactivate_speaker(session_id)

    def session_count(self):
        return self.sessions.count()

    def domain_profile_names(self):
        with self.domain_profiles_lock:
            return self.domain_profiles.names()

    def domain_profiles_payload(self):
        with self.domain_profiles_lock:
            return {
                "profiles": self.domain_profiles.to_dict(),
                "domainProfiles": self.domain_profiles.names(),
            }

    def _domain_profiles_updated_message(self):
        payload = self.domain_profiles_payload()
        return {
            "type": "domain_profiles_updated",
            "domainProfiles": payload["domainProfiles"],
            "profiles": payload["profiles"],
        }

    def update_domain_profile(self, name, profile_data):
        with self.domain_profiles_lock:
            profile = self.domain_profiles.upsert(name, profile_data)
            save_domain_profiles(self.domain_profiles_path, self.domain_profiles)
            result = profile.to_dict()
        self.manager.publish_all(self._domain_profiles_updated_message())
        return result

    def delete_domain_profile(self, name):
        with self.domain_profiles_lock:
            deleted = self.domain_profiles.delete(name)
            if not deleted:
                raise ValueError(f"Unknown domain profile: {name}")
            save_domain_profiles(self.domain_profiles_path, self.domain_profiles)
        self.manager.publish_all(self._domain_profiles_updated_message())
        return self.domain_profiles_payload()

    def resolve_domain_profile(self, requested_domain):
        domain_name = requested_domain if requested_domain is not None else self.settings.default_domain
        with self.domain_profiles_lock:
            if domain_name:
                selected_profile = self.domain_profiles.get(domain_name)
                if selected_profile is None:
                    raise ValueError(f"Unknown domain profile: {domain_name}")
            profile = compose_domain_profile(self.domain_profiles, domain_name)
        if domain_name and profile is None:
            raise ValueError(f"Unknown domain profile: {domain_name}")
        return str(domain_name) if domain_name else None, profile

    def active_speaker_count(self):
        return self.sessions.active_speaker_count()

    def packet_to_server_samples(self, packet):
        if len(packet.audio) > self.settings.max_audio_packet_bytes:
            raise AudioPacketError("audio packet is too large")

        sample_rate = require_positive_int(packet.metadata, "sampleRate")
        channels = packet.metadata.get("channels", 1)
        if isinstance(channels, bool) or not isinstance(channels, int) or channels <= 0:
            raise AudioPacketError("audio packet metadata field 'channels' must be a positive integer")
        if channels > 8:
            raise AudioPacketError("audio packet metadata field 'channels' must be at most 8")
        audio_format = packet.metadata.get("format", "pcm_s16le")
        if audio_format != "pcm_s16le":
            raise AudioPacketError("only pcm_s16le audio packets are supported")
        frame_width = channels * 2
        if len(packet.audio) % frame_width:
            raise AudioPacketError("pcm_s16le audio packet is not aligned to whole frames")
        if "frames" in packet.metadata:
            expected_frames = require_positive_int(packet.metadata, "frames")
            expected_bytes = expected_frames * frame_width
            if len(packet.audio) != expected_bytes:
                raise AudioPacketError(
                    "audio packet metadata field 'frames' does not match payload length"
                )

        samples = np.frombuffer(packet.audio, dtype=np.int16)
        if channels > 1:
            usable = len(samples) - (len(samples) % channels)
            if usable <= 0:
                return np.array([], dtype=np.int16)
            samples = samples[:usable].reshape(-1, channels).mean(axis=1).astype(np.int16)
        return resample_int16(samples, sample_rate, SERVER_SAMPLE_RATE)

    def metrics(self):
        data = self.sessions.snapshots()
        data["ready"] = self.ready.is_set()
        data["ok"] = self.ready.is_set() and self.scheduler.healthy()
        data["scheduler"] = self.scheduler.snapshot()
        data["limits"] = self.limits_dict()
        data["settings"] = self.settings.public_dict()
        data["startupErrors"] = list(self.startup_errors)
        data["resources"] = self.resource_snapshot()
        data["thresholds"] = DIAGNOSTIC_THRESHOLDS
        data["diagnostics"] = diagnose_bottleneck(data)
        return data

    def resource_snapshot(self):
        if not self.settings.resource_monitoring_enabled:
            return {
                "timestamp": time.time(),
                "process": {"available": False, "reason": "resource_monitoring_disabled"},
                "system": {"available": False, "reason": "resource_monitoring_disabled"},
                "cuda": {"available": False, "reason": "resource_monitoring_disabled"},
            }
        return self.resource_monitor.snapshot()

    def _resource_log_worker(self):
        while not self.stop_event.wait(
            max(1, int(self.settings.resource_log_interval_seconds))
        ):
            self._log_resource_snapshot("periodic")

    def _log_resource_snapshot(self, reason):
        resources = self.resource_snapshot()
        process = resources.get("process") or {}
        system = resources.get("system") or {}
        cuda = resources.get("cuda") or {}
        LOGGER.info(
            "resources reason=%s cpu_percent=%s process_cpu_percent=%s rss_mb=%s "
            "system_memory_percent=%s thread_count=%s cuda_available=%s "
            "cuda_allocated_mb=%s cuda_reserved_mb=%s cuda_free_mb=%s "
            "cuda_total_mb=%s cuda_memory_pressure=%s",
            reason,
            system.get("cpuPercent"),
            process.get("cpuPercent"),
            process.get("rssMb"),
            system.get("memoryPercent"),
            process.get("threadCount"),
            cuda.get("available"),
            cuda.get("allocatedMb"),
            cuda.get("reservedMb"),
            cuda.get("freeMb"),
            cuda.get("totalMb"),
            cuda.get("memoryPressure"),
        )

    def limits_dict(self):
        return {
            "maxSessions": self.settings.max_sessions,
            "maxActiveSpeakers": self.settings.max_active_speakers,
            "maxAudioQueueSecondsPerSession": self.settings.max_audio_queue_seconds_per_session,
            "maxRealtimeQueueAgeMs": self.settings.max_realtime_queue_age_ms,
            "maxFinalQueueDepthPerSession": self.settings.max_final_queue_depth_per_session,
            "maxGlobalInferenceQueueDepth": self.settings.max_global_inference_queue_depth,
            "realtimeDegradationThresholdMs": self.settings.realtime_degradation_threshold_ms,
        }

    def runtime_settings_contract(self):
        return runtime_settings_contract()

    def update_settings(self, updates):
        applied = {}
        rejected = {}
        if not isinstance(updates, dict):
            raise ValueError("settings update must be a JSON object")

        for name, value in updates.items():
            if name in STARTUP_ONLY_SETTINGS:
                rejected[name] = {
                    "reason": "startup_only",
                    "message": "This setting requires a server restart because shared resources are already initialized.",
                }
                continue
            if name not in ACTIVE_RUNTIME_SETTINGS and name not in NEW_SESSION_RUNTIME_SETTINGS:
                rejected[name] = {
                    "reason": "unknown",
                    "message": "Unknown or unsupported server setting.",
                }
                continue
            try:
                coerced = coerce_setting_value(name, value)
            except ValueError as exc:
                rejected[name] = {
                    "reason": "invalid_value",
                    "message": str(exc),
                }
                continue
            setattr(self.settings, name, coerced)
            applied[name] = {
                "value": coerced,
                "appliesTo": (
                    "active_sessions"
                    if name in ACTIVE_RUNTIME_SETTINGS
                    else "new_sessions"
                ),
            }

        return {
            "applied": applied,
            "rejected": rejected,
            "settings": self.settings.public_dict(),
            "runtimeSettings": self.runtime_settings_contract(),
        }

    def transcribe_for_recorder(self, session_id, kind, audio, language, use_prompt):
        from CoreSTT.transcription_engines import TranscriptionResult

        session = self.sessions.get(session_id)
        if session is None:
            return TranscriptionResult(text="")
        if kind == "realtime" and not session.settings.realtime_transcription_enabled:
            return TranscriptionResult(text="")

        generation = getattr(session, "generation", 0)
        request_id = uuid.uuid4().hex
        holder = {
            "event": threading.Event(),
            "result": None,
            "error": None,
            "sessionId": session_id,
            "generation": generation,
        }
        with self._pending_recorder_lock:
            self._pending_recorder_results[request_id] = holder

        job = InferenceJob(
            request_id=request_id,
            session_id=session_id,
            kind=kind,
            audio=audio,
            language=language,
            use_prompt=use_prompt,
            segment_id=session.segment_state.current(),
            sequence=0,
            generation=generation,
            created_at=time.monotonic(),
            initial_prompt=(
                session.settings.initial_prompt_realtime
                if kind == "realtime"
                else session.settings.initial_prompt
            ),
            override_initial_prompt=session.domain_profile_applied,
            engine_options=(
                session.settings.realtime_transcription_engine_options
                if kind == "realtime"
                and session.settings.realtime_transcription_engine_options is not None
                else session.settings.transcription_engine_options
            ),
            override_engine_options=session.domain_profile_applied,
            deadline_at=(
                time.monotonic() + (self.settings.max_realtime_queue_age_ms / 1000.0)
                if kind == "realtime"
                else None
            ),
        )

        submit_result = self.submit_inference_job(job)
        if not submit_result.accepted:
            self._pop_pending_recorder_result(request_id)
            raise RuntimeError(submit_result.reason)

        while not holder["event"].wait(timeout=0.1):
            current_session = self.sessions.get(session_id)
            if (
                self.stop_event.is_set()
                or current_session is None
                or getattr(current_session, "generation", generation) != generation
            ):
                self._pop_pending_recorder_result(request_id)
                return TranscriptionResult(text="")

        self._pop_pending_recorder_result(request_id)
        current_session = self.sessions.get(session_id)
        if current_session is None or getattr(current_session, "generation", generation) != generation:
            return TranscriptionResult(text="")

        if holder["error"]:
            raise RuntimeError(holder["error"])

        result = holder["result"]
        if result is None:
            return TranscriptionResult(text="")
        if result.error:
            raise RuntimeError(result.error)

        current_session.record_executor_result(result)
        return TranscriptionResult(text=result.text)

    def complete_pending_recorder_transcription(self, result: InferenceResult):
        with self._pending_recorder_lock:
            holder = self._pending_recorder_results.get(result.request_id)
        if holder is None:
            return False
        holder["result"] = result
        holder["event"].set()
        return True

    def fail_pending_recorder_transcription(self, request_id, error):
        with self._pending_recorder_lock:
            holder = self._pending_recorder_results.get(request_id)
        if holder is None:
            return False
        holder["error"] = error
        holder["event"].set()
        return True

    def cancel_pending_recorder_transcriptions(self, session_id):
        with self._pending_recorder_lock:
            pending = [
                (request_id, holder)
                for request_id, holder in self._pending_recorder_results.items()
                if holder["sessionId"] == session_id
            ]
        for request_id, holder in pending:
            holder["error"] = "session was cancelled"
            holder["event"].set()
            self._pop_pending_recorder_result(request_id)

    def _pop_pending_recorder_result(self, request_id):
        with self._pending_recorder_lock:
            return self._pending_recorder_results.pop(request_id, None)

    def _ready_worker(self):
        self.scheduler.wait_ready()
        self.ready.set()
        ready_message = {
            "type": "ready",
            "settings": self.settings.public_dict(),
            "limits": self.limits_dict(),
            "domainProfiles": self.domain_profile_names(),
            "runtimeSettings": self.runtime_settings_contract(),
            "ok": self.scheduler.healthy(),
        }
        self.manager.publish_all(ready_message)
        if self.settings.resource_monitoring_enabled:
            self._log_resource_snapshot("startup")
        if self.startup_errors:
            for error in self.startup_errors:
                self.manager.publish_all(error)

    def _on_inference_result(self, result: InferenceResult):
        if self.complete_pending_recorder_transcription(result):
            return
        session = self.sessions.get(result.session_id)
        if session is not None:
            session.handle_inference_result(result)

    def _on_scheduler_drop(self, job: InferenceJob, reason: str, lane: str):
        session = self.sessions.get(job.session_id)
        if session is not None:
            session.on_job_dropped(job, reason)
        else:
            self.fail_pending_recorder_transcription(
                job.request_id,
                f"{job.kind} transcription was {reason}",
            )

    def _on_scheduler_error(self, lane, exc):
        message = {
            "type": "error",
            "message": str(exc),
            "where": f"{lane}_engine",
        }
        self.startup_errors.append(message)
        self.manager.publish_all(message)


def load_fastapi():
    try:
        from fastapi import FastAPI, WebSocket, WebSocketDisconnect
        from fastapi.responses import HTMLResponse, JSONResponse
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            "FastAPI server dependencies are missing. Install them with "
            "'python -m pip install -r requirements.txt'."
        ) from exc
    return FastAPI, WebSocket, WebSocketDisconnect, HTMLResponse, JSONResponse


def create_app(settings: Optional[ServerSettings] = None, scheduler_factory=None, recorder_factory=None):
    FastAPI, WebSocket, WebSocketDisconnect, HTMLResponse, JSONResponse = load_fastapi()
    from contextlib import asynccontextmanager
    from CoreSTT.transcription_engines import get_supported_transcription_engines

    settings = settings or ServerSettings()
    manager = ConnectionManager()
    service = CoreSTTService(
        settings,
        manager,
        scheduler_factory=scheduler_factory,
        recorder_factory=recorder_factory,
    )

    @asynccontextmanager
    async def lifespan(app):
        service.start(asyncio.get_running_loop())
        yield
        service.stop()

    app = FastAPI(
        title="CoreSTT FastAPI Server",
        version="2.0.0",
        lifespan=lifespan,
    )

    @app.get("/")
    async def index():
        return HTMLResponse(INDEX_PATH.read_text(encoding="utf-8"))

    @app.get("/health")
    async def health():
        metrics = service.metrics()
        return JSONResponse({
            "ok": metrics["ok"],
            "ready": metrics["ready"],
            "activeSessions": metrics["activeSessions"],
            "activeSpeakers": metrics["activeSpeakers"],
            "rejectedSessions": metrics["rejectedSessions"],
            "scheduler": metrics["scheduler"],
            "startupErrors": metrics["startupErrors"],
        })

    @app.get("/api/config")
    async def config():
        return JSONResponse({
            "settings": settings.public_dict(),
            "limits": service.limits_dict(),
            "supportedEngines": get_supported_transcription_engines(),
            "domainProfiles": service.domain_profile_names(),
            "runtimeSettings": service.runtime_settings_contract(),
        })

    @app.get("/api/domain-profiles")
    async def domain_profiles():
        return JSONResponse(service.domain_profiles_payload())

    @app.put("/api/domain-profiles/{name}")
    async def update_domain_profile(name: str, payload: dict):
        try:
            profile = service.update_domain_profile(name, payload)
        except DomainProfileError as exc:
            return JSONResponse(
                {"error": str(exc)},
                status_code=400,
            )
        return JSONResponse({
            "profile": profile,
            **service.domain_profiles_payload(),
        })

    @app.delete("/api/domain-profiles/{name}")
    async def delete_domain_profile(name: str):
        try:
            return JSONResponse(service.delete_domain_profile(name))
        except ValueError as exc:
            return JSONResponse(
                {"error": str(exc)},
                status_code=404,
            )

    @app.patch("/api/config")
    async def update_config(payload: dict):
        updates = payload.get("settings", payload)
        try:
            result = service.update_settings(updates)
        except ValueError as exc:
            return JSONResponse(
                {"error": str(exc)},
                status_code=400,
            )
        return JSONResponse(
            result,
            status_code=400 if result["rejected"] else 200,
        )

    @app.get("/api/metrics")
    async def metrics():
        return JSONResponse(service.metrics())

    @app.websocket("/ws/transcribe")
    async def websocket_transcribe(websocket: WebSocket):
        session_id = uuid.uuid4().hex
        session = service.admit_session(session_id)
        if session is None:
            await websocket.accept()
            await websocket.send_text(json.dumps({
                "type": "error",
                "where": "admission",
                "message": "Server is at the configured session limit.",
                "limits": service.limits_dict(),
            }))
            await websocket.close(code=1013)
            return

        await manager.connect(session_id, websocket)
        await websocket.send_text(json.dumps({
            "type": "hello",
            "clientId": session_id,
            "sessionId": session_id,
            "settings": settings.public_dict(),
            "limits": service.limits_dict(),
            "supportedEngines": get_supported_transcription_engines(),
            "domainProfiles": service.domain_profile_names(),
            "runtimeSettings": service.runtime_settings_contract(),
        }))
        if service.ready.is_set():
            await websocket.send_text(json.dumps({
                "type": "ready",
                "sessionId": session_id,
                "settings": settings.public_dict(),
                "limits": service.limits_dict(),
                "domainProfiles": service.domain_profile_names(),
                "runtimeSettings": service.runtime_settings_contract(),
                "ok": service.scheduler.healthy(),
            }))
            for error in service.startup_errors:
                await websocket.send_text(json.dumps(error))

        try:
            while True:
                message = await websocket.receive()
                if "bytes" in message and message["bytes"] is not None:
                    try:
                        accepted, warning = session.ingest_audio_packet(
                            decode_audio_packet(message["bytes"])
                        )
                    except AudioPacketError as exc:
                        await websocket.send_text(json.dumps({
                            "type": "error",
                            "sessionId": session_id,
                            "message": str(exc),
                            "where": "audio_packet",
                        }))
                        continue
                    except Exception as exc:
                        LOGGER.exception("Could not ingest audio packet")
                        await websocket.send_text(json.dumps({
                            "type": "error",
                            "sessionId": session_id,
                            "message": str(exc),
                            "where": "audio",
                        }))
                        continue
                    if not accepted:
                        await websocket.send_text(json.dumps({
                            "type": "warning",
                            "sessionId": session_id,
                            "message": warning or "Audio chunk was rejected.",
                        }))
                elif "text" in message and message["text"] is not None:
                    try:
                        data = json.loads(message["text"])
                    except json.JSONDecodeError as exc:
                        await websocket.send_text(json.dumps({
                            "type": "error",
                            "sessionId": session_id,
                            "message": f"Invalid command JSON: {exc.msg}",
                            "where": "command",
                        }))
                        continue

                    if not isinstance(data, dict):
                        await websocket.send_text(json.dumps({
                            "type": "error",
                            "sessionId": session_id,
                            "message": "WebSocket commands must be JSON objects.",
                            "where": "command",
                        }))
                        continue

                    command = data.get("type")
                    if command == "start":
                        try:
                            domain_name, domain_profile = service.resolve_domain_profile(
                                data.get("domain")
                            )
                            session.start_streaming(domain_profile, domain_name)
                        except ValueError as exc:
                            await websocket.send_text(json.dumps({
                                "type": "error",
                                "sessionId": session_id,
                                "message": str(exc),
                                "where": "domain",
                            }))
                    elif command == "stop":
                        session.stop_streaming()
                    elif command == "clear":
                        session.clear()
                    elif command == "ping":
                        await websocket.send_text(json.dumps({
                            "type": "pong",
                            "sessionId": session_id,
                            "serverTime": time.time(),
                        }))
                    elif command == "metrics":
                        await websocket.send_text(json.dumps({
                            "type": "metrics",
                            "sessionId": session_id,
                            "metrics": session.snapshot(),
                        }))
                    else:
                        await websocket.send_text(json.dumps({
                            "type": "error",
                            "sessionId": session_id,
                            "message": f"Unknown command: {command}",
                            "where": "command",
                        }))
        except WebSocketDisconnect:
            pass
        except RuntimeError as exc:
            if "disconnect" not in str(exc).lower():
                raise
        finally:
            service.remove_session(session_id)
            await manager.disconnect(session_id)

    app.state.corestt_service = service
    return app


def main(argv=None):
    args = parse_args(argv)
    settings = settings_from_args(args)
    logging.basicConfig(
        level=getattr(logging, settings.log_level, logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    try:
        import uvicorn
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            "uvicorn is missing. Install server dependencies with "
            "'python -m pip install -r requirements.txt'."
        ) from exc

    uvicorn.run(
        create_app(settings),
        host=settings.host,
        port=settings.port,
        log_level=settings.log_level.lower(),
    )


if __name__ == "__main__":
    main()
