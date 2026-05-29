import unittest

from app.domains.general import GeneralDomainAdapter
from app.domains.registry import get_domain_adapter


class DomainAdapterTests(unittest.TestCase):
    def test_general_domain_returns_raw_text_without_commands(self):
        adapter = GeneralDomainAdapter()

        processed_text, commands = adapter.process_transcript("meeting starts now")

        self.assertEqual(processed_text, "meeting starts now")
        self.assertEqual(commands, [])
        self.assertFalse(adapter.commands_enabled)
        self.assertEqual(adapter.command_processor.get_available_commands(), {})

    def test_registry_treats_unknown_domain_as_vanilla(self):
        adapter = get_domain_adapter("legacy-domain")

        self.assertIsInstance(adapter, GeneralDomainAdapter)
        self.assertEqual(adapter.name, "general")


if __name__ == "__main__":
    unittest.main()
