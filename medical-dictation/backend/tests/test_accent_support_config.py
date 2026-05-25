import os
import unittest
from unittest.mock import patch

from app.audio_config import AudioConfig


class AccentSupportConfigTests(unittest.TestCase):
    def test_accent_support_defaults_are_automatic(self):
        self.assertTrue(AudioConfig.ACCENT_SUPPORT_ENABLED)
        self.assertEqual(AudioConfig.TRANSCRIPTION_LANGUAGE, "en")
        self.assertEqual(AudioConfig.MODEL_SIZE, "base")

    def test_explicit_model_size_is_respected(self):
        with patch.dict(os.environ, {"MODEL_SIZE": "base.en"}):
            class TestConfig(AudioConfig):
                MODEL_SIZE = os.getenv("MODEL_SIZE") or AudioConfig.DEFAULT_ACCENT_MODEL_SIZE

            self.assertEqual(TestConfig.MODEL_SIZE, "base.en")

    def test_initial_prompt_includes_accent_guidance(self):
        prompt = AudioConfig.get_initial_prompt()

        self.assertIn("multiple English accents", prompt)
        self.assertIn("medical dictation", prompt.lower())
        self.assertIn(AudioConfig.MEDICAL_CONTEXT_PROMPT, prompt)


if __name__ == "__main__":
    unittest.main()
