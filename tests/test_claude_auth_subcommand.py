from types import SimpleNamespace

import pytest

import coding_agent_telegram.cli as cli
from coding_agent_telegram.claude_health import ClaudeHealthResult


def _patch_common(monkeypatch, tmp_path, *, existing_token=None):
    env_path = tmp_path / ".env"
    if existing_token is not None:
        env_path.write_text(f"CLAUDE_CODE_OAUTH_TOKEN={existing_token}\n", encoding="utf-8")
    monkeypatch.setattr(cli, "_ensure_env_file", lambda: (env_path, None))
    monkeypatch.setattr(cli, "load_config", lambda path: SimpleNamespace(app_internal_root=tmp_path))
    monkeypatch.setattr(cli, "_build_runner", lambda cfg, **kwargs: object())
    monkeypatch.delenv("CLAUDE_CODE_OAUTH_TOKEN", raising=False)
    return env_path


def test_declining_verification_just_saves_the_token(monkeypatch, tmp_path):
    env_path = _patch_common(monkeypatch, tmp_path)
    monkeypatch.setattr(cli, "_prompt_yes_no", lambda *a, **k: False)
    checked = {"called": False}
    monkeypatch.setattr(cli, "check_claude_auth", lambda *a, **k: checked.__setitem__("called", True))

    cli._run_claude_auth_subcommand(["sk-ant-oat01-newtoken"])

    assert checked["called"] is False
    assert "CLAUDE_CODE_OAUTH_TOKEN=sk-ant-oat01-newtoken" in env_path.read_text(encoding="utf-8")


def test_accepting_verification_uses_the_cheap_model_and_keeps_token_on_success(monkeypatch, tmp_path):
    env_path = _patch_common(monkeypatch, tmp_path)
    monkeypatch.setattr(cli, "_prompt_yes_no", lambda *a, **k: True)
    seen_kwargs = {}

    def fake_check(runner, scratch_dir):
        return ClaudeHealthResult(healthy=True, is_auth_failure=False, detail="")

    build_calls = []
    monkeypatch.setattr(
        cli, "_build_runner", lambda cfg, **kwargs: build_calls.append(kwargs) or object()
    )
    monkeypatch.setattr(cli, "check_claude_auth", fake_check)

    cli._run_claude_auth_subcommand(["sk-ant-oat01-newtoken"])

    assert build_calls == [{"claude_model": cli.CLAUDE_AUTH_VERIFY_MODEL}]
    assert "CLAUDE_CODE_OAUTH_TOKEN=sk-ant-oat01-newtoken" in env_path.read_text(encoding="utf-8")
    monkeypatch.delenv("CLAUDE_CODE_OAUTH_TOKEN", raising=False)


def test_failed_verification_rolls_back_to_previous_token(monkeypatch, tmp_path):
    env_path = _patch_common(monkeypatch, tmp_path, existing_token="sk-ant-oat01-oldtoken")
    monkeypatch.setattr(cli, "_prompt_yes_no", lambda *a, **k: True)
    monkeypatch.setattr(
        cli,
        "check_claude_auth",
        lambda *a, **k: ClaudeHealthResult(healthy=False, is_auth_failure=True, detail="401 Invalid bearer token"),
    )

    with pytest.raises(SystemExit):
        cli._run_claude_auth_subcommand(["sk-ant-oat01-newtoken"])

    text = env_path.read_text(encoding="utf-8")
    assert "CLAUDE_CODE_OAUTH_TOKEN=sk-ant-oat01-oldtoken" in text
    assert "newtoken" not in text
    monkeypatch.delenv("CLAUDE_CODE_OAUTH_TOKEN", raising=False)


def test_failed_verification_removes_token_when_none_existed_before(monkeypatch, tmp_path):
    env_path = _patch_common(monkeypatch, tmp_path)
    monkeypatch.setattr(cli, "_prompt_yes_no", lambda *a, **k: True)
    monkeypatch.setattr(
        cli,
        "check_claude_auth",
        lambda *a, **k: ClaudeHealthResult(healthy=False, is_auth_failure=True, detail="401 Invalid bearer token"),
    )

    with pytest.raises(SystemExit):
        cli._run_claude_auth_subcommand(["sk-ant-oat01-newtoken"])

    text = env_path.read_text(encoding="utf-8") if env_path.exists() else ""
    assert "CLAUDE_CODE_OAUTH_TOKEN" not in text
    monkeypatch.delenv("CLAUDE_CODE_OAUTH_TOKEN", raising=False)
