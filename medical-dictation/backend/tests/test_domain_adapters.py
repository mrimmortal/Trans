import unittest
from unittest.mock import patch

from app.domains.general import GeneralDomainAdapter
from app.domains.medical import MedicalDomainAdapter
from app.domains.registry import get_domain_adapter


class DomainAdapterTests(unittest.TestCase):
    def test_general_domain_returns_raw_text_without_commands(self):
        adapter = GeneralDomainAdapter()

        processed_text, commands = adapter.process_transcript("patient takes aspirin")

        self.assertEqual(processed_text, "patient takes aspirin")
        self.assertEqual(commands, [])
        self.assertFalse(adapter.commands_enabled)
        self.assertEqual(adapter.command_processor.get_available_commands(), {})

    def test_medical_domain_applies_formatter_and_commands(self):
        with patch("app.services.template_manager.get_template_manager") as get_manager:
            get_manager.return_value.list_templates.return_value = []
            adapter = MedicalDomainAdapter()

        processed_text, commands = adapter.process_transcript("patient takes aspirin period")

        self.assertEqual(processed_text, "Patient takes Aspirin.")
        self.assertEqual(len(commands), 1)
        self.assertEqual(commands[0].action, "punctuation")
        self.assertTrue(adapter.commands_enabled)

    def test_registry_falls_back_to_general_for_unknown_domain(self):
        adapter = get_domain_adapter("unknown")

        self.assertIsInstance(adapter, GeneralDomainAdapter)

    def test_registry_creates_medical_adapter(self):
        with patch("app.services.template_manager.get_template_manager") as get_manager:
            get_manager.return_value.list_templates.return_value = []
            adapter = get_domain_adapter("medical")

        self.assertIsInstance(adapter, MedicalDomainAdapter)


if __name__ == "__main__":
    unittest.main()
