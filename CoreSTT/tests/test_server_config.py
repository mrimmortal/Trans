import unittest

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
            "--wake-words",
            "jarvis",
        ])

        settings = settings_from_args(args)

        self.assertEqual(settings.host, "127.0.0.1")
        self.assertEqual(settings.port, 8090)
        self.assertEqual(settings.transcription_engine, "faster_whisper")
        self.assertEqual(settings.realtime_transcription_engine, "parakeet")
        self.assertEqual(settings.batch_size, 1)
        self.assertEqual(settings.realtime_batch_size, 1)
        self.assertEqual(settings.wakeword_backend, "pvporcupine")
        self.assertTrue(settings.wake_word_enabled())

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
        self.assertEqual(health_response.status_code, 200)
        self.assertTrue(health_response.json()["ok"])
        self.assertEqual(config_response.status_code, 200)
        self.assertIn("faster_whisper", config_response.json()["supportedEngines"])


if __name__ == "__main__":
    unittest.main()
