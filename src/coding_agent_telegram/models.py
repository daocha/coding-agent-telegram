from __future__ import annotations

"""Default per-provider model choices offered by the /model command."""

from importlib import resources


_MODEL_CHOICE_ENV_NAMES = {
    "codex": "CODEX_MODEL_CHOICES",
    "copilot": "COPILOT_MODEL_CHOICES",
    "claude": "CLAUDE_MODEL_CHOICES",
}
_CLAUDE_FALLBACK_MODEL_CHOICES = ("sonnet", "opus", "fable", "haiku")


def _parse_template_model_choices(template_text: str) -> dict[str, tuple[str, ...]]:
    """Read model-picker defaults from the packaged .env.example template."""
    values = {provider: () for provider in _MODEL_CHOICE_ENV_NAMES}
    for line in template_text.splitlines():
        name, separator, raw_value = line.partition("=")
        if not separator:
            continue
        for provider, env_name in _MODEL_CHOICE_ENV_NAMES.items():
            if name != env_name:
                continue
            values[provider] = tuple(item.strip() for item in raw_value.split(",") if item.strip())
            break
    return values


def _load_default_model_choices() -> dict[str, tuple[str, ...]]:
    try:
        template_text = resources.files("coding_agent_telegram").joinpath("resources/.env.example").read_text(
            encoding="utf-8"
        )
    except (FileNotFoundError, ModuleNotFoundError, OSError):
        template_text = ""

    choices = _parse_template_model_choices(template_text)
    # Claude's stable aliases remain useful even when a package is distributed
    # without its configuration template.
    if not choices["claude"]:
        choices["claude"] = _CLAUDE_FALLBACK_MODEL_CHOICES
    return choices


DEFAULT_MODEL_CHOICES = _load_default_model_choices()


def model_choices_for(provider: str) -> tuple[str, ...]:
    """Return the fallback model choices for a provider identifier."""
    return DEFAULT_MODEL_CHOICES.get(provider, ())
