from __future__ import annotations

"""Default per-provider model choices offered by the /model command.

These only seed the /model picker; the model actually passed to each CLI
still comes from CODEX_MODEL/COPILOT_MODEL/CLAUDE_MODEL (config.py) or a
per-session override set via /model. Override the picker's choices with the
CODEX_MODEL_CHOICES/COPILOT_MODEL_CHOICES/CLAUDE_MODEL_CHOICES env vars
(comma separated) if a CLI supports models not listed here.
"""

DEFAULT_MODEL_CHOICES: dict[str, tuple[str, ...]] = {
    "codex": ("gpt-5.4",),
    "copilot": ("gpt-5.4", "claude-sonnet-4.6"),
    "claude": ("sonnet", "opus", "haiku"),
}


def model_choices_for(provider: str) -> tuple[str, ...]:
    """Return the fallback model choices for a provider identifier."""
    return DEFAULT_MODEL_CHOICES.get(provider, ())
