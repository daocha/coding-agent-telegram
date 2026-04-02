"""Tests for native_codex_sessions.py and native_copilot_sessions.py."""
from __future__ import annotations

import json
import os
import sqlite3
from pathlib import Path
from unittest.mock import patch

import pytest

from coding_agent_telegram.native_codex_sessions import discover_codex_sessions
from coding_agent_telegram.native_copilot_sessions import (
    copilot_session_label,
    copilot_session_roots,
    discover_copilot_sessions,
)


# ===========================================================================
# native_codex_sessions.py
# ===========================================================================


def test_discover_codex_sessions_returns_empty_when_db_missing(tmp_path: Path):
    with patch("coding_agent_telegram.native_codex_sessions.Path.home", return_value=tmp_path):
        result = discover_codex_sessions(tmp_path / "proj", "proj")
    assert result == []


def test_discover_codex_sessions_returns_empty_on_connect_error(tmp_path: Path):
    fake_home = tmp_path / "home"
    fake_home.mkdir()
    db_dir = fake_home / ".codex"
    db_dir.mkdir()
    db_path = db_dir / "state_5.sqlite"
    db_path.write_bytes(b"not a sqlite db")  # corrupted → connect error

    with patch("coding_agent_telegram.native_codex_sessions.Path.home", return_value=fake_home):
        result = discover_codex_sessions(tmp_path / "proj", "proj")
    assert result == []


def test_discover_codex_sessions_returns_empty_on_query_error(tmp_path: Path):
    fake_home = tmp_path / "home"
    fake_home.mkdir()
    db_dir = fake_home / ".codex"
    db_dir.mkdir()
    db_path = db_dir / "state_5.sqlite"

    # Create a valid db but with no 'threads' table → query will raise sqlite3.Error
    conn = sqlite3.connect(str(db_path))
    conn.close()

    with patch("coding_agent_telegram.native_codex_sessions.Path.home", return_value=fake_home):
        result = discover_codex_sessions(tmp_path / "proj", "proj")
    assert result == []


def test_discover_codex_sessions_filters_non_matching_projects(tmp_path: Path):
    fake_home = tmp_path / "home"
    fake_home.mkdir()
    db_dir = fake_home / ".codex"
    db_dir.mkdir()
    db_path = db_dir / "state_5.sqlite"

    proj = tmp_path / "myproj"
    proj.mkdir()
    other = tmp_path / "other"
    other.mkdir()

    conn = sqlite3.connect(str(db_path))
    conn.execute("""
        CREATE TABLE threads (
            id TEXT, cwd TEXT, title TEXT, first_user_message TEXT,
            git_branch TEXT, created_at REAL, updated_at REAL, archived INTEGER
        )
    """)
    # Row for a different project — should be filtered out
    conn.execute("INSERT INTO threads VALUES (?,?,?,?,?,?,?,?)",
                 ("sid1", str(other), "title1", "msg1", "main", 1700000000.0, 1700000001.0, 0))
    # Row for the right project
    conn.execute("INSERT INTO threads VALUES (?,?,?,?,?,?,?,?)",
                 ("sid2", str(proj), "title2", "msg2", "feature", 1700000002.0, 1700000003.0, 0))
    conn.commit()
    conn.close()

    with patch("coding_agent_telegram.native_codex_sessions.Path.home", return_value=fake_home):
        result = discover_codex_sessions(proj, "myproj")

    assert len(result) == 1
    assert result[0].session_id == "sid2"
    assert result[0].branch_name == "feature"


# ===========================================================================
# native_copilot_sessions.py
# ===========================================================================


def test_copilot_session_roots_uses_env_home(tmp_path: Path):
    env_home = str(tmp_path / "custom_home")
    with patch.dict(os.environ, {"COPILOT_HOME": env_home}):
        roots = copilot_session_roots(tmp_path)
    assert len(roots) == 1
    assert roots[0] == Path(env_home)


def test_copilot_session_roots_uses_default_when_no_env(tmp_path: Path):
    env = {k: v for k, v in os.environ.items() if k != "COPILOT_HOME"}
    with patch.dict(os.environ, env, clear=True):
        roots = copilot_session_roots(tmp_path)
    assert len(roots) == 1
    assert roots[0] == Path.home() / ".copilot"


def test_copilot_session_label_with_branch():
    result = copilot_session_label({"branch": "main"}, "sid1", "myproj")
    assert "main" in result


def test_copilot_session_label_without_branch():
    result = copilot_session_label({}, "sid1", "myproj")
    assert "myproj" in result


def test_discover_copilot_sessions_returns_empty_when_no_session_root(tmp_path: Path):
    fake_home = tmp_path / "home"
    fake_home.mkdir()
    # No session-state directory

    with patch.dict(os.environ, {"COPILOT_HOME": str(fake_home)}):
        result = discover_copilot_sessions(tmp_path / "proj", "proj")
    assert result == []


def test_discover_copilot_sessions_skips_non_matching_cwd(tmp_path: Path):
    fake_home = tmp_path / "home"
    session_state = fake_home / "session-state" / "sess1"
    session_state.mkdir(parents=True)

    proj = tmp_path / "myproj"
    proj.mkdir()
    other = tmp_path / "other"
    other.mkdir()

    workspace = session_state / "workspace.yaml"
    workspace.write_text(f"id: sess1\ncwd: {other}\n", encoding="utf-8")

    with patch.dict(os.environ, {"COPILOT_HOME": str(fake_home)}):
        result = discover_copilot_sessions(proj, "myproj")
    assert result == []


def test_discover_copilot_sessions_deduplicates_sessions(tmp_path: Path):
    fake_home = tmp_path / "home"
    proj = tmp_path / "myproj"
    proj.mkdir()

    # Two session dirs with the same session id (duplicate)
    for i in [1, 2]:
        sess_dir = fake_home / "session-state" / f"sess{i}"
        sess_dir.mkdir(parents=True)
        workspace = sess_dir / "workspace.yaml"
        workspace.write_text(
            f"id: same-session-id\ncwd: {proj}\nbranch: main\n",
            encoding="utf-8",
        )

    with patch.dict(os.environ, {"COPILOT_HOME": str(fake_home)}):
        result = discover_copilot_sessions(proj, "myproj")

    assert len(result) == 1
    assert result[0].session_id == "same-session-id"


def test_discover_copilot_sessions_returns_matching_session(tmp_path: Path):
    fake_home = tmp_path / "home"
    proj = tmp_path / "myproj"
    proj.mkdir()

    sess_dir = fake_home / "session-state" / "abc123"
    sess_dir.mkdir(parents=True)
    workspace = sess_dir / "workspace.yaml"
    workspace.write_text(
        f"id: abc123\ncwd: {proj}\nbranch: feature-x\nsummary: My summary\n",
        encoding="utf-8",
    )

    with patch.dict(os.environ, {"COPILOT_HOME": str(fake_home)}):
        result = discover_copilot_sessions(proj, "myproj")

    assert len(result) == 1
    assert result[0].session_id == "abc123"
    assert result[0].branch_name == "feature-x"
    assert "My summary" in result[0].name


def test_discover_codex_sessions_returns_empty_on_sqlite_connect_error(tmp_path: Path):
    """Lines 16-17: sqlite3.Error on connect → return []."""
    import sqlite3
    from unittest.mock import patch

    fake_home = tmp_path / "home"
    db_dir = fake_home / ".codex"
    db_dir.mkdir(parents=True)
    (db_dir / "state_5.sqlite").write_bytes(b"")  # file exists

    with patch("coding_agent_telegram.native_codex_sessions.Path.home", return_value=fake_home):
        with patch("coding_agent_telegram.native_codex_sessions.sqlite3.connect",
                   side_effect=sqlite3.Error("cannot open")):
            result = discover_codex_sessions(tmp_path / "proj", "proj")
    assert result == []
