from __future__ import annotations

"""Best-effort "how long has this native session been idle" detection.

Used to warn a user before resuming a session that has been idle long enough
for the provider's prompt cache to have expired, since resuming past that
point forces the whole accumulated conversation to be reprocessed instead of
read from cache (see the "does this app burn more tokens" FAQ in README.md).

Deliberately uses filesystem/db modification time as a cheap proxy for "last
activity" rather than parsing the full transcript on every incoming message.
"""

import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from coding_agent_telegram.native_claude_sessions import claude_projects_root
from coding_agent_telegram.native_codex_sessions import codex_state_db_path
from coding_agent_telegram.native_copilot_sessions import copilot_session_roots


def _mtime_utc(path: Path) -> Optional[datetime]:
    try:
        return datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)
    except OSError:
        return None


def _claude_last_activity(session_id: str) -> Optional[datetime]:
    projects_root = claude_projects_root()
    if not projects_root.exists():
        return None
    # Session IDs are UUIDs, unique across every project directory, so a glob
    # by filename alone finds the right transcript without needing to
    # reimplement Claude Code's project-path-to-folder-name encoding.
    try:
        matches = sorted(projects_root.glob(f"*/{session_id}.jsonl"))
    except OSError:
        return None
    if not matches:
        return None
    return _mtime_utc(matches[0])


def _codex_last_activity(session_id: str) -> Optional[datetime]:
    db_path = codex_state_db_path()
    if not db_path.exists():
        return None
    try:
        conn = sqlite3.connect(db_path)
    except sqlite3.Error:
        return None
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT updated_at FROM threads WHERE id = ?", (session_id,))
        row = cursor.fetchone()
    except sqlite3.Error:
        return None
    finally:
        conn.close()
    if not row or not row[0]:
        return None
    return datetime.fromtimestamp(row[0], tz=timezone.utc)


def _copilot_last_activity(session_id: str) -> Optional[datetime]:
    latest: Optional[datetime] = None
    for root in copilot_session_roots(Path.home()):
        session_dir = root / "session-state" / session_id
        for name in ("workspace.yaml", "events.jsonl"):
            candidate = _mtime_utc(session_dir / name)
            if candidate is not None and (latest is None or candidate > latest):
                latest = candidate
    return latest


def native_session_last_activity(provider: str, session_id: str) -> Optional[datetime]:
    """Return the last-modified time of *session_id*'s native transcript, if found."""
    if not session_id:
        return None
    normalized_provider = (provider or "").strip().lower()
    if normalized_provider == "claude":
        return _claude_last_activity(session_id)
    if normalized_provider == "codex":
        return _codex_last_activity(session_id)
    if normalized_provider == "copilot":
        return _copilot_last_activity(session_id)
    return None


def gap_seconds_since_last_activity(provider: str, session_id: str) -> Optional[float]:
    """Seconds since *session_id* last had activity, or None if it can't be determined."""
    last_activity = native_session_last_activity(provider, session_id)
    if last_activity is None:
        return None
    now = datetime.now(timezone.utc)
    return max(0.0, (now - last_activity).total_seconds())


def humanize_gap_seconds(seconds: float) -> str:
    """Render a gap as a short human string, e.g. "12h 30m" or "45m"."""
    total_minutes = int(seconds // 60)
    days, remainder_minutes = divmod(total_minutes, 24 * 60)
    hours, minutes = divmod(remainder_minutes, 60)
    parts: list[str] = []
    if days:
        parts.append(f"{days}d")
    if hours:
        parts.append(f"{hours}h")
    if minutes or not parts:
        parts.append(f"{minutes}m")
    return " ".join(parts[:2])
