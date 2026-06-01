"""Base domain adapter contracts for transcription output."""

from typing import List, Tuple

from app.services.commands import VoiceCommand


class NoopCommandProcessor:
    """Command processor facade for domains that do not support commands."""

    enabled = False

    def enable(self):
        self.enabled = False

    def disable(self):
        self.enabled = False

    def get_available_commands(self) -> dict:
        return {}

    def register_custom_command(self, *args, **kwargs):
        return None

    def unregister_custom_command(self, *args, **kwargs):
        return None

    def get_command_history(self, limit: int = 50) -> list:
        return []

    def clear_history(self):
        return None


class DomainAdapter:
    """Base adapter for domain-specific transcript processing."""

    name = "general"
    commands_enabled = False

    def __init__(self):
        self.command_processor = NoopCommandProcessor()

    def process_transcript(self, text: str) -> Tuple[str, List[VoiceCommand]]:
        return text, []
