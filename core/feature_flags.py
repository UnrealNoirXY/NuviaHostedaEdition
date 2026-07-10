"""Runtime feature flags for modules that can be decommissioned safely."""

from django.conf import settings


def is_feature_enabled(name: str, default: bool = True) -> bool:
    """Return a boolean feature flag from Django settings."""
    return bool(getattr(settings, name, default))


def get_external_url(name: str) -> str:
    """Return an optional external replacement URL for a decommissioned module."""
    return str(getattr(settings, name, "") or "").strip()
