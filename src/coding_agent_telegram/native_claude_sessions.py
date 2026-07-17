from __future__ import annotations

import json
import os
from pathlib import Path

from coding_agent_telegram.native_session_types import NativeSessionRecord
from coding_agent_telegram.native_session_utils import normalize_init_text, path_matches_project


def claude_projects_root() -> Path:
    config_dir = os.environ.get("CLAUDE_CONFIG_DIR", "").strip()
    base = Path(config_dir).expanduser() if config_dir else Path.home() / ".claude"
    return base / "projects"


def _first_text_from_content(content: object) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        for block in content:
            if isinstance(block, dict) and block.get("type") == "text" and isinstance(block.get("text"), str):
                return block["text"]
    return ""


def _read_claude_session_file(jsonl_path: Path, project_path: Path, project_folder: str) -> NativeSessionRecord | None:
    session_id = jsonl_path.stem
    branch_name = ""
    created_at = ""
    updated_at = ""
    first_user_message = ""
    matched = False

    try:
        with jsonl_path.open(encoding="utf-8") as handle:
            for raw_line in handle:
                line = raw_line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if not isinstance(entry, dict):
                    continue

                entry_cwd = entry.get("cwd")
                if isinstance(entry_cwd, str) and entry_cwd and not matched:
                    if not path_matches_project(entry_cwd, project_path):
                        return None
                    matched = True

                entry_branch = entry.get("gitBranch")
                if isinstance(entry_branch, str) and entry_branch:
                    branch_name = entry_branch

                timestamp = entry.get("timestamp")
                if isinstance(timestamp, str) and timestamp:
                    if not created_at:
                        created_at = timestamp
                    updated_at = timestamp

                if not first_user_message and entry.get("type") == "user" and not entry.get("isMeta"):
                    message = entry.get("message")
                    if isinstance(message, dict):
                        text = _first_text_from_content(message.get("content")).strip()
                        if text:
                            first_user_message = text
    except OSError:
        return None

    if not matched:
        return None

    init_text = first_user_message or session_id
    return NativeSessionRecord(
        session_id=session_id,
        name=normalize_init_text(init_text, fallback=f"Claude session in {project_folder}"),
        project_folder=project_folder,
        provider="claude",
        branch_name=branch_name,
        created_at=created_at,
        updated_at=updated_at,
        source_label="native claude",
        initialized_from=normalize_init_text(init_text, fallback="Native Claude session"),
    )


def discover_claude_sessions(project_path: Path, project_folder: str) -> list[NativeSessionRecord]:
    projects_root = claude_projects_root()
    if not projects_root.exists():
        return []

    try:
        project_dirs = [entry for entry in projects_root.iterdir() if entry.is_dir()]
    except OSError:
        return []

    records: list[NativeSessionRecord] = []
    for project_dir in project_dirs:
        try:
            jsonl_paths = sorted(project_dir.glob("*.jsonl"))
        except OSError:
            continue
        for jsonl_path in jsonl_paths:
            record = _read_claude_session_file(jsonl_path, project_path, project_folder)
            if record is not None:
                records.append(record)

    records.sort(key=lambda item: (item.updated_at or item.created_at, item.session_id), reverse=True)
    return records
