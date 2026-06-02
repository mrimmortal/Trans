import logging
import unittest

from fastapi.testclient import TestClient

from app.main import app


class ObservabilityTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_request_id_header_is_generated_when_missing(self):
        response = self.client.get("/")

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.headers["x-request-id"])

    def test_request_id_header_uses_client_value(self):
        response = self.client.get("/", headers={"x-request-id": "debug-request-1"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["x-request-id"], "debug-request-1")

    def test_safe_error_message_does_not_include_trace_or_secret(self):
        from app.observability.safe_errors import safe_error_message

        error = RuntimeError("failed with SECRET_TOKEN=abc123 at /Users/example/app.py")

        message = safe_error_message(error)

        self.assertEqual(message, "failed with [redacted] at [path]")

    def test_structured_log_event_uses_safe_metadata(self):
        from app.observability.events import log_event

        with self.assertLogs("app.observability.events", level=logging.INFO) as captured:
            log_event(
                category="LLM",
                event="llm.respond",
                status="success",
                provider="lmstudio",
                duration_ms=12.345,
                request_id="req-1",
                text_length=42,
            )

        self.assertIn('"category": "LLM"', captured.output[0])
        self.assertIn('"event": "llm.respond"', captured.output[0])
        self.assertIn('"request_id": "req-1"', captured.output[0])
        self.assertIn('"text_length": 42', captured.output[0])


if __name__ == "__main__":
    unittest.main()
