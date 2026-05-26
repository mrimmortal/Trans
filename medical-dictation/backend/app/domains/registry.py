"""Domain adapter registry."""

from app.domains.base import DomainAdapter
from app.domains.general import GeneralDomainAdapter


def get_domain_adapter(domain: str | None) -> DomainAdapter:
    """Create a domain adapter by name, falling back to vanilla general mode."""
    _normalized = (domain or "general").strip().lower()
    return GeneralDomainAdapter()
