import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.api.tts_routes import SupertonicConfigError, SupertonicSynthesisError
from app.main import app


class TTSRoutesTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_synthesize_rejects_empty_text(self):
        response = self.client.post("/tts/synthesize", json={"text": "   "})

        self.assertEqual(response.status_code, 422)

    def test_config_error_returns_503(self):
        with patch("app.api.tts_routes.create_tts_service") as create_service:
            create_service.return_value.synthesize.side_effect = SupertonicConfigError("supertonic is not installed")

            response = self.client.post(
                "/tts/synthesize",
                json={"text": "hello"},
                headers={"x-request-id": "tts-config-1"},
            )

        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.headers["x-request-id"], "tts-config-1")
        self.assertEqual(
            response.json()["detail"],
            {
                "code": "TTS_CONFIG_ERROR",
                "message": "supertonic is not installed",
                "request_id": "tts-config-1",
            },
        )

    def test_synthesis_error_returns_502(self):
        with patch("app.api.tts_routes.create_tts_service") as create_service:
            create_service.return_value.synthesize.side_effect = SupertonicSynthesisError("model download failed")

            response = self.client.post(
                "/tts/synthesize",
                json={"text": "hello"},
                headers={"x-request-id": "tts-synthesis-1"},
            )

        self.assertEqual(response.status_code, 502)
        self.assertEqual(response.headers["x-request-id"], "tts-synthesis-1")
        self.assertEqual(
            response.json()["detail"],
            {
                "code": "TTS_SYNTHESIS_ERROR",
                "message": "model download failed",
                "request_id": "tts-synthesis-1",
            },
        )

    def test_success_returns_wav_audio(self):
        with patch("app.api.tts_routes.create_tts_service") as create_service:
            create_service.return_value.synthesize.return_value = b"RIFFfake-wav-bytes"

            response = self.client.post(
                "/tts/synthesize",
                json={"text": "hello", "voice": "F1", "lang": "es"},
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["content-type"], "audio/wav")
        self.assertEqual(response.content, b"RIFFfake-wav-bytes")
        create_service.return_value.synthesize.assert_called_once_with("hello", voice="F1", lang="es")


if __name__ == "__main__":
    unittest.main()
