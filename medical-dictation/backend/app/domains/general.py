"""Vanilla transcription domain."""

from app.domains.base import DomainAdapter


class GeneralDomainAdapter(DomainAdapter):
    """Plain transcription with no domain formatting or voice commands."""

    name = "general"
    commands_enabled = False
