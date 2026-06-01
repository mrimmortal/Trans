import unittest

from app.services.tts.base import TTSConfigError, TTSProviderError
from app.services.tts.service import TTSService


class RecordingTTSProvider:
    def __init__(self):
        self.calls = []

    def synthesize(self, text, voice=None, lang=None):
        self.calls.append((text, voice, lang))
        return b"RIFFfake-wav-bytes"


class TTSServiceTests(unittest.TestCase):
    def test_synthesize_delegates_to_provider(self):
        provider = RecordingTTSProvider()
        service = TTSService(provider)

        audio = service.synthesize("  hello  ", voice=" M1 ", lang=" en ")

        self.assertEqual(audio, b"RIFFfake-wav-bytes")
        self.assertEqual(provider.calls, [("hello", "M1", "en")])

    def test_blank_text_raises_value_error_before_provider_call(self):
        provider = RecordingTTSProvider()
        service = TTSService(provider)

        with self.assertRaises(ValueError):
            service.synthesize("   ")

        self.assertEqual(provider.calls, [])

    def test_provider_config_error_propagates(self):
        class FailingProvider:
            def synthesize(self, text, voice=None, lang=None):
                raise TTSConfigError("missing dependency")

        with self.assertRaises(TTSConfigError):
            TTSService(FailingProvider()).synthesize("hello")

    def test_provider_error_propagates(self):
        class FailingProvider:
            def synthesize(self, text, voice=None, lang=None):
                raise TTSProviderError("synthesis failed")

        with self.assertRaises(TTSProviderError):
            TTSService(FailingProvider()).synthesize("hello")


if __name__ == "__main__":
    unittest.main()
