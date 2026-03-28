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


def test_scrub_secrets_redacts_openai_project_key():
    text = "OpenAI key sk-proj-ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghij1234567890"
    result = _scrub_secrets(text)
    assert "<openai-project-key>" in result
    assert "sk-proj-ABCDEFGHIJKLMNOPQRSTUVWXYZ" not in result


def test_scrub_secrets_redacts_anthropic_key():
    text = "Anthropic key sk-ant-api03-ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghij1234567890"
    result = _scrub_secrets(text)
    assert "<anthropic-key>" in result
    assert "sk-ant-api03-" not in result


def test_scrub_secrets_redacts_stripe_secret_key():
    text = "Stripe key sk_live_ABCDEFGHIJKLMNOPQRSTUVWXYZ123456"
    result = _scrub_secrets(text)
    assert "<stripe-secret-key>" in result
    assert "sk_live_" not in result


def test_scrub_secrets_redacts_jwt_like_token():
    text = "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IlRlc3QgVXNlciIsImlhdCI6MTUxNjIzOTAyMn0.c2lnbmF0dXJlVmFsdWVFeGFtcGxlMTIzNDU2Nzg5MA"
    result = _scrub_secrets(text)
    assert "<jwt-like-token>" in result
    assert "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9" not in result


def test_scrub_secrets_redacts_ssh_public_key_ed25519():
    text = "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAINPZxtCMs5sIfsMWpq7SHuqFFpBtSTmFqXWOYdf6dX4i your_email@example.com"
    result = _scrub_secrets(text)
    assert "<ssh-public-key>" in result
    assert "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5" not in result


def test_scrub_secrets_redacts_ssh_public_key_rsa():
    text = "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQCy1gU1s6n5r4qV2bFJ8XH4m2J3J4k5L6m7N8o9P0q1R2s3T4u5V6w7X8y9Z0 test@example.com"
    result = _scrub_secrets(text)
    assert "<ssh-public-key>" in result
    assert "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQ" not in result


def test_scrub_secrets_redacts_passwd_like_line():
    text = "root:x:0:0:root:/root:/bin/bash"
    result = _scrub_secrets(text)
    assert result == "<passwd-like-line>"


def test_scrub_secrets_redacts_shadow_like_line():
    text = "root:$6$rounds=656000$saltvalue$hashedsecretvaluegoeshere:19793:0:99999:7:::"
    result = _scrub_secrets(text)
    assert result == "<shadow-like-line>"


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


def test_scrub_secrets_redacts_pem_like_text():
    text = (
        "cert:\n"
        "-----BEGIN PRIVATE KEY-----\n"
        "abc123ABC123abc123ABC123abc123ABC123abc123ABC123\n"
        "-----END PRIVATE KEY-----"
    )
    result = _scrub_secrets(text)
    assert "<pem-like-text>" in result
    assert "BEGIN PRIVATE KEY" not in result


def test_scrub_secrets_redacts_certificate_block():
    text = (
        "-----BEGIN CERTIFICATE-----\n"
        "MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAtesttesttesttest\n"
        "-----END CERTIFICATE-----"
    )
    result = _scrub_secrets(text)
    assert "<crt-like-text>" in result
    assert "BEGIN CERTIFICATE" not in result


def test_scrub_secrets_redacts_hex_like_text():
    text = "fingerprint deadbeefdeadbeefdeadbeefdeadbeefdeadbeefdeadbeefdeadbeefdeadbeef"
    result = _scrub_secrets(text)
    assert "<hex-like-text>" in result
    assert "deadbeefdeadbeef" not in result


def test_scrub_secrets_redacts_base64_like_text():
    text = "blob QUJDREVGR0hJSktMTU5PUFFSU1RVVldYWVo0MTIzNDU2Nzg5MDEyMzQ1Njc4OTA="
    result = _scrub_secrets(text)
    assert "<base64-like-text>" in result
    assert "QUJDREVGR0hJ" not in result


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


def test_sanitize_agent_error_normalizes_abort_message_with_path():
    text = "Agent run aborted by /Users/daocha/.coding-agent-telegram/queued_questions/abc.txt"
    assert _sanitize_agent_error(text) == "Agent run aborted by /abort."


def test_sanitize_agent_error_normalizes_abort_message_without_path():
    text = "Agent run aborted by."
    assert _sanitize_agent_error(text) == "Agent run aborted by /abort."
