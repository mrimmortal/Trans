import unittest
import json
from pathlib import Path
from tempfile import TemporaryDirectory

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
from CoreSTT.server.domain_profiles import DomainProfileError, load_domain_profiles


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

    def test_update_settings_splits_applied_rejected_and_startup_only(self):
        service = CoreSTTService(
            ServerSettings(),
            ConnectionManager(),
            scheduler_factory=FakeScheduler,
        )

        result = service.update_settings({
            "max_sessions": 12,
            "min_length_of_recording": 0.4,
            "model": "base.en",
            "unknown": "value",
        })

        self.assertEqual(result["applied"]["max_sessions"]["appliesTo"], "active_sessions")
        self.assertEqual(result["applied"]["min_length_of_recording"]["appliesTo"], "new_sessions")
        self.assertEqual(result["rejected"]["model"]["reason"], "startup_only")
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

        self.assertEqual(index_response.status_code, 200)
        self.assertIn("CoreSTT WebSocket Integration", index_response.text)
        self.assertIn('id="domainSelect"', index_response.text)
        self.assertIn("selectedDomain", index_response.text)
        self.assertIn("startCommand.domain", index_response.text)
        self.assertEqual(health_response.status_code, 200)
        self.assertTrue(health_response.json()["ok"])
        self.assertEqual(config_response.status_code, 200)
        self.assertIn("faster_whisper", config_response.json()["supportedEngines"])

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
                "medical": {
                    "initial_prompt": "Medical final prompt.",
                    "initial_prompt_realtime": "Medical realtime prompt.",
                    "hotwords": ["hypertension", "metformin"],
                }
            },
            "domainProfiles": ["medical"],
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
        self.assertEqual(recorder.config["initial_prompt"], "Medical final prompt.")
        self.assertEqual(recorder.config["initial_prompt_realtime"], "Medical realtime prompt.")
        self.assertEqual(
            recorder.config["transcription_engine_options"]["hotwords"],
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
