import unittest

from app.models.schemas import LLMRespondResponse
from app.services.llm.base import LLMConfigError, LLMProviderError
from app.services.llm.service import LLMService


class RecordingLLMProvider:
    def __init__(self):
        self.calls = []

    def respond(self, text, system_prompt=None):
        self.calls.append((text, system_prompt))
        return LLMRespondResponse(response="assistant response", model="local-model")


class LLMServiceTests(unittest.TestCase):
    def test_respond_delegates_to_provider(self):
        provider = RecordingLLMProvider()
        service = LLMService(provider)

        response = service.respond("  hello  ", system_prompt=" Be concise. ")

        self.assertEqual(response.response, "assistant response")
        self.assertEqual(response.model, "local-model")
        self.assertEqual(response.provider, "lmstudio")
        self.assertEqual(provider.calls, [("hello", "Be concise.")])

    def test_blank_text_raises_value_error_before_provider_call(self):
        provider = RecordingLLMProvider()
        service = LLMService(provider)

        with self.assertRaises(ValueError):
            service.respond("   ")

        self.assertEqual(provider.calls, [])

    def test_provider_config_error_propagates(self):
        class FailingProvider:
            def respond(self, text, system_prompt=None):
                raise LLMConfigError("missing config")

        with self.assertRaises(LLMConfigError):
            LLMService(FailingProvider()).respond("hello")

    def test_provider_error_propagates(self):
        class FailingProvider:
            def respond(self, text, system_prompt=None):
                raise LLMProviderError("offline")

        with self.assertRaises(LLMProviderError):
            LLMService(FailingProvider()).respond("hello")


if __name__ == "__main__":
    unittest.main()
