"""Tests for native_session_utils.py — pure utility functions."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from coding_agent_telegram.native_session_utils import (
    first_copilot_user_message,
    iso_from_unix,
    normalize_init_text,
    path_matches_project,
    read_simple_yaml_map,
)


# ---------------------------------------------------------------------------
# iso_from_unix
# ---------------------------------------------------------------------------


def test_iso_from_unix_returns_empty_for_none():
    assert iso_from_unix(None) == ""


def test_iso_from_unix_returns_empty_for_zero():
    assert iso_from_unix(0) == ""


def test_iso_from_unix_returns_iso_string():
    result = iso_from_unix(0.001)  # small positive value
    assert result.endswith("Z")
    assert "T" in result


def test_iso_from_unix_normal_timestamp():
    result = iso_from_unix(1700000000)
    assert result.endswith("Z")


# ---------------------------------------------------------------------------
# normalize_init_text
# ---------------------------------------------------------------------------


def test_normalize_init_text_returns_fallback_for_empty():
    assert normalize_init_text("", fallback="default") == "default"


def test_normalize_init_text_returns_fallback_for_whitespace_only():
    assert normalize_init_text("   ", fallback="fb") == "fb"


def test_normalize_init_text_truncates_long_text():
    long_text = "word " * 30  # ~150 chars
    result = normalize_init_text(long_text, fallback="fb")
    assert len(result) <= 120
    assert result.endswith("...")


def test_normalize_init_text_preserves_normal_text():
    assert normalize_init_text("hello world", fallback="fb") == "hello world"


def test_normalize_init_text_collapses_whitespace():
    assert normalize_init_text("  hello   world  ", fallback="fb") == "hello world"


# ---------------------------------------------------------------------------
# path_matches_project
# ---------------------------------------------------------------------------


def test_path_matches_project_returns_false_for_empty_candidate(tmp_path: Path):
    assert path_matches_project("", tmp_path) is False


def test_path_matches_project_returns_true_for_exact_match(tmp_path: Path):
    assert path_matches_project(str(tmp_path), tmp_path) is True


def test_path_matches_project_returns_true_for_child_path(tmp_path: Path):
    child = tmp_path / "subdir" / "file.py"
    assert path_matches_project(str(child), tmp_path) is True


def test_path_matches_project_returns_false_for_unrelated_path(tmp_path: Path):
    other = tmp_path.parent / "other"
    assert path_matches_project(str(other), tmp_path) is False


# ---------------------------------------------------------------------------
# first_copilot_user_message
# ---------------------------------------------------------------------------


def test_first_copilot_user_message_returns_empty_when_file_missing(tmp_path: Path):
    assert first_copilot_user_message(tmp_path / "nonexistent.jsonl") == ""


def test_first_copilot_user_message_returns_first_content(tmp_path: Path):
    events = tmp_path / "events.jsonl"
    events.write_text(
        json.dumps({"type": "user.message", "data": {"content": "hello"}}) + "\n",
        encoding="utf-8",
    )
    assert first_copilot_user_message(events) == "hello"


def test_first_copilot_user_message_skips_non_user_message_lines(tmp_path: Path):
    events = tmp_path / "events.jsonl"
    events.write_text(
        json.dumps({"type": "system.init", "data": {}}) + "\n"
        + json.dumps({"type": "user.message", "data": {"content": "second"}}) + "\n",
        encoding="utf-8",
    )
    assert first_copilot_user_message(events) == "second"


def test_first_copilot_user_message_skips_malformed_json(tmp_path: Path):
    events = tmp_path / "events.jsonl"
    events.write_text(
        "not valid json\n"
        + json.dumps({"type": "user.message", "data": {"content": "valid"}}) + "\n",
        encoding="utf-8",
    )
    assert first_copilot_user_message(events) == "valid"


def test_first_copilot_user_message_returns_empty_when_no_user_message(tmp_path: Path):
    events = tmp_path / "events.jsonl"
    events.write_text(
        json.dumps({"type": "system.init", "data": {}}) + "\n",
        encoding="utf-8",
    )
    assert first_copilot_user_message(events) == ""


def test_first_copilot_user_message_returns_empty_for_empty_content(tmp_path: Path):
    events = tmp_path / "events.jsonl"
    events.write_text(
        json.dumps({"type": "user.message", "data": {"content": ""}}) + "\n"
        + json.dumps({"type": "user.message", "data": {"content": "second"}}) + "\n",
        encoding="utf-8",
    )
    assert first_copilot_user_message(events) == "second"


# ---------------------------------------------------------------------------
# read_simple_yaml_map
# ---------------------------------------------------------------------------


def test_read_simple_yaml_map_returns_empty_for_missing_file(tmp_path: Path):
    assert read_simple_yaml_map(tmp_path / "nope.yaml") == {}


def test_read_simple_yaml_map_parses_key_value_pairs(tmp_path: Path):
    f = tmp_path / "config.yaml"
    f.write_text("key1: value1\nkey2: value2\n", encoding="utf-8")
    assert read_simple_yaml_map(f) == {"key1": "value1", "key2": "value2"}


def test_read_simple_yaml_map_skips_blank_and_comment_lines(tmp_path: Path):
    f = tmp_path / "config.yaml"
    f.write_text(
        "\n# this is a comment\nkey: val\n  # indented comment\n",
        encoding="utf-8",
    )
    assert read_simple_yaml_map(f) == {"key": "val"}


def test_read_simple_yaml_map_skips_lines_without_colon(tmp_path: Path):
    f = tmp_path / "config.yaml"
    f.write_text("no_colon_here\nkey: value\n", encoding="utf-8")
    assert read_simple_yaml_map(f) == {"key": "value"}


# ---------------------------------------------------------------------------
# OSError paths
# ---------------------------------------------------------------------------


def test_path_matches_project_returns_false_on_oserror(tmp_path: Path):
    from unittest.mock import patch, MagicMock

    def raising_resolve(self):
        raise OSError("mock oserror")

    with patch.object(Path, "resolve", raising_resolve):
        result = path_matches_project("/some/path", tmp_path)
    assert result is False


def test_first_copilot_user_message_returns_empty_on_oserror(tmp_path: Path):
    events = tmp_path / "events.jsonl"
    events.write_text("some content\n", encoding="utf-8")

    from unittest.mock import patch, mock_open

    with patch("builtins.open", side_effect=OSError("permission denied")):
        result = first_copilot_user_message(events)
    assert result == ""


def test_first_copilot_user_message_returns_empty_on_file_read_oserror(tmp_path: Path):
    """Lines 50-51: except OSError path inside first_copilot_user_message."""
    from unittest.mock import patch

    events = tmp_path / "events.jsonl"
    events.write_text("some content\n", encoding="utf-8")

    # Patch Path.open to raise OSError (the function uses events_path.open(...))
    with patch.object(Path, "open", side_effect=OSError("permission denied")):
        result = first_copilot_user_message(events)
    assert result == ""
