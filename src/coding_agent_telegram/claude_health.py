from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from coding_agent_telegram.agent_runner import MultiAgentRunner
from coding_agent_telegram.i18n import translate
from coding_agent_telegram.install_detect import claude_auth_command_hint

# Mirrors SESSION_PRIMING_PROMPT's intent (read-only, no real work) without
# importing router code into this lower-level module.
_PROBE_PROMPT = "Reply with exactly: ok. Do not make any changes, run any commands, or use any tools."
_AUTH_FAILURE_MARKERS = ("authenticat", "oauth")


@dataclass(frozen=True)
class ClaudeHealthResult:
    healthy: bool
    is_auth_failure: bool
    detail: str


def is_claude_auth_failure(text: Optional[str]) -> bool:
    """Whether a Claude error message matches this failure's signature.

    Shared by the background health-check probe below and by the live
    /new-time and message-time failure paths (session_lifecycle_commands.py,
    session_runtime.py), so both surfaces agree on what counts as this
    specific failure and show the identical fix message.
    """
    if not text:
        return False
    return any(marker in text.lower() for marker in _AUTH_FAILURE_MARKERS)


def claude_auth_failure_message(locale: str, detail: Optional[str]) -> str:
    """The user-facing guidance text for a Claude auth failure, with the
    install-mode-appropriate `claude-auth` command filled in."""
    return translate(
        locale,
        "health.claude_auth_failed_auth",
        detail=(detail or "").strip(),
        claude_auth_hint=claude_auth_command_hint(),
    )


def check_claude_auth(runner: MultiAgentRunner, scratch_dir: Path) -> ClaudeHealthResult:
    """Probe whether Claude can create a session the same way a real /new does.

    `claude auth status` is not a substitute for this: during the 2026-09-14
    incident it reported a valid login the entire time a Claude Code CLI
    regression broke authentication for every detached-subprocess session
    creation (the pattern this bot uses), because the interactive command
    exercises a different auth path than a headless one. This runs the exact
    same subprocess pattern `create_session` does, against a throwaway
    directory, and applies the same success criteria the session-creation
    command router uses (see session_lifecycle_commands.py): a run only
    counts as healthy if it both succeeds and returns a session ID.
    """
    scratch_dir.mkdir(parents=True, exist_ok=True)
    result = runner.create_session("claude", scratch_dir, _PROBE_PROMPT, priming_only=True)
    if result.success and result.session_id:
        return ClaudeHealthResult(healthy=True, is_auth_failure=False, detail="")
    detail = (result.error_message or "Claude did not return a session ID.").strip()
    return ClaudeHealthResult(healthy=False, is_auth_failure=is_claude_auth_failure(detail), detail=detail)
