import unittest
from types import SimpleNamespace
from unittest.mock import patch

from app.main import AudioStreamHandler


class FakeEngine:
    def transcribe_audio_bytes(self, audio_bytes):
        return {
            "text": "patient is stable",
            "processing_time_ms": 123.4,
            "error": None,
        }


class AudioStreamHandlerLatencyTests(unittest.TestCase):
    def setUp(self):
        self.config = SimpleNamespace(
            SAMPLE_RATE=16000,
            SAMPLE_WIDTH=2,
            MIN_AUDIO_SAMPLES=8000,
            MIN_CHUNK_SIZE_BYTES=19200,
            MAX_CHUNK_SIZE_BYTES=192000,
            OVERLAP_SIZE_BYTES=16000,
        )

    def test_transcribe_buffer_returns_processing_metadata(self):
        with patch("app.services.template_manager.get_template_manager") as get_manager:
            get_manager.return_value.list_templates.return_value = []
            handler = AudioStreamHandler(FakeEngine(), self.config)

        handler.pending_flush_reason = "natural_pause"
        handler.audio_buffer.extend(b"\x01\x00" * 16000)
        handler.has_speech_in_buffer = True

        result = handler._transcribe_buffer()

        self.assertEqual(result["text"], "Patient is stable")
        self.assertEqual(result["processing_time_ms"], 123.4)
        self.assertEqual(result["audio_duration_seconds"], 1.0)
        self.assertEqual(result["flush_reason"], "natural_pause")

    def test_flush_marks_manual_flush_reason(self):
        with patch("app.services.template_manager.get_template_manager") as get_manager:
            get_manager.return_value.list_templates.return_value = []
            handler = AudioStreamHandler(FakeEngine(), self.config)

        handler.audio_buffer.extend(b"\x01\x00" * 16000)

        result = handler.flush()

        self.assertEqual(result["flush_reason"], "manual_flush")


if __name__ == "__main__":
    unittest.main()
