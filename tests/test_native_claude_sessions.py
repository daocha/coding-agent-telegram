"""Tests for native_claude_sessions.py."""
from __future__ import annotations

import json
import os
from pathlib import Path
from unittest.mock import patch

from coding_agent_telegram.native_claude_sessions import claude_projects_root, discover_claude_sessions
from coding_agent_telegram.native_sessions import discover_native_project_sessions


def _write_jsonl(path: Path, entries: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(json.dumps(entry) for entry in entries) + "\n", encoding="utf-8")


def test_claude_projects_root_uses_config_dir_env(tmp_path: Path):
    custom = tmp_path / "custom-claude-home"
    with patch.dict(os.environ, {"CLAUDE_CONFIG_DIR": str(custom)}):
        assert claude_projects_root() == custom / "projects"


def test_claude_projects_root_defaults_to_home(tmp_path: Path):
    env = {k: v for k, v in os.environ.items() if k != "CLAUDE_CONFIG_DIR"}
    with patch.dict(os.environ, env, clear=True):
        with patch("coding_agent_telegram.native_claude_sessions.Path.home", return_value=tmp_path):
            assert claude_projects_root() == tmp_path / ".claude" / "projects"


def test_discover_claude_sessions_returns_empty_when_projects_root_missing(tmp_path: Path):
    with patch.dict(os.environ, {"CLAUDE_CONFIG_DIR": str(tmp_path / "does-not-exist")}):
        result = discover_claude_sessions(tmp_path / "proj", "proj")
    assert result == []


def test_discover_claude_sessions_skips_non_matching_cwd(tmp_path: Path):
    claude_home = tmp_path / "claude-home"
    proj = tmp_path / "myproj"
    proj.mkdir()
    other = tmp_path / "other"
    other.mkdir()

    session_file = claude_home / "projects" / "-tmp-other" / "sess-1.jsonl"
    _write_jsonl(
        session_file,
        [
            {
                "type": "user",
                "message": {"role": "user", "content": "hello"},
                "cwd": str(other),
                "gitBranch": "main",
                "timestamp": "2026-01-01T00:00:00.000Z",
                "sessionId": "sess-1",
            }
        ],
    )

    with patch.dict(os.environ, {"CLAUDE_CONFIG_DIR": str(claude_home)}):
        result = discover_claude_sessions(proj, "myproj")

    assert result == []


def test_discover_claude_sessions_returns_matching_session(tmp_path: Path):
    claude_home = tmp_path / "claude-home"
    proj = tmp_path / "myproj"
    proj.mkdir()

    session_file = claude_home / "projects" / "-tmp-myproj" / "sess-abc.jsonl"
    _write_jsonl(
        session_file,
        [
            {"type": "mode", "mode": "normal", "sessionId": "sess-abc"},
            {
                "type": "user",
                "message": {"role": "user", "content": "Fix the failing test"},
                "cwd": str(proj),
                "gitBranch": "feature-x",
                "timestamp": "2026-01-01T00:00:00.000Z",
                "sessionId": "sess-abc",
            },
            {
                "type": "assistant",
                "message": {"role": "assistant", "content": [{"type": "text", "text": "Sure, looking now."}]},
                "cwd": str(proj),
                "gitBranch": "feature-x",
                "timestamp": "2026-01-01T00:05:00.000Z",
                "sessionId": "sess-abc",
            },
        ],
    )

    with patch.dict(os.environ, {"CLAUDE_CONFIG_DIR": str(claude_home)}):
        result = discover_claude_sessions(proj, "myproj")

    assert len(result) == 1
    record = result[0]
    assert record.session_id == "sess-abc"
    assert record.project_folder == "myproj"
    assert record.provider == "claude"
    assert record.branch_name == "feature-x"
    assert record.created_at == "2026-01-01T00:00:00.000Z"
    assert record.updated_at == "2026-01-01T00:05:00.000Z"
    assert "Fix the failing test" in record.name
    assert record.source_label == "native claude"


def test_discover_claude_sessions_ignores_meta_messages_for_first_user_text(tmp_path: Path):
    claude_home = tmp_path / "claude-home"
    proj = tmp_path / "myproj"
    proj.mkdir()

    session_file = claude_home / "projects" / "-tmp-myproj" / "sess-meta.jsonl"
    _write_jsonl(
        session_file,
        [
            {
                "type": "user",
                "isMeta": True,
                "message": {"role": "user", "content": "<local-command-caveat>ignored</local-command-caveat>"},
                "cwd": str(proj),
                "timestamp": "2026-01-01T00:00:00.000Z",
                "sessionId": "sess-meta",
            },
            {
                "type": "user",
                "message": {"role": "user", "content": "Actual user prompt"},
                "cwd": str(proj),
                "timestamp": "2026-01-01T00:01:00.000Z",
                "sessionId": "sess-meta",
            },
        ],
    )

    with patch.dict(os.environ, {"CLAUDE_CONFIG_DIR": str(claude_home)}):
        result = discover_claude_sessions(proj, "myproj")

    assert len(result) == 1
    assert "Actual user prompt" in result[0].name


def test_discover_claude_sessions_ignores_malformed_lines(tmp_path: Path):
    claude_home = tmp_path / "claude-home"
    proj = tmp_path / "myproj"
    proj.mkdir()

    session_file = claude_home / "projects" / "-tmp-myproj" / "sess-broken.jsonl"
    session_file.parent.mkdir(parents=True, exist_ok=True)
    session_file.write_text(
        "not json at all\n"
        + json.dumps(
            {
                "type": "user",
                "message": {"role": "user", "content": "still works"},
                "cwd": str(proj),
                "timestamp": "2026-01-01T00:00:00.000Z",
            }
        )
        + "\n",
        encoding="utf-8",
    )

    with patch.dict(os.environ, {"CLAUDE_CONFIG_DIR": str(claude_home)}):
        result = discover_claude_sessions(proj, "myproj")

    assert len(result) == 1
    assert result[0].session_id == "sess-broken"


def test_discover_claude_sessions_sorts_newest_first(tmp_path: Path):
    claude_home = tmp_path / "claude-home"
    proj = tmp_path / "myproj"
    proj.mkdir()

    _write_jsonl(
        claude_home / "projects" / "-tmp-myproj" / "sess-old.jsonl",
        [
            {
                "type": "user",
                "message": {"role": "user", "content": "old"},
                "cwd": str(proj),
                "timestamp": "2026-01-01T00:00:00.000Z",
            }
        ],
    )
    _write_jsonl(
        claude_home / "projects" / "-tmp-myproj" / "sess-new.jsonl",
        [
            {
                "type": "user",
                "message": {"role": "user", "content": "new"},
                "cwd": str(proj),
                "timestamp": "2026-06-01T00:00:00.000Z",
            }
        ],
    )

    with patch.dict(os.environ, {"CLAUDE_CONFIG_DIR": str(claude_home)}):
        result = discover_claude_sessions(proj, "myproj")

    assert [record.session_id for record in result] == ["sess-new", "sess-old"]


def test_discover_native_project_sessions_includes_claude_records(tmp_path: Path):
    claude_home = tmp_path / "claude-home"
    proj = tmp_path / "myproj"
    proj.mkdir()

    _write_jsonl(
        claude_home / "projects" / "-tmp-myproj" / "sess-claude.jsonl",
        [
            {
                "type": "user",
                "message": {"role": "user", "content": "hello"},
                "cwd": str(proj),
                "timestamp": "2026-01-01T00:00:00.000Z",
            }
        ],
    )

    with patch.dict(os.environ, {"CLAUDE_CONFIG_DIR": str(claude_home), "COPILOT_HOME": str(tmp_path / "no-copilot")}):
        with patch("coding_agent_telegram.native_codex_sessions.Path.home", return_value=tmp_path / "no-codex-home"):
            sessions = discover_native_project_sessions(proj, "myproj")

    assert "sess-claude" in sessions
    assert sessions["sess-claude"].provider == "claude"


def test_discover_native_project_sessions_can_filter_to_claude_only(tmp_path: Path):
    claude_home = tmp_path / "claude-home"
    proj = tmp_path / "myproj"
    proj.mkdir()

    _write_jsonl(
        claude_home / "projects" / "-tmp-myproj" / "sess-claude.jsonl",
        [
            {
                "type": "user",
                "message": {"role": "user", "content": "hello"},
                "cwd": str(proj),
                "timestamp": "2026-01-01T00:00:00.000Z",
            }
        ],
    )

    with patch.dict(os.environ, {"CLAUDE_CONFIG_DIR": str(claude_home)}):
        sessions = discover_native_project_sessions(proj, "myproj", provider="claude")

    assert set(sessions.keys()) == {"sess-claude"}
