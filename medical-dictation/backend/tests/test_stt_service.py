import unittest

from app.services.stt.base import SpeechDetectionResult, STTConfigError, STTProviderError, TranscriptionResult
from app.services.stt.service import STTService


class FakeSTTProvider:
    def __init__(self):
        self.detect_calls = []
        self.transcribe_calls = []

    def detect_speech(self, audio_bytes) -> SpeechDetectionResult:
        self.detect_calls.append(audio_bytes)
        return {
            "has_speech": True,
            "speech_prob": 0.75,
            "speech_segments": [{"start": 0, "end": 512}],
        }

    def transcribe_audio_bytes(self, audio_bytes) -> TranscriptionResult:
        self.transcribe_calls.append(audio_bytes)
        return {
            "text": "project is stable",
            "is_final": True,
            "confidence": 0.95,
            "processing_time_ms": 12.3,
            "error": None,
        }


class STTServiceTests(unittest.TestCase):
    def test_detect_speech_delegates_to_provider(self):
        provider = FakeSTTProvider()
        service = STTService(provider)

        result = service.detect_speech(b"audio")

        self.assertEqual(provider.detect_calls, [b"audio"])
        self.assertTrue(result["has_speech"])
        self.assertEqual(result["speech_prob"], 0.75)

    def test_transcribe_audio_bytes_delegates_to_provider(self):
        provider = FakeSTTProvider()
        service = STTService(provider)

        result = service.transcribe_audio_bytes(b"audio")

        self.assertEqual(provider.transcribe_calls, [b"audio"])
        self.assertEqual(result["text"], "project is stable")
        self.assertIsNone(result["error"])

    def test_fake_provider_satisfies_typed_result_contracts(self):
        provider = FakeSTTProvider()
        service = STTService(provider)

        speech_result: SpeechDetectionResult = service.detect_speech(b"audio")
        transcription_result: TranscriptionResult = service.transcribe_audio_bytes(b"audio")

        self.assertEqual(set(speech_result), {"has_speech", "speech_prob", "speech_segments"})
        self.assertIn("text", transcription_result)
        self.assertIn("processing_time_ms", transcription_result)
        self.assertIn("error", transcription_result)

    def test_provider_config_error_propagates(self):
        class BrokenProvider(FakeSTTProvider):
            def detect_speech(self, audio_bytes):
                raise STTConfigError("bad config")

        service = STTService(BrokenProvider())

        with self.assertRaises(STTConfigError):
            service.detect_speech(b"audio")

    def test_provider_error_propagates(self):
        class BrokenProvider(FakeSTTProvider):
            def transcribe_audio_bytes(self, audio_bytes):
                raise STTProviderError("provider failed")

        service = STTService(BrokenProvider())

        with self.assertRaises(STTProviderError):
            service.transcribe_audio_bytes(b"audio")


if __name__ == "__main__":
    unittest.main()
