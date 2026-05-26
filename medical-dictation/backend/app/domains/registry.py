"""Domain adapter registry."""

from app.domains.base import DomainAdapter
from app.domains.general import GeneralDomainAdapter
from app.domains.medical import MedicalDomainAdapter


def get_domain_adapter(domain: str | None) -> DomainAdapter:
    """Create a domain adapter by name, falling back to vanilla general mode."""
    normalized = (domain or "general").strip().lower()
    if normalized == "medical":
        return MedicalDomainAdapter()
    return GeneralDomainAdapter()
