import unittest
from types import SimpleNamespace
from unittest.mock import patch

from app.dependencies import create_llm_service, create_stt_service, create_tts_service
from app.services.llm.service import LLMService
from app.services.stt.service import STTService
from app.services.tts.service import TTSService


class DependencyFactoryTests(unittest.TestCase):
    def test_create_stt_service_wraps_faster_whisper_provider(self):
        config = SimpleNamespace()

        with patch("app.dependencies.FasterWhisperSTTProvider") as provider_class:
            service = create_stt_service(config)

        provider_class.assert_called_once_with(config)
        self.assertIsInstance(service, STTService)

    def test_create_llm_service_wraps_lm_studio_provider(self):
        config = SimpleNamespace(
            LM_STUDIO_BASE_URL="http://localhost:1234/v1",
            LM_STUDIO_MODEL="local-model",
            LM_STUDIO_TIMEOUT_SECONDS=10.0,
        )

        service = create_llm_service(config)

        self.assertIsInstance(service, LLMService)

    def test_create_tts_service_wraps_supertonic_provider(self):
        config = SimpleNamespace(
            TTS_PROVIDER="supertonic",
            SUPERTONIC_VOICE="M1",
            SUPERTONIC_LANG="en",
            TTS_OUTPUT_DIR="",
        )

        service = create_tts_service(config)

        self.assertIsInstance(service, TTSService)


if __name__ == "__main__":
    unittest.main()
