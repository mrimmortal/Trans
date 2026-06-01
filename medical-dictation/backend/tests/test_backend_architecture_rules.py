import unittest
from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parents[1]


class BackendArchitectureRulesTests(unittest.TestCase):
    def read_source(self, relative_path: str) -> str:
        return (BACKEND_ROOT / relative_path).read_text(encoding="utf-8")

    def test_cuda_bootstrap_is_centralized(self):
        self.assertTrue((BACKEND_ROOT / "app/infrastructure/cuda_bootstrap.py").exists())

        main_source = self.read_source("app/main.py")
        engine_source = self.read_source("app/services/stt/faster_whisper.py")

        self.assertNotIn("nvidia_base", main_source)
        self.assertNotIn("nvidia_base", engine_source)
        self.assertIn("configure_windows_cuda_paths", engine_source)

    def test_faster_whisper_provider_delegates_audio_and_text_helpers(self):
        self.assertTrue((BACKEND_ROOT / "app/services/stt/audio_processing.py").exists())
        self.assertTrue((BACKEND_ROOT / "app/services/stt/transcription_text.py").exists())

        engine_source = self.read_source("app/services/stt/faster_whisper.py")

        self.assertIn("from app.services.stt.audio_processing import", engine_source)
        self.assertIn("from app.services.stt.transcription_text import", engine_source)
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
            "app/dependencies.py",
            "app/services/llm/base.py",
            "app/services/llm/config.py",
            "app/services/llm/lm_studio.py",
            "app/services/llm/service.py",
            "app/services/tts/base.py",
            "app/services/tts/config.py",
            "app/services/tts/service.py",
            "app/services/tts/supertonic.py",
            "app/services/commands/processor.py",
            "app/services/stt/base.py",
            "app/services/stt/config.py",
            "app/services/stt/service.py",
            "app/services/stt/faster_whisper.py",
        ]

        for relative_path in expected_paths:
            self.assertTrue((BACKEND_ROOT / relative_path).exists(), relative_path)

        self.assertFalse((BACKEND_ROOT / "app/services/lm_studio_client.py").exists())
        self.assertFalse((BACKEND_ROOT / "app/services/supertonic_tts_client.py").exists())
        self.assertFalse((BACKEND_ROOT / "app/services/transcription_engine.py").exists())
        self.assertFalse((BACKEND_ROOT / "app/services/command_processor.py").exists())

        llm_route_source = self.read_source("app/api/llm_routes.py")
        tts_route_source = self.read_source("app/api/tts_routes.py")
        system_route_source = self.read_source("app/api/system_routes.py")
        dependencies_source = self.read_source("app/dependencies.py")
        main_source = self.read_source("app/main.py")
        handler_source = self.read_source("app/websocket/audio_stream_handler.py")

        self.assertIn("create_llm_service", llm_route_source)
        self.assertIn("create_tts_service", tts_route_source)
        self.assertIn("create_stt_service", main_source)
        self.assertIn("def get_config", system_route_source)
        self.assertIn("LLMService", dependencies_source)
        self.assertIn("LMStudioProvider", dependencies_source)
        self.assertIn("TTSService", dependencies_source)
        self.assertIn("SupertonicProvider", dependencies_source)
        self.assertIn("STTService", dependencies_source)
        self.assertIn("FasterWhisperSTTProvider", dependencies_source)
        self.assertIn("STTProvider", handler_source)

    def test_domain_registry_exposes_extension_api(self):
        registry_source = self.read_source("app/domains/registry.py")
        system_route_source = self.read_source("app/api/system_routes.py")
        response_source = self.read_source("app/websocket/responses.py")

        self.assertIn("def register_domain", registry_source)
        self.assertIn("def get_available_domains", registry_source)
        self.assertNotIn('"available": ["general"]', system_route_source)
        self.assertNotIn('"available_domains": ["general"]', response_source)

    def test_command_processor_comments_stay_domain_neutral(self):
        source = self.read_source("app/services/commands/processor.py").lower()

        self.assertNotIn("patient", source)
        self.assertNotIn("diabetes", source)
        self.assertNotIn("dr. john smith", source)

    def test_system_routes_are_split_from_main(self):
        main_source = self.read_source("app/main.py")
        system_route_source = self.read_source("app/api/system_routes.py")

        self.assertIn("system_router", main_source)
        self.assertNotIn("@app.get(\"/\")", main_source)
        self.assertNotIn("@app.get(\"/health\")", main_source)
        self.assertNotIn("@app.get(\"/config\")", main_source)
        self.assertIn("@router.get(\"/\")", system_route_source)
        self.assertIn("@router.get(\"/health\")", system_route_source)
        self.assertIn("@router.get(\"/config\")", system_route_source)


if __name__ == "__main__":
    unittest.main()
