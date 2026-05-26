import unittest
from types import SimpleNamespace
from unittest.mock import patch

from app.main import AudioStreamHandler
from app.services.command_processor import CommandProcessor


class FakeTemplateManager:
    def list_templates(self):
        return [
            {
                "name": "assessment_plan",
                "trigger_phrases": [
                    "assessment and plan",
                    "a and p",
                    "insert assessment",
                    "assessment plan",
                ],
                "content": "ASSESSMENT PLAN CONTENT",
                "category": "notes",
                "description": "Problem-oriented assessment and plan template",
            }
        ]


class TemplateVoiceTriggerTests(unittest.TestCase):
    def test_websocket_handler_registers_database_template_triggers(self):
        config = SimpleNamespace(
            MIN_CHUNK_SIZE_BYTES=32000,
            MAX_CHUNK_SIZE_BYTES=320000,
            OVERLAP_SIZE_BYTES=16000,
        )

        with patch("app.services.template_manager.get_template_manager", return_value=FakeTemplateManager()):
            handler = AudioStreamHandler(
                transcription_engine=SimpleNamespace(),
                config=config,
                domain="medical",
            )

        processed_text, commands = handler.command_processor.process("insert assessment")

        self.assertEqual(processed_text, "ASSESSMENT PLAN CONTENT")
        self.assertEqual(len(commands), 1)
        self.assertEqual(commands[0].action, "assessment_plan")
        self.assertEqual(commands[0].original_text, "insert assessment")

    def test_fresh_command_processor_does_not_know_database_templates_by_default(self):
        processor = CommandProcessor()

        processed_text, commands = processor.process("insert assessment")

        self.assertEqual(processed_text, "insert assessment")
        self.assertEqual(commands, [])


if __name__ == "__main__":
    unittest.main()
