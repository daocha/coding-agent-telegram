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


def test_load_config_missing(monkeypatch):
    monkeypatch.delenv("WORKSPACE_ROOT", raising=False)
    monkeypatch.delenv("TELEGRAM_BOT_TOKENS", raising=False)
    monkeypatch.delenv("ALLOWED_CHAT_IDS", raising=False)

    with pytest.raises(ValueError):
        load_config()
