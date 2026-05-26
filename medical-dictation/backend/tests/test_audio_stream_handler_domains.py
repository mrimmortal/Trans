import unittest
from types import SimpleNamespace
from unittest.mock import patch

from app.main import AudioStreamHandler


class FakeEngine:
    def transcribe_audio_bytes(self, audio_bytes):
        return {
            "text": "patient takes aspirin period",
            "processing_time_ms": 10.0,
            "error": None,
        }


class AudioStreamHandlerDomainTests(unittest.TestCase):
    def setUp(self):
        self.config = SimpleNamespace(
            SAMPLE_RATE=16000,
            SAMPLE_WIDTH=2,
            MIN_AUDIO_SAMPLES=8000,
            MIN_CHUNK_SIZE_BYTES=19200,
            MAX_CHUNK_SIZE_BYTES=192000,
            OVERLAP_SIZE_BYTES=16000,
            DEFAULT_TRANSCRIPTION_DOMAIN="general",
        )

    def test_general_domain_returns_vanilla_transcript(self):
        handler = AudioStreamHandler(FakeEngine(), self.config, domain="general")
        handler.audio_buffer.extend(b"\x01\x00" * 16000)

        result = handler._transcribe_buffer()

        self.assertEqual(result["domain"], "general")
        self.assertEqual(result["text"], "patient takes aspirin period")
        self.assertEqual(result["commands"], [])

    def test_medical_domain_preserves_current_medical_behavior(self):
        with patch("app.services.template_manager.get_template_manager") as get_manager:
            get_manager.return_value.list_templates.return_value = []
            handler = AudioStreamHandler(FakeEngine(), self.config, domain="medical")

        handler.audio_buffer.extend(b"\x01\x00" * 16000)

        result = handler._transcribe_buffer()

        self.assertEqual(result["domain"], "medical")
        self.assertEqual(result["text"], "Patient takes Aspirin.")
        self.assertEqual(len(result["commands"]), 1)


if __name__ == "__main__":
    unittest.main()
