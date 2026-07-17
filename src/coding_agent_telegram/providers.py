from __future__ import annotations

"""Shared provider identifiers and display labels used across config, router, and runtime code."""

SUPPORTED_PROVIDERS: tuple[str, ...] = ("codex", "copilot", "claude")

_PROVIDER_LABELS: dict[str, str] = {
    "codex": "Codex",
    "copilot": "Copilot",
    "claude": "Claude",
}


def provider_label(provider: str) -> str:
    """Return a human-friendly display label for a provider identifier."""
    return _PROVIDER_LABELS.get(provider, provider.capitalize() if provider else "")
