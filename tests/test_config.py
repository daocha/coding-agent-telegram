import pytest

from coding_agent_telegram.config import load_config


def test_load_config_required(monkeypatch):
    monkeypatch.setenv("WORKSPACE_ROOT", "~/git")
    monkeypatch.setenv("TELEGRAM_BOT_TOKENS", "token-a, token-b")
    monkeypatch.setenv("ALLOWED_CHAT_IDS", "123,456")

    cfg = load_config()
    assert cfg.workspace_root.name == "git"
    assert cfg.telegram_bot_tokens == ("token-a", "token-b")
    assert cfg.allowed_chat_ids == {123, 456}
    assert cfg.codex_approval_policy == "never"
    assert cfg.codex_sandbox_mode == "workspace-write"
    assert cfg.codex_skip_git_repo_check is False
    assert cfg.default_agent_provider == "codex"
    assert cfg.log_dir.name == "logs"
    assert cfg.codex_model == ""
    assert cfg.copilot_model == ""
    assert cfg.copilot_autopilot is True
    assert cfg.copilot_no_ask_user is True
    assert cfg.copilot_allow_all is True
    assert cfg.copilot_allow_all_tools is False
    assert cfg.copilot_allow_tools == ()
    assert cfg.copilot_deny_tools == ()
    assert cfg.copilot_available_tools == ()


def test_load_config_missing(monkeypatch):
    monkeypatch.delenv("WORKSPACE_ROOT", raising=False)
    monkeypatch.delenv("TELEGRAM_BOT_TOKENS", raising=False)
    monkeypatch.delenv("ALLOWED_CHAT_IDS", raising=False)

    with pytest.raises(ValueError):
        load_config()
