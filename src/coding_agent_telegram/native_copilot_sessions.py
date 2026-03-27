from __future__ import annotations

import os
from pathlib import Path

from coding_agent_telegram.native_session_types import NativeSessionRecord
from coding_agent_telegram.native_session_utils import (
    first_copilot_user_message,
    normalize_init_text,
    path_matches_project,
    read_simple_yaml_map,
)


def copilot_session_roots(project_path: Path) -> list[Path]:
    env_home = Path(os.environ["COPILOT_HOME"]).expanduser() if os.environ.get("COPILOT_HOME") else None
    if env_home is not None:
        return [env_home]
    return [project_path / ".copilot"]


def discover_copilot_sessions(project_path: Path, project_folder: str) -> list[NativeSessionRecord]:
    records: list[NativeSessionRecord] = []
    seen_session_ids: set[str] = set()
    for root in copilot_session_roots(project_path):
        session_root = root / "session-state"
        if not session_root.exists():
            continue
        for workspace_path in sorted(session_root.glob("*/workspace.yaml")):
            data = read_simple_yaml_map(workspace_path)
            session_id = data.get("id") or workspace_path.parent.name
            if session_id in seen_session_ids:
                continue
            cwd = data.get("cwd") or data.get("git_root") or ""
            if not path_matches_project(cwd, project_path):
                continue
            init_text = data.get("summary") or first_copilot_user_message(workspace_path.parent / "events.jsonl") or session_id
            records.append(
                NativeSessionRecord(
                    session_id=session_id,
                    name=normalize_init_text(init_text, fallback=session_id),
                    project_folder=project_folder,
                    provider="copilot",
                    branch_name=data.get("branch", ""),
                    created_at=data.get("created_at", ""),
                    updated_at=data.get("updated_at", ""),
                    source_label="native copilot",
                    initialized_from=normalize_init_text(init_text, fallback="Native Copilot session"),
                )
            )
            seen_session_ids.add(session_id)
    records.sort(key=lambda item: (item.updated_at or item.created_at, item.session_id), reverse=True)
    return records
