import unittest
from pathlib import Path

from app.services.tts.config import SupertonicSettings
from app.services.tts.supertonic import (
    SupertonicConfigError,
    SupertonicSynthesisError,
    SupertonicProvider,
)


class StubConfig:
    provider = "supertonic"
    voice = "M1"
    lang = "en"
    output_dir = ""


class FakeSupertonicTTS:
    def __init__(self, auto_download):
        self.auto_download = auto_download
        self.voice_name = None
        self.synthesize_kwargs = None

    def get_voice_style(self, voice_name):
        self.voice_name = voice_name
        return {"voice": voice_name}

    def synthesize(self, **kwargs):
        self.synthesize_kwargs = kwargs
        return "fake-wav-array", [1.0]

    def save_audio(self, wav, output_path):
        Path(output_path).write_bytes(b"RIFFfake-wav-bytes")


class SupertonicProviderTests(unittest.TestCase):
    def settings(self, config=StubConfig):
        return SupertonicSettings(
            provider=config.provider,
            voice=config.voice,
            lang=config.lang,
            output_dir=config.output_dir,
        )

    def test_unsupported_provider_raises_config_error(self):
        class UnsupportedProvider(StubConfig):
            provider = "other"

        provider = SupertonicProvider(self.settings(UnsupportedProvider), tts_factory=FakeSupertonicTTS)

        with self.assertRaises(SupertonicConfigError):
            provider.synthesize("hello")

    def test_blank_text_raises_value_error(self):
        provider = SupertonicProvider(self.settings(), tts_factory=FakeSupertonicTTS)

        with self.assertRaises(ValueError):
            provider.synthesize("   ")

    def test_missing_dependency_raises_config_error(self):
        def missing_dependency_factory(auto_download):
            raise ImportError("No module named supertonic")

        provider = SupertonicProvider(self.settings(), tts_factory=missing_dependency_factory)

        with self.assertRaises(SupertonicConfigError):
            provider.synthesize("hello")

    def test_model_load_error_raises_synthesis_error(self):
        def failing_factory(auto_download):
            raise RuntimeError("download failed")

        provider = SupertonicProvider(self.settings(), tts_factory=failing_factory)

        with self.assertRaises(SupertonicSynthesisError):
            provider.synthesize("hello")

    def test_successful_synthesis_returns_wav_bytes_with_defaults(self):
        created = []

        def factory(auto_download):
            instance = FakeSupertonicTTS(auto_download=auto_download)
            created.append(instance)
            return instance

        provider = SupertonicProvider(self.settings(), tts_factory=factory)

        audio = provider.synthesize("  hello  ")

        self.assertEqual(audio, b"RIFFfake-wav-bytes")
        self.assertTrue(created[0].auto_download)
        self.assertEqual(created[0].voice_name, "M1")
        self.assertEqual(
            created[0].synthesize_kwargs,
            {
                "text": "hello",
                "lang": "en",
                "voice_style": {"voice": "M1"},
                "total_steps": 8,
            },
        )

    def test_request_voice_and_lang_override_defaults(self):
        created = []

        def factory(auto_download):
            instance = FakeSupertonicTTS(auto_download=auto_download)
            created.append(instance)
            return instance

        provider = SupertonicProvider(self.settings(), tts_factory=factory)

        provider.synthesize("hello", voice="F1", lang="es")

        self.assertEqual(created[0].voice_name, "F1")
        self.assertEqual(created[0].synthesize_kwargs["lang"], "es")

    def test_empty_wav_output_raises_synthesis_error(self):
        class EmptyAudioTTS(FakeSupertonicTTS):
            def save_audio(self, wav, output_path):
                Path(output_path).write_bytes(b"")

        provider = SupertonicProvider(self.settings(), tts_factory=EmptyAudioTTS)

        with self.assertRaises(SupertonicSynthesisError):
            provider.synthesize("hello")

    def test_temp_file_is_removed_after_synthesis(self):
        output_paths = []

        class TrackingTTS(FakeSupertonicTTS):
            def save_audio(self, wav, output_path):
                output_paths.append(Path(output_path))
                super().save_audio(wav, output_path)

        provider = SupertonicProvider(self.settings(), tts_factory=TrackingTTS)

        provider.synthesize("hello")

        self.assertEqual(len(output_paths), 1)
        self.assertFalse(output_paths[0].exists())


if __name__ == "__main__":
    unittest.main()
