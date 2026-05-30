import unittest

from app.audio_config import AudioConfig, parse_cors_origins


class ParseCorsOriginsTests(unittest.TestCase):
    def test_defaults_to_local_frontend_origins_when_empty(self):
        self.assertEqual(
            parse_cors_origins(None),
            ["http://localhost:3000", "http://127.0.0.1:3000"],
        )

    def test_parses_comma_separated_origins(self):
        self.assertEqual(
            parse_cors_origins("https://uat.example.com, http://localhost:3000/"),
            ["https://uat.example.com", "http://localhost:3000"],
        )

    def test_ignores_blank_entries(self):
        self.assertEqual(
            parse_cors_origins("https://uat.example.com, ,"),
            ["https://uat.example.com"],
        )

    def test_tts_defaults_are_supertonic(self):
        self.assertEqual(AudioConfig.TTS_PROVIDER, "supertonic")
        self.assertEqual(AudioConfig.SUPERTONIC_VOICE, "M1")
        self.assertEqual(AudioConfig.SUPERTONIC_LANG, "en")
        self.assertEqual(AudioConfig.TTS_OUTPUT_DIR, "")


if __name__ == "__main__":
    unittest.main()
