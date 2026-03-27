from __future__ import annotations

import sqlite3
from pathlib import Path

from coding_agent_telegram.native_session_types import NativeSessionRecord
from coding_agent_telegram.native_session_utils import iso_from_unix, normalize_init_text, path_matches_project


def discover_codex_sessions(project_path: Path, project_folder: str) -> list[NativeSessionRecord]:
    db_path = Path.home() / ".codex" / "state_5.sqlite"
    if not db_path.exists():
        return []
    try:
        conn = sqlite3.connect(db_path)
    except sqlite3.Error:
        return []
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT id, cwd, title, first_user_message, git_branch, created_at, updated_at
            FROM threads
            WHERE archived = 0
            ORDER BY updated_at DESC
            """
        )
        rows = cursor.fetchall()
    except sqlite3.Error:
        return []
    finally:
        conn.close()

    records: list[NativeSessionRecord] = []
    for session_id, cwd, title, first_user_message, git_branch, created_at, updated_at in rows:
        if not path_matches_project(str(cwd or ""), project_path):
            continue
        init_text = title or first_user_message or session_id
        records.append(
            NativeSessionRecord(
                session_id=str(session_id),
                name=str(title or first_user_message or session_id).strip() or str(session_id),
                project_folder=project_folder,
                provider="codex",
                branch_name=str(git_branch or ""),
                created_at=iso_from_unix(created_at),
                updated_at=iso_from_unix(updated_at),
                source_label="native codex",
                initialized_from=normalize_init_text(str(init_text), fallback="Native Codex session"),
            )
        )
    return records
