import unittest
from types import SimpleNamespace

from app.observability.metrics import STTMetrics
from app.websocket.audio_stream_handler import AudioStreamHandler


class FakeEngine:
    def detect_speech(self, audio_bytes):
        return {"has_speech": True, "speech_prob": 0.9, "speech_segments": []}

    def transcribe_audio_bytes(self, audio_bytes):
        return {
            "text": "project is stable",
            "processing_time_ms": 250.0,
            "error": None,
        }


class STTMetricsTests(unittest.TestCase):
    def setUp(self):
        self.config = SimpleNamespace(
            SAMPLE_RATE=16000,
            CHANNELS=1,
            SAMPLE_WIDTH=2,
            MIN_AUDIO_SAMPLES=8000,
            MIN_CHUNK_SIZE_BYTES=19200,
            MAX_CHUNK_SIZE_BYTES=192000,
            OVERLAP_SIZE_BYTES=16000,
            MODEL_SIZE="base",
            DEVICE="cpu",
            COMPUTE_TYPE="int8",
        )

    def test_audio_stream_handler_records_process_level_stt_metrics(self):
        metrics = STTMetrics.from_config(self.config, vad_enabled=True)
        handler = AudioStreamHandler(FakeEngine(), self.config, metrics=metrics)
        handler.pending_flush_reason = "natural_pause"
        handler.audio_buffer.extend(b"\x01\x00" * 16000)
        handler.has_speech_in_buffer = True

        result = handler._transcribe_buffer()

        snapshot = metrics.snapshot()
        self.assertEqual(result["text"], "project is stable")
        self.assertEqual(snapshot["model_size"], "base")
        self.assertEqual(snapshot["device"], "cpu")
        self.assertEqual(snapshot["compute_type"], "int8")
        self.assertTrue(snapshot["vad_enabled"])
        self.assertEqual(snapshot["sample_rate"], 16000)
        self.assertEqual(snapshot["channels"], 1)
        self.assertEqual(snapshot["transcriptions_count"], 1)
        self.assertEqual(snapshot["empty_transcription_count"], 0)
        self.assertEqual(snapshot["last_audio_duration_seconds"], 1.0)
        self.assertEqual(snapshot["last_processing_time_ms"], 250.0)
        self.assertEqual(snapshot["last_real_time_factor"], 0.25)
        self.assertEqual(snapshot["last_flush_reason"], "natural_pause")
        self.assertEqual(snapshot["average_processing_time_ms"], 250.0)
        self.assertEqual(snapshot["average_real_time_factor"], 0.25)


if __name__ == "__main__":
    unittest.main()
