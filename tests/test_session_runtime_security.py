"""Tests for output-sanitization helpers in session_runtime."""
from __future__ import annotations

from coding_agent_telegram.session_runtime import _sanitize_agent_error, _scrub_secrets


# ---------------------------------------------------------------------------
# _scrub_secrets
# ---------------------------------------------------------------------------


def test_scrub_secrets_redacts_telegram_bot_token():
    text = "Token is 1234567890:AAHabcdefghij0123456789ABCDEFGHIJklm in config."
    result = _scrub_secrets(text)
    assert "<telegram-token>" in result
    assert "AAHabcdefghij0123456789ABCDEFGHIJklm" not in result


def test_scrub_secrets_redacts_github_pat():
    # GitHub PAT pattern requires 36+ alphanumeric chars after the prefix.
    text = "Use token ghp_ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghij1234 for auth."
    result = _scrub_secrets(text)
    assert "<github-token>" in result
    assert "ghp_ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghij1234" not in result


def test_scrub_secrets_redacts_aws_access_key():
    text = "AWS key: AKIAIOSFODNN7EXAMPLE is set."
    result = _scrub_secrets(text)
    assert "<aws-access-key>" in result
    assert "AKIAIOSFODNN7EXAMPLE" not in result


def test_scrub_secrets_leaves_normal_text_unchanged():
    text = "Updated README with installation steps and examples."
    assert _scrub_secrets(text) == text


def test_scrub_secrets_leaves_short_token_like_strings_unchanged():
    # A short string that does not match any pattern must pass through.
    text = "Session ID: abc-123"
    assert _scrub_secrets(text) == text


def test_scrub_secrets_handles_multiple_secrets_in_same_text():
    text = (
        "bot token: 9876543210:BBHabcdefghij0123456789ABCDEFGHIJklm "
        "github: ghs_ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghij1234"
    )
    result = _scrub_secrets(text)
    assert "<telegram-token>" in result
    assert "<github-token>" in result
    assert "BBHabcdefghij" not in result
    assert "ghs_ABCDE" not in result


# ---------------------------------------------------------------------------
# _sanitize_agent_error
# ---------------------------------------------------------------------------


def test_sanitize_agent_error_redacts_unix_absolute_path():
    text = "Cannot read /home/user/projects/myapp/config.py"
    result = _sanitize_agent_error(text)
    assert "<path>" in result
    assert "/home/user/projects" not in result


def test_sanitize_agent_error_redacts_windows_absolute_path():
    text = r"File not found: C:\Users\rayli\project\src\main.py"
    result = _sanitize_agent_error(text)
    assert "<path>" in result
    assert r"C:\Users\rayli" not in result


def test_sanitize_agent_error_leaves_relative_paths_unchanged():
    text = "Could not open src/main.py for reading"
    assert _sanitize_agent_error(text) == text


def test_sanitize_agent_error_leaves_plain_messages_unchanged():
    text = "Agent timed out after 300 seconds."
    assert _sanitize_agent_error(text) == text
