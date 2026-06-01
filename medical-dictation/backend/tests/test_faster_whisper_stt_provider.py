import unittest

from app.audio_config import AudioConfig
from app.services.stt.config import get_faster_whisper_settings
from app.services.stt.faster_whisper import FasterWhisperSTTProvider


class FasterWhisperSTTProviderTests(unittest.TestCase):
    def test_settings_are_built_from_audio_config(self):
        config = AudioConfig()

        settings = get_faster_whisper_settings(config)

        self.assertEqual(settings.model_size, config.MODEL_SIZE)
        self.assertEqual(settings.device, config.DEVICE)
        self.assertEqual(settings.compute_type, config.COMPUTE_TYPE)
        self.assertEqual(settings.sample_rate, config.SAMPLE_RATE)

    def test_provider_exposes_streaming_stt_contract(self):
        self.assertTrue(hasattr(FasterWhisperSTTProvider, "detect_speech"))
        self.assertTrue(hasattr(FasterWhisperSTTProvider, "transcribe_audio_bytes"))


if __name__ == "__main__":
    unittest.main()
