import unittest

from app.services.command_processor import CommandProcessor


class VoiceCommandContractTests(unittest.TestCase):
    def setUp(self):
        self.processor = CommandProcessor()

    def test_formatting_commands_do_not_insert_markdown_markers(self):
        processed_text, commands = self.processor.process("bold")

        self.assertEqual(processed_text, "")
        self.assertEqual(len(commands), 1)
        self.assertEqual(commands[0].action, "bold")

    def test_editing_commands_do_not_insert_text(self):
        processed_text, commands = self.processor.process("undo")

        self.assertEqual(processed_text, "")
        self.assertEqual(len(commands), 1)
        self.assertEqual(commands[0].action, "undo")

    def test_navigation_commands_with_actions_do_not_insert_text(self):
        processed_text, commands = self.processor.process("go to start")

        self.assertEqual(processed_text, "")
        self.assertEqual(len(commands), 1)
        self.assertEqual(commands[0].action, "go_to_start")

    def test_punctuation_commands_still_insert_punctuation(self):
        processed_text, commands = self.processor.process("period")

        self.assertEqual(processed_text, ".")
        self.assertEqual(len(commands), 1)
        self.assertEqual(commands[0].command_type.value, "punctuation")

    def test_template_commands_still_insert_template_text(self):
        processed_text, commands = self.processor.process("insert vitals")

        self.assertIn("Vital Signs", processed_text)
        self.assertEqual(len(commands), 1)
        self.assertEqual(commands[0].action, "vitals")


if __name__ == "__main__":
    unittest.main()
