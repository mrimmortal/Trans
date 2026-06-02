import unittest
from types import SimpleNamespace
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.main import app


class FakeSTTService:
    model = object()
    vad_model = object()


class DiagnosticsRoutesTests(unittest.TestCase):
    def setUp(self):
        app.state.config = SimpleNamespace(
            ENVIRONMENT="development",
            MODEL_SIZE="base",
            DEVICE="cpu",
            COMPUTE_TYPE="int8",
            SAMPLE_RATE=16000,
            CHANNELS=1,
            LM_STUDIO_BASE_URL="http://127.0.0.1:1234/v1",
            LM_STUDIO_MODEL="local-model",
            LM_STUDIO_TIMEOUT_SECONDS=1.0,
            TTS_PROVIDER="supertonic",
            SUPERTONIC_VOICE="M1",
            SUPERTONIC_LANG="en",
            TTS_OUTPUT_DIR="",
        )
        app.state.stt_service = FakeSTTService()
        app.state.stt_metrics = None
        self.client = TestClient(app)

    def test_aggregate_diagnostics_returns_safe_provider_statuses(self):
        with patch("app.services.llm.lm_studio.LMStudioProvider.check_health") as llm_health:
            with patch("app.services.tts.supertonic.SupertonicProvider.check_health") as tts_health:
                llm_health.return_value = {"status": "healthy", "reachable": True, "last_error": None}
                tts_health.return_value = {"status": "healthy", "available": True, "last_error": None}

                response = self.client.get("/diagnostics", headers={"x-request-id": "diag-1"})

        body = response.json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["x-request-id"], "diag-1")
        self.assertEqual(body["request_id"], "diag-1")
        self.assertEqual(body["status"], "healthy")
        self.assertEqual(body["stt"]["provider"], "faster_whisper")
        self.assertEqual(body["stt"]["model_size"], "base")
        self.assertTrue(body["stt"]["loaded"])
        self.assertEqual(body["llm"]["provider"], "lmstudio")
        self.assertTrue(body["llm"]["configured"])
        self.assertTrue(body["llm"]["reachable"])
        self.assertEqual(body["tts"]["provider"], "supertonic")
        self.assertTrue(body["tts"]["available"])
        self.assertNotIn("LM_STUDIO_BASE_URL", str(body))

    def test_llm_diagnostics_reports_missing_model_without_crashing(self):
        app.state.config.LM_STUDIO_MODEL = ""

        response = self.client.get("/diagnostics/llm")

        body = response.json()["llm"]
        self.assertEqual(response.status_code, 200)
        self.assertEqual(body["status"], "unhealthy")
        self.assertFalse(body["configured"])
        self.assertFalse(body["model_configured"])
        self.assertEqual(body["last_error"], "LM_STUDIO_MODEL is required")

    def test_tts_diagnostics_reports_unavailable_provider_safely(self):
        with patch("app.services.tts.supertonic.SupertonicProvider.check_health") as tts_health:
            tts_health.return_value = {
                "status": "unhealthy",
                "available": False,
                "last_error": "Supertonic is not installed",
            }

            response = self.client.get("/diagnostics/tts")

        body = response.json()["tts"]
        self.assertEqual(response.status_code, 200)
        self.assertEqual(body["status"], "unhealthy")
        self.assertFalse(body["available"])
        self.assertEqual(body["last_error"], "Supertonic is not installed")


if __name__ == "__main__":
    unittest.main()
