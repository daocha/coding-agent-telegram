from __future__ import annotations

import io
from pathlib import Path

from coding_agent_telegram.agent_runner import MultiAgentRunner
from coding_agent_telegram.claude_health import check_claude_auth


class FakePopen:
    def __init__(self, stdout: str = "", stderr: str = "", returncode: int = 0):
        self.stdout = io.StringIO(stdout)
        self.stderr = io.StringIO(stderr)
        self.returncode = returncode

    def poll(self):
        return self.returncode

    def kill(self):
        self.returncode = -9

    def terminate(self):
        self.returncode = -15


def _make_runner() -> MultiAgentRunner:
    return MultiAgentRunner(
        codex_bin="codex",
        copilot_bin="copilot",
        approval_policy="never",
        sandbox_mode="read-only",
        claude_bin="claude",
    )


def test_check_claude_auth_healthy(monkeypatch, tmp_path):
    stdout = (
        '{"type":"system","subtype":"init","session_id":"abc-123"}\n'
        '{"type":"result","is_error":false,"result":"ok"}\n'
    )
    monkeypatch.setattr(
        "coding_agent_telegram.agent_runner.subprocess.Popen",
        lambda *a, **k: FakePopen(stdout=stdout, returncode=0),
    )

    result = check_claude_auth(_make_runner(), tmp_path / "scratch")

    assert result.healthy is True
    assert result.is_auth_failure is False
    assert result.detail == ""


def test_check_claude_auth_detects_auth_failure(monkeypatch, tmp_path):
    # No "result" event at all -- the CLI can exit after an early auth failure
    # without ever emitting one, so session_lifecycle_commands.py's own success
    # check (`not result.success or not result.session_id`) is what actually
    # catches this, not `parsed_success`. This mirrors that exact shape.
    stdout = (
        '{"type":"system","subtype":"init"}\n'
        '{"type":"result","is_error":true,'
        '"result":"Failed to authenticate: OAuth session expired and could not be refreshed"}\n'
    )
    monkeypatch.setattr(
        "coding_agent_telegram.agent_runner.subprocess.Popen",
        lambda *a, **k: FakePopen(stdout=stdout, returncode=0),
    )

    result = check_claude_auth(_make_runner(), tmp_path / "scratch")

    assert result.healthy is False
    assert result.is_auth_failure is True
    assert "authenticate" in result.detail.lower()


def test_check_claude_auth_missing_session_id_is_unhealthy(monkeypatch, tmp_path):
    # success stays True by default when no "result" event appears at all, but
    # there's still no session_id -- must not be reported healthy.
    stdout = '{"type":"system","subtype":"init"}\n'
    monkeypatch.setattr(
        "coding_agent_telegram.agent_runner.subprocess.Popen",
        lambda *a, **k: FakePopen(stdout=stdout, returncode=0),
    )

    result = check_claude_auth(_make_runner(), tmp_path / "scratch")

    assert result.healthy is False
    assert result.is_auth_failure is False


def test_check_claude_auth_non_auth_failure(monkeypatch, tmp_path):
    stdout = '{"type":"result","is_error":true,"result":"Rate limit exceeded."}\n'
    monkeypatch.setattr(
        "coding_agent_telegram.agent_runner.subprocess.Popen",
        lambda *a, **k: FakePopen(stdout=stdout, returncode=0),
    )

    result = check_claude_auth(_make_runner(), tmp_path / "scratch")

    assert result.healthy is False
    assert result.is_auth_failure is False
    assert result.detail == "Rate limit exceeded."


def test_check_claude_auth_creates_scratch_dir(monkeypatch, tmp_path):
    stdout = '{"type":"result","is_error":false,"result":"ok"}\n'
    monkeypatch.setattr(
        "coding_agent_telegram.agent_runner.subprocess.Popen",
        lambda *a, **k: FakePopen(stdout=stdout, returncode=0),
    )
    scratch_dir = tmp_path / "does" / "not" / "exist" / "yet"

    check_claude_auth(_make_runner(), scratch_dir)

    assert scratch_dir.is_dir()
