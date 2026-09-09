"""Tests for session_gap.py."""
from __future__ import annotations

import json
import os
from pathlib import Path
from unittest.mock import patch

from coding_agent_telegram.session_gap import native_session_activity


def _write_jsonl(path: Path, entries: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(json.dumps(entry) for entry in entries) + "\n", encoding="utf-8")


def _real_usage_entry(total_tokens: int) -> dict:
    return {
        "type": "assistant",
        "message": {
            "model": "claude-sonnet-5",
            "role": "assistant",
            "usage": {
                "input_tokens": total_tokens,
                "cache_creation_input_tokens": 0,
                "cache_read_input_tokens": 0,
            },
        },
    }


def _synthetic_stub_entry(text: str, error: str | None = None) -> dict:
    entry = {
        "type": "assistant",
        "message": {
            "model": "<synthetic>",
            "role": "assistant",
            "usage": {
                "input_tokens": 0,
                "cache_creation_input_tokens": 0,
                "cache_read_input_tokens": 0,
            },
            "content": [{"type": "text", "text": text}],
        },
    }
    if error is not None:
        entry["error"] = error
    return entry


def test_claude_size_skips_trailing_synthetic_rate_limit_stub(tmp_path: Path):
    claude_home = tmp_path / "claude-home"
    session_file = claude_home / "projects" / "-tmp-proj" / "sess-1.jsonl"
    _write_jsonl(
        session_file,
        [
            _real_usage_entry(50_000),
            _synthetic_stub_entry("You've hit your session limit · resets 12:40am (Asia/Shanghai)", error="rate_limit"),
        ],
    )

    with patch.dict(os.environ, {"CLAUDE_CONFIG_DIR": str(claude_home)}):
        _last_activity, size_tokens = native_session_activity("claude", "sess-1")

    assert size_tokens == 50_000


def test_claude_size_skips_trailing_synthetic_auth_and_no_response_stubs(tmp_path: Path):
    claude_home = tmp_path / "claude-home"
    session_file = claude_home / "projects" / "-tmp-proj" / "sess-2.jsonl"
    _write_jsonl(
        session_file,
        [
            _real_usage_entry(30_000),
            _synthetic_stub_entry("Not logged in · Please run /login", error="authentication_failed"),
            _synthetic_stub_entry("No response requested."),
        ],
    )

    with patch.dict(os.environ, {"CLAUDE_CONFIG_DIR": str(claude_home)}):
        _last_activity, size_tokens = native_session_activity("claude", "sess-2")

    assert size_tokens == 30_000


def test_claude_size_is_none_when_only_synthetic_entries_exist(tmp_path: Path):
    claude_home = tmp_path / "claude-home"
    session_file = claude_home / "projects" / "-tmp-proj" / "sess-3.jsonl"
    _write_jsonl(
        session_file,
        [_synthetic_stub_entry("No response requested.")],
    )

    with patch.dict(os.environ, {"CLAUDE_CONFIG_DIR": str(claude_home)}):
        _last_activity, size_tokens = native_session_activity("claude", "sess-3")

    assert size_tokens is None
