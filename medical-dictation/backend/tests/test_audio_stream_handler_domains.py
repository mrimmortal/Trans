import unittest
from types import SimpleNamespace

from app.main import AudioStreamHandler


class FakeEngine:
    def transcribe_audio_bytes(self, audio_bytes):
        return {
            "text": "project update period",
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
        self.assertEqual(result["text"], "project update period")
        self.assertEqual(result["commands"], [])

    def test_unknown_domain_uses_vanilla_transcript(self):
        handler = AudioStreamHandler(FakeEngine(), self.config, domain="legacy-domain")
        handler.audio_buffer.extend(b"\x01\x00" * 16000)

        result = handler._transcribe_buffer()

        self.assertEqual(result["domain"], "general")
        self.assertEqual(result["text"], "project update period")
        self.assertEqual(result["commands"], [])


if __name__ == "__main__":
    unittest.main()
