from __future__ import annotations

from pathlib import Path

from coding_agent_telegram.native_codex_sessions import discover_codex_sessions
from coding_agent_telegram.native_copilot_sessions import discover_copilot_sessions
from coding_agent_telegram.native_session_types import NativeSessionRecord


def discover_native_project_sessions(
    project_path: Path,
    project_folder: str,
    *,
    provider: str | None = None,
) -> dict[str, NativeSessionRecord]:
    sessions: dict[str, NativeSessionRecord] = {}
    if provider in (None, "", "codex"):
        for record in discover_codex_sessions(project_path, project_folder):
            sessions.setdefault(record.session_id, record)
    if provider in (None, "", "copilot"):
        for record in discover_copilot_sessions(project_path, project_folder):
            sessions.setdefault(record.session_id, record)
    return sessions
