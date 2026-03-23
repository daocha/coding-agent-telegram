import pytest

from coding_agent_telegram.config import load_config


def test_load_config_required(monkeypatch):
    monkeypatch.setenv("WORKSPACE_ROOT", "~/git")
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "token")
    monkeypatch.setenv("ALLOWED_CHAT_ID", "123")

    cfg = load_config()
    assert cfg.workspace_root.name == "git"
    assert cfg.allowed_chat_ids == {123}
    assert cfg.codex_approval_policy == "never"
    assert cfg.codex_sandbox_mode == "workspace-write"
    assert cfg.default_agent_provider == "codex"


def test_load_config_missing(monkeypatch):
    monkeypatch.delenv("WORKSPACE_ROOT", raising=False)
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    monkeypatch.delenv("ALLOWED_CHAT_ID", raising=False)
    monkeypatch.delenv("ALLOWED_CHAT_IDS", raising=False)

    with pytest.raises(ValueError):
        load_config()
