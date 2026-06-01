"""Domain adapter registry."""

from app.domains.base import DomainAdapter
from app.domains.general import GeneralDomainAdapter

_DOMAIN_REGISTRY: dict[str, type[DomainAdapter]] = {
    GeneralDomainAdapter.name: GeneralDomainAdapter,
}


def _normalize_domain_name(domain: str | None) -> str:
    return (domain or "general").strip().lower() or "general"


def register_domain(name: str, adapter_cls: type[DomainAdapter]) -> None:
    """Register a domain adapter class for wrapper-specific transcript processing."""
    normalized = _normalize_domain_name(name)
    _DOMAIN_REGISTRY[normalized] = adapter_cls


def get_available_domains() -> list[str]:
    """Return registered domain names in stable order."""
    return sorted(_DOMAIN_REGISTRY)


def get_domain_adapter(domain: str | None) -> DomainAdapter:
    """Create a domain adapter by name, falling back to vanilla general mode."""
    adapter_cls = _DOMAIN_REGISTRY.get(_normalize_domain_name(domain), GeneralDomainAdapter)
    return adapter_cls()
