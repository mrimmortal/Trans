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
        self.assertIn("dictation", prompt.lower())
        self.assertIn(AudioConfig.TRANSCRIPTION_CONTEXT_PROMPT, prompt)
        self.assertNotIn("medical", prompt.lower())
        self.assertNotIn("clinical", prompt.lower())

    def test_initial_prompt_does_not_seed_domain_specific_facts(self):
        prompt = AudioConfig.get_initial_prompt().lower()

        self.assertNotIn("symptoms", prompt)
        self.assertNotIn("diagnoses", prompt)
        self.assertNotIn("medications", prompt)
        self.assertNotIn("patient presents with hypertension", prompt)
        self.assertNotIn("metformin 500mg", prompt)
        self.assertNotIn("hba1c 7.2", prompt)
        self.assertNotIn("prescribe amoxicillin", prompt)


if __name__ == "__main__":
    unittest.main()
