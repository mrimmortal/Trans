import unittest
from types import SimpleNamespace

from app.websocket.audio_stream_handler import AudioStreamHandler
from app.websocket.responses import build_transcription_message, build_welcome_config


class FakeEngine:
    vad_model = object()


class WebSocketPipelineModuleTests(unittest.TestCase):
    def setUp(self):
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
