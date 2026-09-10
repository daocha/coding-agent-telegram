from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Optional

from coding_agent_telegram.native_session_types import NativeSessionRecord
from coding_agent_telegram.native_session_utils import iso_from_unix, normalize_init_text, path_matches_project


def codex_state_db_path() -> Path:
    return Path.home() / ".codex" / "state_5.sqlite"


def query_codex_state_db(sql: str, params: tuple = ()) -> Optional[list[tuple]]:
    """Run a read-only query against the local Codex state db.

    Returns None if the db doesn't exist or the query fails, so callers can tell "no
    rows" (empty list) apart from "couldn't read the db at all" without each
    reimplementing the connect/execute/close boilerplate and its error handling.
    """
    db_path = codex_state_db_path()
    if not db_path.exists():
        return None
    try:
        conn = sqlite3.connect(db_path)
    except sqlite3.Error:
        return None
    try:
        cursor = conn.cursor()
        cursor.execute(sql, params)
        return cursor.fetchall()
    except sqlite3.Error:
        return None
    finally:
        conn.close()


def discover_codex_sessions(project_path: Path, project_folder: str) -> list[NativeSessionRecord]:
    rows = query_codex_state_db(
        """
        SELECT id, cwd, title, first_user_message, git_branch, created_at, updated_at
        FROM threads
        WHERE archived = 0
        ORDER BY updated_at DESC
        """
    )
    if not rows:
        return []

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
