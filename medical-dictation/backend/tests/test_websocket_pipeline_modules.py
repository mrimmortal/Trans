import unittest
from types import SimpleNamespace

from fastapi.testclient import TestClient

from app.domains.base import DomainAdapter
from app.domains import registry
from app.domains.registry import register_domain
from app.main import app
from app.websocket.audio_stream_handler import AudioStreamHandler
from app.websocket.responses import build_transcription_message, build_welcome_config


class FakeEngine:
    vad_model = object()


class WebSocketPipelineModuleTests(unittest.TestCase):
    def setUp(self):
        self._registry_snapshot = registry._DOMAIN_REGISTRY.copy()
        self.config = SimpleNamespace(
            SAMPLE_RATE=16000,
            CHANNELS=1,
            SAMPLE_WIDTH=2,
            MIN_AUDIO_SAMPLES=8000,
            MIN_CHUNK_SIZE_BYTES=19200,
            MAX_CHUNK_SIZE_BYTES=192000,
            OVERLAP_SIZE_BYTES=16000,
            MODEL_SIZE="tiny",
            DEVICE="cpu",
            TRANSCRIPTION_LANGUAGE="en",
            ACCENT_SUPPORT_ENABLED=False,
            DEFAULT_TRANSCRIPTION_DOMAIN="general",
        )

    def tearDown(self):
        registry._DOMAIN_REGISTRY.clear()
        registry._DOMAIN_REGISTRY.update(self._registry_snapshot)

    def test_welcome_config_matches_websocket_connection_contract(self):
        handler = AudioStreamHandler(FakeEngine(), self.config, domain="general")

        config = build_welcome_config(self.config, FakeEngine(), handler)

        self.assertEqual(config["sample_rate"], 16000)
        self.assertEqual(config["channels"], 1)
        self.assertEqual(config["sample_width"], 2)
        self.assertEqual(config["domain"], "general")
        self.assertEqual(config["available_domains"], ["general"])
        self.assertTrue(config["vad_enabled"])
        self.assertIn("available_commands", config)

    def test_welcome_config_uses_registered_available_domains(self):
        class CustomDomainAdapter(DomainAdapter):
            name = "custom"

        register_domain("custom", CustomDomainAdapter)
        handler = AudioStreamHandler(FakeEngine(), self.config, domain="general")

        config = build_welcome_config(self.config, FakeEngine(), handler)

        self.assertEqual(config["available_domains"], ["custom", "general"])

    def test_config_endpoint_uses_registered_available_domains(self):
        class CustomDomainAdapter(DomainAdapter):
            name = "custom"

        register_domain("custom", CustomDomainAdapter)
        app.state.config = self.config
        app.state.stt_service = FakeEngine()

        response = TestClient(app).get("/config")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json()["domains"],
            {
                "default": "general",
                "available": ["custom", "general"],
            },
        )

    def test_transcription_message_matches_websocket_response_contract(self):
        message = build_transcription_message(
            {
                "text": "project update period",
                "domain": "general",
                "commands": [],
                "processing_time_ms": 10.0,
                "audio_duration_seconds": 1.0,
                "flush_reason": "natural_pause",
            },
            fallback_domain="general",
        )

        self.assertEqual(message["type"], "transcription")
        self.assertEqual(message["text"], "project update period")
        self.assertEqual(message["domain"], "general")
        self.assertEqual(message["commands"], [])
        self.assertTrue(message["is_final"])
        self.assertEqual(message["confidence"], 0.95)
        self.assertEqual(message["processing_time_ms"], 10.0)
        self.assertEqual(message["audio_duration_seconds"], 1.0)
        self.assertEqual(message["flush_reason"], "natural_pause")
        self.assertIn("timestamp", message)


if __name__ == "__main__":
    unittest.main()
