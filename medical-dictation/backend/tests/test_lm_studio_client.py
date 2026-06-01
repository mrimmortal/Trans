import json
import unittest

import httpx

from app.services.llm.config import LMStudioSettings
from app.services.llm.lm_studio import (
    LMStudioProvider,
    LMStudioConfigError,
    LMStudioUnavailableError,
)


class StubConfig:
    base_url = "http://127.0.0.1:1234/v1"
    model = "local-model"
    timeout_seconds = 30.0


class LMStudioProviderTests(unittest.TestCase):
    def settings(self, config=StubConfig):
        return LMStudioSettings(
            base_url=config.base_url,
            model=config.model,
            timeout_seconds=config.timeout_seconds,
        )

    def test_missing_base_url_raises_config_error(self):
        class MissingBaseUrl(StubConfig):
            base_url = ""

        provider = LMStudioProvider(self.settings(MissingBaseUrl))

        with self.assertRaises(LMStudioConfigError):
            provider.respond("hello")

    def test_missing_model_raises_config_error(self):
        class MissingModel(StubConfig):
            model = ""

        provider = LMStudioProvider(self.settings(MissingModel))

        with self.assertRaises(LMStudioConfigError):
            provider.respond("hello")

    def test_blank_text_raises_value_error(self):
        provider = LMStudioProvider(self.settings())

        with self.assertRaises(ValueError):
            provider.respond("   ")

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

        provider = LMStudioProvider(self.settings(), transport=httpx.MockTransport(handler))

        response = provider.respond("  hello  ", system_prompt=" Be concise. ")

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

        provider = LMStudioProvider(self.settings(), transport=httpx.MockTransport(handler))

        provider.respond("hello", system_prompt="   ")

    def test_connect_error_maps_to_unavailable_error(self):
        def handler(request):
            raise httpx.ConnectError("offline", request=request)

        provider = LMStudioProvider(self.settings(), transport=httpx.MockTransport(handler))

        with self.assertRaises(LMStudioUnavailableError):
            provider.respond("hello")

    def test_timeout_maps_to_unavailable_error(self):
        def handler(request):
            raise httpx.TimeoutException("timed out", request=request)

        provider = LMStudioProvider(self.settings(), transport=httpx.MockTransport(handler))

        with self.assertRaises(LMStudioUnavailableError):
            provider.respond("hello")

    def test_non_2xx_response_maps_to_unavailable_error(self):
        provider = LMStudioProvider(
            self.settings(),
            transport=httpx.MockTransport(lambda request: httpx.Response(500, json={"error": "failed"})),
        )

        with self.assertRaises(LMStudioUnavailableError):
            provider.respond("hello")

    def test_malformed_json_maps_to_unavailable_error(self):
        provider = LMStudioProvider(
            self.settings(),
            transport=httpx.MockTransport(lambda request: httpx.Response(200, content=b"not json")),
        )

        with self.assertRaises(LMStudioUnavailableError):
            provider.respond("hello")

    def test_missing_choice_content_maps_to_unavailable_error(self):
        provider = LMStudioProvider(
            self.settings(),
            transport=httpx.MockTransport(lambda request: httpx.Response(200, json={"choices": []})),
        )

        with self.assertRaises(LMStudioUnavailableError):
            provider.respond("hello")


if __name__ == "__main__":
    unittest.main()
