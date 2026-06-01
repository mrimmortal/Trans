import unittest

from app.domains.base import DomainAdapter
from app.domains.general import GeneralDomainAdapter
from app.domains import registry
from app.domains.registry import get_available_domains, get_domain_adapter, register_domain


class DomainAdapterTests(unittest.TestCase):
    def setUp(self):
        self._registry_snapshot = registry._DOMAIN_REGISTRY.copy()

    def tearDown(self):
        registry._DOMAIN_REGISTRY.clear()
        registry._DOMAIN_REGISTRY.update(self._registry_snapshot)

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

    def test_registry_returns_known_registered_domain(self):
        class CustomDomainAdapter(DomainAdapter):
            name = "custom"

        register_domain("custom", CustomDomainAdapter)

        adapter = get_domain_adapter(" CUSTOM ")

        self.assertIsInstance(adapter, CustomDomainAdapter)
        self.assertEqual(adapter.name, "custom")

    def test_registered_domain_appears_in_available_domains(self):
        class CustomDomainAdapter(DomainAdapter):
            name = "custom"

        register_domain("custom", CustomDomainAdapter)

        self.assertEqual(get_available_domains(), ["custom", "general"])


if __name__ == "__main__":
    unittest.main()
