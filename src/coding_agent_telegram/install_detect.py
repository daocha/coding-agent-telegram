from __future__ import annotations

from pathlib import Path
from typing import Optional


def detect_startup_script() -> Optional[Path]:
    """Return startup.sh's path when running from a cloned repo checkout
    (README Quick Start Option C), or None for a pip / install.sh install
    (Options A/B -- both end up as a plain `pip install` with no repo
    checkout nearby, so `coding-agent-telegram` is the right command instead).
    """
    here = Path(__file__).resolve()
    for parent in here.parents:
        candidate = parent / "startup.sh"
        if candidate.is_file() and (parent / "pyproject.toml").is_file():
            return candidate
    return None


def claude_auth_command_hint(token_placeholder: str = "<token>") -> str:
    """The exact command the operator should run to save a `claude setup-token`
    result, matching however this install is actually run."""
    startup_script = detect_startup_script()
    if startup_script is not None:
        return f"{startup_script} claude-auth {token_placeholder}"
    return f"coding-agent-telegram claude-auth {token_placeholder}"
