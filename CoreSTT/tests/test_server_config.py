import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

import numpy as np

from protocol import encode_audio_packet
import server
from server import (
    AudioPacketError,
    ConnectionManager,
    CoreSTTService,
    ServerSettings,
    create_app,
    decode_audio_packet,
    parse_args,
    settings_from_args,
)
from CoreSTT.server.domain_profiles import (
    DomainProfileError,
    compose_domain_profile,
    load_domain_profiles,
)


class FakeScheduler:
    def __init__(self, settings, result_callback, drop_callback, error_callback):
        self.settings = settings

    def start(self):
        pass

    def stop(self):
        pass

    def wait_ready(self, timeout=None):
        return True

    def healthy(self):
        return True

    def snapshot(self):
        return {"mode": "fake", "queues": {}, "workers": {}}

    def submit(self, job):
        raise AssertionError("not used by these tests")

    def cancel_session(self, session_id):
        pass


class FakeRecorder:
    instances = []

    def __init__(self, **config):
        self.config = config
        self.is_recording = False
        self.is_shut_down = False
        FakeRecorder.instances.append(self)

    def flush_buffered_audio(self):
        pass

    def abort(self):
        pass

    def shutdown(self):
        self.is_shut_down = True

    def feed_audio(self, *_args, **_kwargs):
        pass

    def text(self):
        return ""


class CaptureManager(ConnectionManager):
    def __init__(self):
        super().__init__()
        self.messages = []
        self.broadcasts = []

    def publish_session(self, session_id, message):
        self.messages.append((session_id, message))

    def publish_all(self, message):
        self.broadcasts.append(message)


class ServerConfigTest(unittest.TestCase):
    def test_default_settings_separate_realtime_and_final_tuning(self):
        settings = settings_from_args(parse_args([]))

        self.assertEqual(settings.model, "small.en")
        self.assertEqual(settings.realtime_model, "tiny.en")
        self.assertEqual(settings.beam_size, 3)
        self.assertEqual(settings.batch_size, 1)
        self.assertEqual(settings.beam_size_realtime, 1)
        self.assertEqual(settings.realtime_batch_size, 1)
        self.assertEqual(settings.realtime_processing_pause, 0.6)
        self.assertTrue(settings.realtime_transcription_enabled)
        self.assertEqual(settings.realtime_min_audio_seconds, 0.8)
        self.assertEqual(settings.realtime_max_audio_seconds, 5.0)
        self.assertEqual(settings.post_speech_silence_duration, 0.7)
        self.assertTrue(settings.vad_filter_final)
        self.assertFalse(settings.vad_filter_realtime)
        self.assertTrue(settings.public_dict()["vad_filter"])

    def test_vad_flags_are_independent_and_legacy_alias_disables_both(self):
        split = settings_from_args(parse_args([
            "--no-vad-filter-final",
            "--vad-filter-realtime",
        ]))
        legacy = settings_from_args(parse_args(["--no-vad-filter"]))

        self.assertFalse(split.vad_filter_final)
        self.assertTrue(split.vad_filter_realtime)
        self.assertFalse(legacy.vad_filter_final)
        self.assertFalse(legacy.vad_filter_realtime)
        legacy_settings = ServerSettings(vad_filter=False)
        self.assertFalse(legacy_settings.vad_filter_final)
        self.assertFalse(legacy_settings.vad_filter_realtime)

    def test_fixed_models_reject_incompatible_overrides(self):
        with self.assertRaisesRegex(SystemExit, "small.en"):
            settings_from_args(parse_args(["--model", "base.en"]))
        with self.assertRaisesRegex(SystemExit, "tiny.en"):
            settings_from_args(parse_args(["--realtime-model", "base.en"]))

    def test_device_and_compute_type_remain_configurable(self):
        settings = settings_from_args(parse_args([
            "--device",
            "cpu",
            "--compute-type",
            "int8",
        ]))

        self.assertEqual(settings.device, "cpu")
        self.assertEqual(settings.compute_type, "int8")

    def test_cli_defaults_follow_server_settings_defaults(self):
        defaults = ServerSettings()
        settings = settings_from_args(parse_args([]))

        self.assertEqual(settings.compute_type, defaults.compute_type)
        self.assertEqual(settings.device, defaults.device)
        self.assertEqual(settings.num_workers, defaults.num_workers)
        self.assertEqual(
            settings.realtime_transcription_enabled,
            defaults.realtime_transcription_enabled,
        )
        self.assertEqual(
            settings.resource_monitoring_enabled,
            defaults.resource_monitoring_enabled,
        )
        self.assertEqual(
            settings.resource_log_interval_seconds,
            defaults.resource_log_interval_seconds,
        )

    def test_startup_performance_controls_parse_from_cli(self):
        settings = settings_from_args(parse_args([
            "--cpu-threads",
            "4",
            "--num-workers",
            "2",
            "--no-single-gpu-inference-gate",
        ]))

        self.assertEqual(settings.cpu_threads, 4)
        self.assertEqual(settings.num_workers, 2)
        self.assertFalse(settings.single_gpu_inference_gate)

    def test_realtime_transcription_can_be_disabled_from_cli(self):
        settings = settings_from_args(parse_args(["--no-realtime-transcription"]))

        self.assertFalse(settings.realtime_transcription_enabled)

    def test_resource_monitoring_settings_parse_from_cli(self):
        settings = settings_from_args(parse_args([
            "--no-resource-monitoring",
            "--resource-log-interval-seconds",
            "5",
            "--no-resource-metrics-include-cuda",
        ]))

        self.assertFalse(settings.resource_monitoring_enabled)
        self.assertEqual(settings.resource_log_interval_seconds, 5)
        self.assertFalse(settings.resource_metrics_include_cuda)

    def test_service_uses_direct_realtime_session_by_default(self):
        service = CoreSTTService(
            ServerSettings(),
            CaptureManager(),
            scheduler_factory=FakeScheduler,
        )

        session = service.admit_session("session-1")
        try:
            self.assertIsInstance(session, server.RealtimeSession)
        finally:
            service.remove_session("session-1")

    def test_direct_session_keeps_bounded_realtime_and_complete_final_audio(self):
        service = CoreSTTService(
            ServerSettings(
                min_length_of_recording=0.0,
                realtime_max_audio_seconds=0.001,
            ),
            CaptureManager(),
            scheduler_factory=FakeScheduler,
        )
        session = service.admit_session("session-1")
        first = np.arange(12, dtype=np.int16)
        second = np.arange(12, 24, dtype=np.int16)

        with session.lock:
            session._start_recording_locked(1.0)
            session._append_recording_samples_locked(first)
            session._append_recording_samples_locked(second)
            realtime_audio = session._frames_to_float32(session.realtime_frames)
            final_job = session._finish_recording_locked("test")

        self.assertEqual(session.realtime_sample_count, 0)
        self.assertEqual(realtime_audio.size, 16)
        np.testing.assert_array_equal(
            np.rint(realtime_audio * 32768).astype(np.int16),
            np.arange(8, 24, dtype=np.int16),
        )
        self.assertEqual(final_job.audio.size, 24)
        np.testing.assert_array_equal(
            np.rint(final_job.audio * 32768).astype(np.int16),
            np.arange(24, dtype=np.int16),
        )
        service.remove_session("session-1")

    def test_direct_session_does_not_create_realtime_job_when_disabled(self):
        service = CoreSTTService(
            ServerSettings(
                realtime_transcription_enabled=False,
                realtime_processing_pause=0.0,
                realtime_min_audio_seconds=0.0,
            ),
            CaptureManager(),
            scheduler_factory=FakeScheduler,
        )
        session = service.admit_session("session-1")

        with session.lock:
            session._start_recording_locked(1.0)
            session._append_recording_samples_locked(np.arange(16000, dtype=np.int16))
            job = session._maybe_create_realtime_job_locked(2.0)
            final_job = session._finish_recording_locked("test")

        self.assertIsNone(job)
        self.assertEqual(session.realtime_sample_count, 0)
        self.assertEqual(len(session.realtime_frames), 0)
        self.assertEqual(final_job.kind, "final")
        self.assertEqual(final_job.audio.size, 16000)
        service.remove_session("session-1")

    def test_recorder_backed_session_disables_recorder_realtime_pipeline(self):
        FakeRecorder.instances = []
        service = CoreSTTService(
            ServerSettings(
                realtime_transcription_enabled=False,
                use_recorder_backed_realtime_session=True,
            ),
            CaptureManager(),
            scheduler_factory=FakeScheduler,
            recorder_factory=FakeRecorder,
        )
        session = service.admit_session("session-1")
        try:
            recorder = FakeRecorder.instances[-1]
            self.assertFalse(recorder.config["enable_realtime_transcription"])
        finally:
            service.remove_session("session-1")

    def test_recorder_backed_session_does_not_submit_realtime_when_disabled(self):
        service = CoreSTTService(
            ServerSettings(realtime_transcription_enabled=False),
            CaptureManager(),
            scheduler_factory=FakeScheduler,
        )
        session = service.admit_session("session-1")
        try:
            result = service.transcribe_for_recorder(
                "session-1",
                "realtime",
                np.array([0.0], dtype=np.float32),
                "en",
                True,
            )
        finally:
            service.remove_session("session-1")

        self.assertEqual(result.text, "")

    def test_direct_session_discards_realtime_after_final_result(self):
        manager = CaptureManager()
        service = CoreSTTService(
            ServerSettings(),
            manager,
            scheduler_factory=FakeScheduler,
        )
        session = service.admit_session("session-1")

        def result(kind, text, sequence=0):
            return server.InferenceResult(
                request_id=f"{kind}-request",
                session_id="session-1",
                kind=kind,
                segment_id=1,
                sequence=sequence,
                generation=session.generation,
                text=text,
                error=None,
                created_at=1.0,
                started_at=1.1,
                completed_at=1.2,
                queue_delay=0.1,
                inference_duration=0.1,
                total_latency=0.2,
            )

        session.handle_inference_result(result("final", "final text"))
        with session.lock:
            session.recording = True
            session.active_segment_id = 1
        session.handle_inference_result(result("realtime", "late text", sequence=1))

        transcript_types = [
            message["type"]
            for _session_id, message in manager.messages
            if message.get("type") in ("realtime", "final")
        ]
        self.assertEqual(transcript_types, ["final"])
        self.assertEqual(session.stale_realtime_discarded, 1)
        service.remove_session("session-1")

    def test_server_module_preserves_public_compatibility_exports(self):
        expected_names = [
            "ACTIVE_RUNTIME_SETTINGS",
            "AudioData",
            "AudioPacketError",
            "BASE_TUNING_DEFAULTS",
            "BOOL_SETTINGS",
            "ConnectionManager",
            "CoreSTTService",
            "DICT_SETTINGS",
            "FairInferenceQueue",
            "FLOAT_SETTINGS",
            "InferenceExecutionGate",
            "InferenceJob",
            "InferenceResult",
            "InferenceScheduler",
            "INT_SETTINGS",
            "NEW_SESSION_RUNTIME_SETTINGS",
            "OPTIONAL_STRING_SETTINGS",
            "QueueSubmitResult",
            "RecorderBackedRealtimeSession",
            "RealtimeSession",
            "RunningStats",
            "SchedulerTranscriptionExecutor",
            "SegmentState",
            "SegmentTimelineTracker",
            "ServerSettings",
            "SessionStore",
            "SharedEngineWorker",
            "STARTUP_ONLY_SETTINGS",
            "TUNING_PROFILES",
            "TUPLE_FLOAT_SETTINGS",
            "VoiceActivityDetector",
            "coerce_setting_value",
            "create_app",
            "decode_audio_packet",
            "effective_device",
            "load_fastapi",
            "main",
            "normalize_engine_name",
            "parse_args",
            "parse_float_tuple",
            "parse_json_object",
            "read_wav_float32",
            "require_positive_int",
            "resample_int16",
            "runtime_settings_contract",
            "settings_from_args",
        ]

        for name in expected_names:
            with self.subTest(name=name):
                self.assertTrue(hasattr(server, name), name)

    def test_settings_from_args_applies_profile_defaults_and_engine_names(self):
        args = parse_args([
            "--host",
            "127.0.0.1",
            "--port",
            "8090",
            "--profile",
            "parakeet-low-latency",
            "--engine",
            "faster-whisper",
            "--realtime-engine",
            "parakeet",
            "--domain-profiles-path",
            "profiles.json",
            "--default-domain",
            "medical",
            "--wake-words",
            "jarvis",
        ])

        settings = settings_from_args(args)

        self.assertEqual(settings.host, "127.0.0.1")
        self.assertEqual(settings.port, 8090)
        self.assertEqual(settings.transcription_engine, "faster_whisper")
        self.assertEqual(settings.realtime_transcription_engine, "parakeet")
        self.assertEqual(settings.domain_profiles_path, "profiles.json")
        self.assertEqual(settings.default_domain, "medical")
        self.assertEqual(settings.batch_size, 1)
        self.assertEqual(settings.realtime_batch_size, 1)
        self.assertEqual(settings.wakeword_backend, "pvporcupine")
        self.assertTrue(settings.wake_word_enabled())

    def test_load_domain_profiles_validates_profiles_and_hotwords(self):
        with TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "profiles.json"
            path.write_text(
                """
                {
                  "profiles": {
                    "medical": {
                      "initial_prompt": "Medical final prompt.",
                      "initial_prompt_realtime": "Medical realtime prompt.",
                      "hotwords": ["hypertension", "metformin"]
                    },
                    "legal": {
                      "initial_prompt": null,
                      "initial_prompt_realtime": null,
                      "hotwords": "affidavit plaintiff"
                    }
                  }
                }
                """,
                encoding="utf-8",
            )

            profiles = load_domain_profiles(path)

        self.assertEqual(sorted(profiles.names()), ["legal", "medical"])
        self.assertEqual(profiles.get("medical").hotwords, ["hypertension", "metformin"])
        self.assertEqual(profiles.get("legal").hotwords, "affidavit plaintiff")

    def test_load_domain_profiles_rejects_invalid_profiles_object(self):
        with TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "profiles.json"
            path.write_text('{"profiles": []}', encoding="utf-8")

            with self.assertRaisesRegex(DomainProfileError, "profiles"):
                load_domain_profiles(path)

    def test_load_domain_profiles_rejects_invalid_hotwords(self):
        with TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "profiles.json"
            path.write_text(
                '{"profiles": {"medical": {"hotwords": [123]}}}',
                encoding="utf-8",
            )

            with self.assertRaisesRegex(DomainProfileError, "hotwords"):
                load_domain_profiles(path)

    def test_compose_domain_profile_uses_global_profile_when_no_domain_selected(self):
        with TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "profiles.json"
            path.write_text(
                """
                {
                  "profiles": {
                    "global": {
                      "initial_prompt": "Global final prompt.",
                      "initial_prompt_realtime": "Global realtime prompt.",
                      "hotwords": ["start bold", "undo"]
                    }
                  }
                }
                """,
                encoding="utf-8",
            )

            profiles = load_domain_profiles(path)
            profile = compose_domain_profile(profiles)

        self.assertEqual(profile.initial_prompt, "Global final prompt.")
        self.assertEqual(profile.initial_prompt_realtime, "Global realtime prompt.")
        self.assertEqual(profile.hotwords, ["start bold", "undo"])

    def test_compose_domain_profile_appends_domain_to_global_profile(self):
        with TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "profiles.json"
            path.write_text(
                """
                {
                  "profiles": {
                    "global": {
                      "initial_prompt": "Global final prompt.",
                      "initial_prompt_realtime": "Global realtime prompt.",
                      "hotwords": ["start bold", "undo", "metformin"]
                    },
                    "medical": {
                      "initial_prompt": "Medical final prompt.",
                      "initial_prompt_realtime": "Medical realtime prompt.",
                      "hotwords": ["metformin", "hypertension"]
                    }
                  }
                }
                """,
                encoding="utf-8",
            )

            profiles = load_domain_profiles(path)
            profile = compose_domain_profile(profiles, "medical")

        self.assertEqual(
            profile.initial_prompt,
            "Global final prompt.\n\nMedical final prompt.",
        )
        self.assertEqual(profile.initial_prompt_realtime, "Medical realtime prompt.")
        self.assertEqual(
            profile.hotwords,
            ["start bold", "undo", "metformin", "hypertension"],
        )

    def test_compose_domain_profile_without_global_preserves_domain_only_behavior(self):
        with TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "profiles.json"
            path.write_text(
                """
                {
                  "profiles": {
                    "medical": {
                      "initial_prompt": "Medical final prompt.",
                      "initial_prompt_realtime": "Medical realtime prompt.",
                      "hotwords": ["hypertension", "metformin"]
                    }
                  }
                }
                """,
                encoding="utf-8",
            )

            profiles = load_domain_profiles(path)
            profile = compose_domain_profile(profiles, "medical")

        self.assertEqual(profile.initial_prompt, "Medical final prompt.")
        self.assertEqual(profile.initial_prompt_realtime, "Medical realtime prompt.")
        self.assertEqual(profile.hotwords, ["hypertension", "metformin"])

    def test_update_settings_splits_applied_rejected_and_startup_only(self):
        service = CoreSTTService(
            ServerSettings(),
            ConnectionManager(),
            scheduler_factory=FakeScheduler,
        )

        result = service.update_settings({
            "max_sessions": 12,
            "resource_monitoring_enabled": False,
            "min_length_of_recording": 0.4,
            "model": "base.en",
            "cpu_threads": 4,
            "num_workers": 2,
            "single_gpu_inference_gate": False,
            "realtime_transcription_enabled": False,
            "unknown": "value",
        })

        self.assertEqual(result["applied"]["max_sessions"]["appliesTo"], "active_sessions")
        self.assertEqual(
            result["applied"]["resource_monitoring_enabled"]["appliesTo"],
            "active_sessions",
        )
        self.assertEqual(result["applied"]["min_length_of_recording"]["appliesTo"], "new_sessions")
        self.assertEqual(
            result["applied"]["realtime_transcription_enabled"]["appliesTo"],
            "new_sessions",
        )
        self.assertEqual(result["rejected"]["model"]["reason"], "startup_only")
        self.assertEqual(result["rejected"]["cpu_threads"]["reason"], "startup_only")
        self.assertEqual(result["rejected"]["num_workers"]["reason"], "startup_only")
        self.assertEqual(
            result["rejected"]["single_gpu_inference_gate"]["reason"],
            "startup_only",
        )
        self.assertEqual(result["rejected"]["unknown"]["reason"], "unknown")
        self.assertEqual(service.settings.max_sessions, 12)

    def test_packet_to_server_samples_rejects_misaligned_multichannel_audio(self):
        service = CoreSTTService(
            ServerSettings(),
            ConnectionManager(),
            scheduler_factory=FakeScheduler,
        )
        packet = decode_audio_packet(
            encode_audio_packet(
                {
                    "sampleRate": 16000,
                    "channels": 2,
                    "format": "pcm_s16le",
                },
                b"\x00\x00\x01",
            )
        )

        with self.assertRaisesRegex(AudioPacketError, "aligned"):
            service.packet_to_server_samples(packet)

    def test_create_app_serves_index_health_and_config_with_fake_scheduler(self):
        from fastapi.testclient import TestClient

        app = create_app(
            ServerSettings(model_warmup=False),
            scheduler_factory=FakeScheduler,
        )

        self.assertTrue(hasattr(app.state, "corestt_service"))
        with TestClient(app) as client:
            index_response = client.get("/")
            health_response = client.get("/health")
            config_response = client.get("/api/config")
            metrics_response = client.get("/api/metrics")

        self.assertEqual(index_response.status_code, 200)
        self.assertIn("CoreSTT WebSocket Integration", index_response.text)
        self.assertIn('id="domainSelect"', index_response.text)
        self.assertIn("selectedDomain", index_response.text)
        self.assertIn("startCommand.domain", index_response.text)
        self.assertIn('id="exportSnapshotButton"', index_response.text)
        self.assertIn("corestt-diagnostics-session-", index_response.text)
        self.assertEqual(health_response.status_code, 200)
        self.assertTrue(health_response.json()["ok"])
        self.assertEqual(config_response.status_code, 200)
        self.assertIn("faster_whisper", config_response.json()["supportedEngines"])
        settings_payload = config_response.json()["settings"]
        self.assertFalse(settings_payload["vad_filter_realtime"])
        self.assertTrue(settings_payload["vad_filter_final"])
        self.assertTrue(settings_payload["vad_filter"])
        self.assertEqual(metrics_response.status_code, 200)
        metrics_payload = metrics_response.json()
        self.assertIn("resources", metrics_payload)
        self.assertIn("diagnostics", metrics_payload)
        self.assertIn("thresholds", metrics_payload)
        self.assertIn("settings", metrics_payload)

    def test_config_exposes_domain_profile_names(self):
        from fastapi.testclient import TestClient

        with TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "profiles.json"
            path.write_text(
                '{"profiles": {"medical": {"hotwords": ["metformin"]}, "general": {}}}',
                encoding="utf-8",
            )
            app = create_app(
                ServerSettings(model_warmup=False, domain_profiles_path=str(path)),
                scheduler_factory=FakeScheduler,
                recorder_factory=FakeRecorder,
            )

            with TestClient(app) as client:
                config_response = client.get("/api/config")

        self.assertEqual(config_response.status_code, 200)
        self.assertEqual(config_response.json()["domainProfiles"], ["general", "medical"])

    def test_get_domain_profiles_returns_editable_profile_details(self):
        from fastapi.testclient import TestClient

        with TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "profiles.json"
            path.write_text(
                """
                {
                  "profiles": {
                    "global": {
                      "initial_prompt": "Global final prompt.",
                      "initial_prompt_realtime": "Global realtime prompt.",
                      "hotwords": ["start bold", "undo", "metformin"]
                    },
                    "medical": {
                      "initial_prompt": "Medical final prompt.",
                      "initial_prompt_realtime": "Medical realtime prompt.",
                      "hotwords": ["hypertension", "metformin"]
                    }
                  }
                }
                """,
                encoding="utf-8",
            )
            app = create_app(
                ServerSettings(model_warmup=False, domain_profiles_path=str(path)),
                scheduler_factory=FakeScheduler,
                recorder_factory=FakeRecorder,
            )

            with TestClient(app) as client:
                response = client.get("/api/domain-profiles")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {
            "profiles": {
                "global": {
                    "initial_prompt": "Global final prompt.",
                    "initial_prompt_realtime": "Global realtime prompt.",
                    "hotwords": ["start bold", "undo", "metformin"],
                },
                "medical": {
                    "initial_prompt": "Medical final prompt.",
                    "initial_prompt_realtime": "Medical realtime prompt.",
                    "hotwords": ["hypertension", "metformin"],
                }
            },
            "domainProfiles": ["global", "medical"],
        })

    def test_put_domain_profile_updates_file_and_broadcasts_names(self):
        with TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "profiles.json"
            path.write_text('{"profiles": {"general": {}}}', encoding="utf-8")
            manager = CaptureManager()
            service = CoreSTTService(
                ServerSettings(model_warmup=False, domain_profiles_path=str(path)),
                manager,
                scheduler_factory=FakeScheduler,
                recorder_factory=FakeRecorder,
            )

            profile = service.update_domain_profile("medical", {
                "initial_prompt": "Medical final prompt.",
                "initial_prompt_realtime": "Medical realtime prompt.",
                "hotwords": ["hypertension", "metformin"],
            })

            saved = json.loads(path.read_text(encoding="utf-8"))

        self.assertEqual(profile["hotwords"], ["hypertension", "metformin"])
        self.assertEqual(saved["profiles"]["medical"]["initial_prompt"], "Medical final prompt.")
        self.assertEqual(
            manager.broadcasts[-1],
            {
                "type": "domain_profiles_updated",
                "domainProfiles": ["general", "medical"],
                "profiles": {
                    "general": {
                        "initial_prompt": None,
                        "initial_prompt_realtime": None,
                        "hotwords": None,
                    },
                    "medical": {
                        "initial_prompt": "Medical final prompt.",
                        "initial_prompt_realtime": "Medical realtime prompt.",
                        "hotwords": ["hypertension", "metformin"],
                    },
                },
            },
        )

    def test_domain_profile_api_validates_updates_and_deletes_profiles(self):
        from fastapi.testclient import TestClient

        with TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "profiles.json"
            path.write_text(
                '{"profiles": {"medical": {"hotwords": ["metformin"]}}}',
                encoding="utf-8",
            )
            app = create_app(
                ServerSettings(model_warmup=False, domain_profiles_path=str(path)),
                scheduler_factory=FakeScheduler,
                recorder_factory=FakeRecorder,
            )

            with TestClient(app) as client:
                invalid = client.put(
                    "/api/domain-profiles/legal",
                    json={"hotwords": [123]},
                )
                deleted = client.delete("/api/domain-profiles/medical")
                after_delete = client.get("/api/domain-profiles")

        self.assertEqual(invalid.status_code, 400)
        self.assertEqual(deleted.status_code, 200)
        self.assertEqual(deleted.json()["domainProfiles"], [])
        self.assertEqual(after_delete.json(), {"profiles": {}, "domainProfiles": []})

    def test_websocket_start_rejects_unknown_domain(self):
        from fastapi.testclient import TestClient

        FakeRecorder.instances = []
        with TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "profiles.json"
            path.write_text(
                '{"profiles": {"medical": {"hotwords": ["metformin"]}}}',
                encoding="utf-8",
            )
            app = create_app(
                ServerSettings(model_warmup=False, domain_profiles_path=str(path)),
                scheduler_factory=FakeScheduler,
                recorder_factory=FakeRecorder,
            )

            with TestClient(app) as client:
                with client.websocket_connect("/ws/transcribe") as websocket:
                    websocket.receive_json()
                    websocket.receive_json()
                    websocket.send_json({"type": "start", "domain": "unknown"})
                    message = websocket.receive_json()

        self.assertEqual(message["type"], "error")
        self.assertEqual(message["where"], "domain")
        self.assertIn("unknown", message["message"])
        self.assertTrue(FakeRecorder.instances)
        self.assertFalse(any(recorder.config.get("initial_prompt") for recorder in FakeRecorder.instances))

    def test_websocket_start_applies_domain_profile_to_session_recorder(self):
        from fastapi.testclient import TestClient

        FakeRecorder.instances = []
        with TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "profiles.json"
            path.write_text(
                """
                {
                  "profiles": {
                    "global": {
                      "initial_prompt": "Global final prompt.",
                      "initial_prompt_realtime": "Global realtime prompt.",
                      "hotwords": ["start bold", "undo", "metformin"]
                    },
                    "medical": {
                      "initial_prompt": "Medical final prompt.",
                      "initial_prompt_realtime": "Medical realtime prompt.",
                      "hotwords": ["hypertension", "metformin"]
                    }
                  }
                }
                """,
                encoding="utf-8",
            )
            app = create_app(
                ServerSettings(model_warmup=False, domain_profiles_path=str(path)),
                scheduler_factory=FakeScheduler,
                recorder_factory=FakeRecorder,
            )

            with TestClient(app) as client:
                with client.websocket_connect("/ws/transcribe") as websocket:
                    websocket.receive_json()
                    websocket.receive_json()
                    websocket.send_json({"type": "start", "domain": "medical"})
                    status = websocket.receive_json()
                    websocket.send_json({"type": "metrics"})
                    metrics = websocket.receive_json()

        self.assertEqual(status["type"], "status")
        self.assertEqual(status["domain"], "medical")
        self.assertEqual(metrics["metrics"]["domain"], "medical")
        recorder = FakeRecorder.instances[-1]
        self.assertEqual(
            recorder.config["initial_prompt"],
            "Global final prompt.\n\nMedical final prompt.",
        )
        self.assertEqual(
            recorder.config["initial_prompt_realtime"],
            "Medical realtime prompt.",
        )
        self.assertEqual(
            recorder.config["transcription_engine_options"]["hotwords"],
            ["start bold", "undo", "metformin", "hypertension"],
        )
        self.assertEqual(
            recorder.config["realtime_transcription_engine_options"]["hotwords"],
            ["hypertension", "metformin"],
        )

    def test_timeline_events_include_domain_for_logs(self):
        FakeRecorder.instances = []
        with TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "profiles.json"
            path.write_text(
                '{"profiles": {"medical": {"hotwords": ["metformin"]}}}',
                encoding="utf-8",
            )
            manager = CaptureManager()
            service = CoreSTTService(
                ServerSettings(model_warmup=False, domain_profiles_path=str(path)),
                manager,
                scheduler_factory=FakeScheduler,
                recorder_factory=FakeRecorder,
            )
            session = service.admit_session("session-1")
            domain_name, domain_profile = service.resolve_domain_profile("medical")
            session.start_streaming(domain_profile, domain_name)

            session._publish_timeline_event("domain_log_probe")

            service.remove_session("session-1")

        timeline_messages = [
            message for _session_id, message in manager.messages
            if message.get("type") == "timeline"
        ]
        self.assertTrue(timeline_messages)
        self.assertEqual(timeline_messages[-1]["domain"], "medical")

    def test_start_streaming_logs_domain_profile(self):
        FakeRecorder.instances = []
        with TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "profiles.json"
            path.write_text(
                '{"profiles": {"medical": {"hotwords": ["metformin"]}}}',
                encoding="utf-8",
            )
            service = CoreSTTService(
                ServerSettings(model_warmup=False, domain_profiles_path=str(path)),
                CaptureManager(),
                scheduler_factory=FakeScheduler,
                recorder_factory=FakeRecorder,
            )
            session = service.admit_session("session-1")
            domain_name, domain_profile = service.resolve_domain_profile("medical")

            with self.assertLogs("uvicorn.error", level="INFO") as logs:
                session.start_streaming(domain_profile, domain_name)

            service.remove_session("session-1")

        self.assertIn(
            "session session-1 streaming started domain=medical",
            "\n".join(logs.output),
        )


if __name__ == "__main__":
    unittest.main()
