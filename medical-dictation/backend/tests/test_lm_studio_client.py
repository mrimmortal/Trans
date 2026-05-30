import json
import unittest

import httpx

from app.services.lm_studio_client import (
    LMStudioClient,
    LMStudioConfigError,
    LMStudioUnavailableError,
)


class StubConfig:
    LM_STUDIO_BASE_URL = "http://127.0.0.1:1234/v1"
    LM_STUDIO_MODEL = "local-model"
    LM_STUDIO_TIMEOUT_SECONDS = 30.0


class LMStudioClientTests(unittest.TestCase):
    def test_missing_base_url_raises_config_error(self):
        class MissingBaseUrl(StubConfig):
            LM_STUDIO_BASE_URL = ""

        client = LMStudioClient(MissingBaseUrl())

        with self.assertRaises(LMStudioConfigError):
            client.respond("hello")

    def test_missing_model_raises_config_error(self):
        class MissingModel(StubConfig):
            LM_STUDIO_MODEL = ""

        client = LMStudioClient(MissingModel())

        with self.assertRaises(LMStudioConfigError):
            client.respond("hello")

    def test_blank_text_raises_value_error(self):
        client = LMStudioClient(StubConfig())

        with self.assertRaises(ValueError):
            client.respond("   ")

    def test_successful_response_returns_text_model_and_provider(self):
        def handler(request):
            self.assertEqual(request.url.path, "/v1/chat/completions")
            self.assertEqual(
                json.loads(request.content),
                {
                    "model": "local-model",
                    "messages": [
                        {"role": "system", "content": "Be concise."},
                        {"role": "user", "content": "hello"},
                    ],
                    "temperature": 0.2,
                },
            )
            return httpx.Response(
                200,
                json={
                    "choices": [
                        {"message": {"content": "Hello back."}},
                    ]
                },
            )

        client = LMStudioClient(StubConfig(), transport=httpx.MockTransport(handler))

        response = client.respond("  hello  ", system_prompt=" Be concise. ")

        self.assertEqual(response.response, "Hello back.")
        self.assertEqual(response.model, "local-model")
        self.assertEqual(response.provider, "lmstudio")

    def test_blank_system_prompt_is_omitted(self):
        def handler(request):
            self.assertEqual(
                json.loads(request.content)["messages"],
                [{"role": "user", "content": "hello"}],
            )
            return httpx.Response(
                200,
                json={
                    "choices": [
                        {"message": {"content": "Hello back."}},
                    ]
                },
            )

        client = LMStudioClient(StubConfig(), transport=httpx.MockTransport(handler))

        client.respond("hello", system_prompt="   ")

    def test_connect_error_maps_to_unavailable_error(self):
        def handler(request):
            raise httpx.ConnectError("offline", request=request)

        client = LMStudioClient(StubConfig(), transport=httpx.MockTransport(handler))

        with self.assertRaises(LMStudioUnavailableError):
            client.respond("hello")

    def test_timeout_maps_to_unavailable_error(self):
        def handler(request):
            raise httpx.TimeoutException("timed out", request=request)

        client = LMStudioClient(StubConfig(), transport=httpx.MockTransport(handler))

        with self.assertRaises(LMStudioUnavailableError):
            client.respond("hello")

    def test_non_2xx_response_maps_to_unavailable_error(self):
        client = LMStudioClient(
            StubConfig(),
            transport=httpx.MockTransport(lambda request: httpx.Response(500, json={"error": "failed"})),
        )

        with self.assertRaises(LMStudioUnavailableError):
            client.respond("hello")

    def test_malformed_json_maps_to_unavailable_error(self):
        client = LMStudioClient(
            StubConfig(),
            transport=httpx.MockTransport(lambda request: httpx.Response(200, content=b"not json")),
        )

        with self.assertRaises(LMStudioUnavailableError):
            client.respond("hello")

    def test_missing_choice_content_maps_to_unavailable_error(self):
        client = LMStudioClient(
            StubConfig(),
            transport=httpx.MockTransport(lambda request: httpx.Response(200, json={"choices": []})),
        )

        with self.assertRaises(LMStudioUnavailableError):
            client.respond("hello")


if __name__ == "__main__":
    unittest.main()
