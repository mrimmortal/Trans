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

    def test_sanitize_stream_text_removes_trailing_hyphen_fragment(self):
        with patch("app.services.template_manager.get_template_manager") as get_manager:
            get_manager.return_value.list_templates.return_value = []
            handler = AudioStreamHandler(FakeEngine(), self.config)

        text = handler._sanitize_stream_text("Filtration occurs in the glomeric-")

        self.assertEqual(text, "Filtration occurs in the")

    def test_sanitize_stream_text_removes_repeated_boundary_words(self):
        with patch("app.services.template_manager.get_template_manager") as get_manager:
            get_manager.return_value.list_templates.return_value = []
            handler = AudioStreamHandler(FakeEngine(), self.config)

        handler.recent_emitted_words = ["filtration", "occurs", "in", "the", "glomerulus"]

        text = handler._sanitize_stream_text("In the glomerulus, water is filtered.")

        self.assertEqual(text, "Water is filtered.")

    def test_sanitize_stream_text_removes_pause_filler_and_repeated_phrase(self):
        with patch("app.services.template_manager.get_template_manager") as get_manager:
            get_manager.return_value.list_templates.return_value = []
            handler = AudioStreamHandler(FakeEngine(), self.config)

        text = handler._sanitize_stream_text("Filtration occurs in the Pause in the glomerulus.")

        self.assertEqual(text, "Filtration occurs in the glomerulus.")

    def test_sanitize_stream_text_tolerates_one_character_boundary_mismatch(self):
        with patch("app.services.template_manager.get_template_manager") as get_manager:
            get_manager.return_value.list_templates.return_value = []
            handler = AudioStreamHandler(FakeEngine(), self.config)

        handler._remember_emitted_text("alpha bravo charlie")

        text = handler._sanitize_stream_text("Alpha brava charlie delta echo.")

        self.assertEqual(text, "Delta echo.")

    def test_sanitize_stream_text_suppresses_repeated_paragraph_prefix(self):
        with patch("app.services.template_manager.get_template_manager") as get_manager:
            get_manager.return_value.list_templates.return_value = []
            handler = AudioStreamHandler(FakeEngine(), self.config)

        emitted = (
            "The kidney participates in the control of the volume of various body fluids, "
            "fluid osmolality, acid-base balance. Various electrolyte concentrations. "
            "And removal of toxins. Filtration occurs in the glomerulus."
        )
        handler._remember_emitted_text(emitted)

        text = handler._sanitize_stream_text(
            "The kidney participates in the control of the volume of various body fluids, "
            "fluid osmolality, acid-base balance. Various electrolyte concentrations. "
            "And removal of toxins. Filtration occurs in the glomerulus, one-fifth of the blood volume."
        )

        self.assertEqual(text, "One-fifth of the blood volume.")


if __name__ == "__main__":
    unittest.main()
