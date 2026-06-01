import unittest
from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parents[1]


class BackendArchitectureRulesTests(unittest.TestCase):
    def read_source(self, relative_path: str) -> str:
        return (BACKEND_ROOT / relative_path).read_text(encoding="utf-8")

    def test_cuda_bootstrap_is_centralized(self):
        self.assertTrue((BACKEND_ROOT / "app/infrastructure/cuda_bootstrap.py").exists())

        main_source = self.read_source("app/main.py")
        engine_source = self.read_source("app/services/transcription_engine.py")

        self.assertNotIn("nvidia_base", main_source)
        self.assertNotIn("nvidia_base", engine_source)
        self.assertIn("configure_windows_cuda_paths", engine_source)

    def test_transcription_engine_delegates_audio_and_text_helpers(self):
        self.assertTrue((BACKEND_ROOT / "app/services/audio_processing.py").exists())
        self.assertTrue((BACKEND_ROOT / "app/services/transcription_text.py").exists())

        engine_source = self.read_source("app/services/transcription_engine.py")

        self.assertIn("from app.services.audio_processing import", engine_source)
        self.assertIn("from app.services.transcription_text import", engine_source)
        self.assertNotIn("if __name__ == \"__main__\"", engine_source)

    def test_real_env_files_are_not_present_in_backend_tree(self):
        real_env_files = [
            path.name
            for path in BACKEND_ROOT.glob(".env*")
            if path.name != ".env.example"
        ]

        self.assertEqual(real_env_files, [])

    def test_schema_file_exposes_only_used_api_models(self):
        source = self.read_source("app/models/schemas.py")

        self.assertIn("class ConnectionResponse", source)
        self.assertIn("class ErrorResponse", source)
        self.assertIn("class LLMRespondRequest", source)
        self.assertIn("class LLMRespondResponse", source)
        self.assertIn("class TTSSynthesizeRequest", source)
        self.assertNotIn("class DictationNote", source)
        self.assertNotIn("class TranscriptionRequest", source)
        self.assertNotIn("class SessionStart", source)

    def test_local_ai_integrations_use_service_provider_boundaries(self):
        expected_paths = [
            "app/services/llm/base.py",
            "app/services/llm/config.py",
            "app/services/llm/lm_studio.py",
            "app/services/llm/service.py",
            "app/services/tts/base.py",
            "app/services/tts/config.py",
            "app/services/tts/service.py",
            "app/services/tts/supertonic.py",
        ]

        for relative_path in expected_paths:
            self.assertTrue((BACKEND_ROOT / relative_path).exists(), relative_path)

        self.assertFalse((BACKEND_ROOT / "app/services/lm_studio_client.py").exists())
        self.assertFalse((BACKEND_ROOT / "app/services/supertonic_tts_client.py").exists())

        llm_route_source = self.read_source("app/api/llm_routes.py")
        tts_route_source = self.read_source("app/api/tts_routes.py")

        self.assertIn("LLMService", llm_route_source)
        self.assertIn("LMStudioProvider", llm_route_source)
        self.assertIn("TTSService", tts_route_source)
        self.assertIn("SupertonicProvider", tts_route_source)

    def test_command_processor_comments_stay_domain_neutral(self):
        source = self.read_source("app/services/command_processor.py").lower()

        self.assertNotIn("patient", source)
        self.assertNotIn("diabetes", source)
        self.assertNotIn("dr. john smith", source)


if __name__ == "__main__":
    unittest.main()
