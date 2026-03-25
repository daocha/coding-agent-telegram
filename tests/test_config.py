from pathlib import Path

import pytest

import coding_agent_telegram.config as config_module
from coding_agent_telegram.config import load_config


def _isolate_env(monkeypatch, tmp_path):
    monkeypatch.setattr(config_module, "load_dotenv", lambda *args, **kwargs: None)
    for name in (
        "WORKSPACE_ROOT",
        "TELEGRAM_BOT_TOKENS",
        "ALLOWED_CHAT_IDS",
        "STATE_FILE",
        "STATE_BACKUP_FILE",
        "LOG_LEVEL",
        "LOG_DIR",
        "CODEX_BIN",
        "COPILOT_BIN",
        "CODEX_MODEL",
        "COPILOT_MODEL",
        "COPILOT_AUTOPILOT",
        "COPILOT_NO_ASK_USER",
        "COPILOT_ALLOW_ALL",
        "COPILOT_ALLOW_ALL_TOOLS",
        "COPILOT_ALLOW_TOOLS",
        "COPILOT_DENY_TOOLS",
        "COPILOT_AVAILABLE_TOOLS",
        "CODEX_APPROVAL_POLICY",
        "CODEX_SANDBOX_MODE",
        "CODEX_SKIP_GIT_REPO_CHECK",
        "ENABLE_COMMIT_COMMAND",
        "SNAPSHOT_TEXT_FILE_MAX_BYTES",
        "MAX_TELEGRAM_MESSAGE_LENGTH",
        "ENABLE_SENSITIVE_DIFF_FILTER",
        "DEFAULT_AGENT_PROVIDER",
    ):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".env").write_text("", encoding="utf-8")


def test_load_config_required(monkeypatch, tmp_path):
    _isolate_env(monkeypatch, tmp_path)
    monkeypatch.setenv("WORKSPACE_ROOT", "~/git")
    monkeypatch.setenv("TELEGRAM_BOT_TOKENS", "token-a, token-b")
    monkeypatch.setenv("ALLOWED_CHAT_IDS", "123,456")
    monkeypatch.setenv("CODEX_APPROVAL_POLICY", "never")
    monkeypatch.setenv("CODEX_SANDBOX_MODE", "workspace-write")
    monkeypatch.setenv("CODEX_SKIP_GIT_REPO_CHECK", "false")
    monkeypatch.setenv("ENABLE_COMMIT_COMMAND", "false")
    monkeypatch.setenv("SNAPSHOT_TEXT_FILE_MAX_BYTES", str(DEFAULT_SNAPSHOT_TEXT_FILE_MAX_BYTES))
    monkeypatch.setenv("MAX_TELEGRAM_MESSAGE_LENGTH", str(DEFAULT_MAX_TELEGRAM_MESSAGE_LENGTH))
    monkeypatch.setenv("DEFAULT_AGENT_PROVIDER", "codex")
    monkeypatch.setenv("LOG_DIR", "./logs")
    monkeypatch.setenv("CODEX_MODEL", "")
    monkeypatch.setenv("COPILOT_MODEL", "")
    monkeypatch.setenv("COPILOT_AUTOPILOT", "true")
    monkeypatch.setenv("COPILOT_NO_ASK_USER", "true")
    monkeypatch.setenv("COPILOT_ALLOW_ALL", "true")
    monkeypatch.setenv("COPILOT_ALLOW_ALL_TOOLS", "false")
    monkeypatch.setenv("COPILOT_ALLOW_TOOLS", "")
    monkeypatch.setenv("COPILOT_DENY_TOOLS", "")
    monkeypatch.setenv("COPILOT_AVAILABLE_TOOLS", "")

    cfg = load_config()
    assert cfg.workspace_root.name == "git"
    assert cfg.telegram_bot_tokens == ("token-a", "token-b")
    assert cfg.allowed_chat_ids == {123, 456}
    assert cfg.codex_approval_policy == "never"
    assert cfg.codex_sandbox_mode == "workspace-write"
    assert cfg.codex_skip_git_repo_check is False
    assert cfg.enable_commit_command is False
    assert cfg.snapshot_text_file_max_bytes == DEFAULT_SNAPSHOT_TEXT_FILE_MAX_BYTES
    assert cfg.max_telegram_message_length == DEFAULT_MAX_TELEGRAM_MESSAGE_LENGTH
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


def test_load_config_missing(monkeypatch, tmp_path):
    _isolate_env(monkeypatch, tmp_path)

    with pytest.raises(ValueError):
        load_config()


def test_load_config_commit_command_enabled(monkeypatch, tmp_path):
    _isolate_env(monkeypatch, tmp_path)
    monkeypatch.setenv("WORKSPACE_ROOT", "~/git")
    monkeypatch.setenv("TELEGRAM_BOT_TOKENS", "token-a")
    monkeypatch.setenv("ALLOWED_CHAT_IDS", "123")
    monkeypatch.setenv("ENABLE_COMMIT_COMMAND", "true")

    cfg = load_config()

    assert cfg.enable_commit_command is True


def test_load_config_snapshot_limit_override(monkeypatch, tmp_path):
    _isolate_env(monkeypatch, tmp_path)
    monkeypatch.setenv("WORKSPACE_ROOT", "~/git")
    monkeypatch.setenv("TELEGRAM_BOT_TOKENS", "token-a")
    monkeypatch.setenv("ALLOWED_CHAT_IDS", "123")
    monkeypatch.setenv("SNAPSHOT_TEXT_FILE_MAX_BYTES", "4096")

    cfg = load_config()

    assert cfg.snapshot_text_file_max_bytes == 4096
