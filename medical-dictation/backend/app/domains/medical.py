"""Medical transcription domain adapter."""

import logging
import re
from typing import List, Tuple

from app.domains.base import DomainAdapter
from app.services.command_processor import CommandProcessor, CommandType, VoiceCommand
from app.services.medical_formatter import MedicalFormatter

logger = logging.getLogger(__name__)


class MedicalDomainAdapter(DomainAdapter):
    """Current medical formatting, command, and template behavior."""

    name = "medical"
    commands_enabled = True

    def __init__(self):
        self.formatter = MedicalFormatter()
        self.command_processor = CommandProcessor()
        self._register_template_commands()

    def process_transcript(self, text: str) -> Tuple[str, List[VoiceCommand]]:
        formatted = self.formatter.format(text)
        processed_text, commands = self.command_processor.process(formatted)
        return self.formatter.format(processed_text), commands

    def _register_template_commands(self):
        """Register active SQLite templates on this domain's command processor."""
        try:
            from app.services.template_manager import get_template_manager

            manager = get_template_manager()
            templates = manager.list_templates()

            for template in templates:
                trigger_phrases = template.get("trigger_phrases") or []
                escaped = [
                    re.escape(phrase.lower().strip())
                    for phrase in trigger_phrases
                    if phrase and phrase.strip()
                ]
                if not escaped:
                    continue

                pattern = rf"\b(?:insert |add )?(?:{'|'.join(escaped)})(?: template)?\b"
                self.command_processor.register_custom_command(
                    pattern,
                    VoiceCommand(
                        command_type=CommandType.TEMPLATE,
                        action=template["name"],
                        replacement=template["content"],
                    ),
                )

            logger.debug("Registered %s template command groups for medical domain", len(templates))
        except Exception as e:
            logger.warning("Could not register template commands for medical domain: %s", e)
