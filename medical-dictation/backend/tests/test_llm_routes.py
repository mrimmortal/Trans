import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.api.llm_routes import LMStudioConfigError, LMStudioUnavailableError
from app.main import app
from app.models.schemas import LLMRespondResponse


class LLMRoutesTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_respond_rejects_empty_text(self):
        response = self.client.post("/llm/respond", json={"text": "   "})

        self.assertEqual(response.status_code, 422)

    def test_missing_config_returns_503(self):
        with patch("app.api.llm_routes.create_llm_service") as create_service:
            create_service.return_value.respond.side_effect = LMStudioConfigError("missing config")

            response = self.client.post("/llm/respond", json={"text": "hello"})

        self.assertEqual(response.status_code, 503)
        self.assertEqual(
            response.json()["detail"],
            {"code": "LM_STUDIO_CONFIG_ERROR", "message": "missing config"},
        )

    def test_unavailable_client_returns_502(self):
        with patch("app.api.llm_routes.create_llm_service") as create_service:
            create_service.return_value.respond.side_effect = LMStudioUnavailableError("offline")

            response = self.client.post("/llm/respond", json={"text": "hello"})

        self.assertEqual(response.status_code, 502)
        self.assertEqual(
            response.json()["detail"],
            {"code": "LM_STUDIO_UNAVAILABLE", "message": "offline"},
        )

    def test_successful_call_returns_lmstudio_response(self):
        with patch("app.api.llm_routes.create_llm_service") as create_service:
            create_service.return_value.respond.return_value = LLMRespondResponse(
                response="Hello back.",
                model="local-model",
            )

            response = self.client.post(
                "/llm/respond",
                json={"text": "hello", "system_prompt": "Be concise."},
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {
                "response": "Hello back.",
                "model": "local-model",
                "provider": "lmstudio",
            },
        )
        create_service.return_value.respond.assert_called_once_with(
            "hello",
            system_prompt="Be concise.",
        )


if __name__ == "__main__":
    unittest.main()
