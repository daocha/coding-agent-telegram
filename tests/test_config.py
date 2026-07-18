from pathlib import Path
from types import SimpleNamespace

import pytest

import coding_agent_telegram.config as config_module
from coding_agent_telegram.config import (
    DEFAULT_MAX_TELEGRAM_MESSAGE_LENGTH,
    DEFAULT_OPENAI_WHISPER_MODEL,
    DEFAULT_OPENAI_WHISPER_TIMEOUT_SECONDS,
    DEFAULT_SNAPSHOT_TEXT_FILE_MAX_BYTES,
    create_initial_env_file,
    detect_system_locale,
    load_config,
    resolve_app_internal_root,
    resolve_default_state_file_path,
    resolve_env_file_path,
    resolve_user_home,
)


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
        "CLAUDE_BIN",
        "CODEX_MODEL",
        "COPILOT_MODEL",
        "CLAUDE_MODEL",
        "COPILOT_AUTOPILOT",
        "COPILOT_NO_ASK_USER",
        "COPILOT_ALLOW_ALL",
        "COPILOT_ALLOW_ALL_TOOLS",
        "COPILOT_ALLOW_TOOLS",
        "COPILOT_DENY_TOOLS",
        "COPILOT_AVAILABLE_TOOLS",
        "CLAUDE_PERMISSION_MODE",
        "CLAUDE_ALLOWED_TOOLS",
        "CLAUDE_DISALLOWED_TOOLS",
        "CODEX_APPROVAL_POLICY",
        "CODEX_SANDBOX_MODE",
        "CODEX_SKIP_GIT_REPO_CHECK",
        "ENABLE_COMMIT_COMMAND",
        "SNAPSHOT_TEXT_FILE_MAX_BYTES",
        "MAX_TELEGRAM_MESSAGE_LENGTH",
        "ENABLE_SENSITIVE_DIFF_FILTER",
        "ENABLE_SECRET_SCRUB_FILTER",
        "ENABLE_OPENAI_WHISPER_SPEECH_TO_TEXT",
        "OPENAI_WHISPER_MODEL",
        "OPENAI_WHISPER_TIMEOUT_SECONDS",
        "APP_LOCALE",
        "DEFAULT_AGENT_PROVIDER",
    ):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".env").write_text("", encoding="utf-8")


def test_load_config_required(monkeypatch, tmp_path):
    _isolate_env(monkeypatch, tmp_path)
    home = tmp_path / "home"
    monkeypatch.setattr(Path, "home", lambda: home)
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
    assert cfg.enable_secret_scrub_filter is True
    assert cfg.enable_openai_whisper_speech_to_text is False
    assert cfg.openai_whisper_model == DEFAULT_OPENAI_WHISPER_MODEL
    assert cfg.openai_whisper_timeout_seconds == DEFAULT_OPENAI_WHISPER_TIMEOUT_SECONDS
    assert cfg.locale == "en"
    assert cfg.default_agent_provider == "codex"
    assert cfg.log_dir.name == "logs"
    assert cfg.codex_model == ""
    assert cfg.copilot_model == ""
    assert cfg.claude_model == ""
    assert cfg.copilot_autopilot is True
    assert cfg.copilot_no_ask_user is True
    assert cfg.copilot_allow_all is True
    assert cfg.copilot_allow_all_tools is False
    assert cfg.copilot_allow_tools == ()
    assert cfg.copilot_deny_tools == ()
    assert cfg.copilot_available_tools == ()
    assert cfg.claude_bin == "claude"
    assert cfg.claude_permission_mode == "bypassPermissions"
    assert cfg.claude_allowed_tools == ()
    assert cfg.claude_disallowed_tools == ()
    assert cfg.state_file == home / ".coding-agent-telegram" / "state.json"
    assert cfg.state_backup_file == home / ".coding-agent-telegram" / "state.json.bak"


def test_load_config_missing(monkeypatch, tmp_path):
    _isolate_env(monkeypatch, tmp_path)

    with pytest.raises(ValueError):
        load_config()


def test_load_config_accepts_claude_as_default_provider(monkeypatch, tmp_path):
    _isolate_env(monkeypatch, tmp_path)
    monkeypatch.setenv("WORKSPACE_ROOT", "~/git")
    monkeypatch.setenv("TELEGRAM_BOT_TOKENS", "token-a")
    monkeypatch.setenv("ALLOWED_CHAT_IDS", "123")
    monkeypatch.setenv("DEFAULT_AGENT_PROVIDER", "claude")

    cfg = load_config()

    assert cfg.default_agent_provider == "claude"


def test_load_config_rejects_unknown_default_provider(monkeypatch, tmp_path):
    _isolate_env(monkeypatch, tmp_path)
    monkeypatch.setenv("WORKSPACE_ROOT", "~/git")
    monkeypatch.setenv("TELEGRAM_BOT_TOKENS", "token-a")
    monkeypatch.setenv("ALLOWED_CHAT_IDS", "123")
    monkeypatch.setenv("DEFAULT_AGENT_PROVIDER", "gemini")

    with pytest.raises(ValueError, match="DEFAULT_AGENT_PROVIDER"):
        load_config()


def test_load_config_claude_overrides(monkeypatch, tmp_path):
    _isolate_env(monkeypatch, tmp_path)
    monkeypatch.setenv("WORKSPACE_ROOT", "~/git")
    monkeypatch.setenv("TELEGRAM_BOT_TOKENS", "token-a")
    monkeypatch.setenv("ALLOWED_CHAT_IDS", "123")
    monkeypatch.setenv("CLAUDE_BIN", "/opt/bin/claude")
    monkeypatch.setenv("CLAUDE_MODEL", "opus")
    monkeypatch.setenv("CLAUDE_PERMISSION_MODE", "acceptEdits")
    monkeypatch.setenv("CLAUDE_ALLOWED_TOOLS", "Read,Edit,Bash(git *)")
    monkeypatch.setenv("CLAUDE_DISALLOWED_TOOLS", "Bash(rm *)")

    cfg = load_config()

    assert cfg.claude_bin == "/opt/bin/claude"
    assert cfg.claude_model == "opus"
    assert cfg.claude_permission_mode == "acceptEdits"
    assert cfg.claude_allowed_tools == ("Read", "Edit", "Bash(git *)")
    assert cfg.claude_disallowed_tools == ("Bash(rm *)",)


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


def test_load_config_secret_scrub_filter_can_be_disabled(monkeypatch, tmp_path):
    _isolate_env(monkeypatch, tmp_path)
    monkeypatch.setenv("WORKSPACE_ROOT", "~/git")
    monkeypatch.setenv("TELEGRAM_BOT_TOKENS", "token-a")
    monkeypatch.setenv("ALLOWED_CHAT_IDS", "123")
    monkeypatch.setenv("ENABLE_SECRET_SCRUB_FILTER", "false")

    cfg = load_config()

    assert cfg.enable_secret_scrub_filter is False


def test_load_config_whisper_speech_to_text_can_be_enabled(monkeypatch, tmp_path):
    _isolate_env(monkeypatch, tmp_path)
    monkeypatch.setenv("WORKSPACE_ROOT", "~/git")
    monkeypatch.setenv("TELEGRAM_BOT_TOKENS", "token-a")
    monkeypatch.setenv("ALLOWED_CHAT_IDS", "123")
    monkeypatch.setenv("ENABLE_OPENAI_WHISPER_SPEECH_TO_TEXT", "true")

    cfg = load_config()

    assert cfg.enable_openai_whisper_speech_to_text is True


def test_load_config_whisper_model_and_timeout_override(monkeypatch, tmp_path):
    _isolate_env(monkeypatch, tmp_path)
    monkeypatch.setenv("WORKSPACE_ROOT", "~/git")
    monkeypatch.setenv("TELEGRAM_BOT_TOKENS", "token-a")
    monkeypatch.setenv("ALLOWED_CHAT_IDS", "123")
    monkeypatch.setenv("OPENAI_WHISPER_MODEL", "turbo")
    monkeypatch.setenv("OPENAI_WHISPER_TIMEOUT_SECONDS", "300")

    cfg = load_config()

    assert cfg.openai_whisper_model == "turbo"
    assert cfg.openai_whisper_timeout_seconds == 300


def test_load_config_locale_override(monkeypatch, tmp_path):
    _isolate_env(monkeypatch, tmp_path)
    monkeypatch.setenv("WORKSPACE_ROOT", "~/git")
    monkeypatch.setenv("TELEGRAM_BOT_TOKENS", "token-a")
    monkeypatch.setenv("ALLOWED_CHAT_IDS", "123")
    monkeypatch.setenv("APP_LOCALE", "zh-TW")

    cfg = load_config()

    assert cfg.locale == "zh-TW"


def test_load_config_invalid_locale_falls_back_to_en(monkeypatch, tmp_path):
    _isolate_env(monkeypatch, tmp_path)
    monkeypatch.setenv("WORKSPACE_ROOT", "~/git")
    monkeypatch.setenv("TELEGRAM_BOT_TOKENS", "token-a")
    monkeypatch.setenv("ALLOWED_CHAT_IDS", "123")
    monkeypatch.setenv("APP_LOCALE", "es")

    cfg = load_config()

    assert cfg.locale == "en"


def test_resolve_env_file_path_uses_explicit_env_override(monkeypatch, tmp_path):
    env_path = tmp_path / "custom.env"
    monkeypatch.setenv("CODING_AGENT_TELEGRAM_ENV_FILE", str(env_path))

    assert resolve_env_file_path() == env_path


def test_resolve_env_file_path_prefers_home_app_specific_file(monkeypatch, tmp_path):
    home = tmp_path / "home"
    monkeypatch.setattr(Path, "home", lambda: home)
    home_env_path = home / ".coding-agent-telegram" / ".env_coding_agent_telegram"
    home_env_path.parent.mkdir(parents=True, exist_ok=True)
    home_env_path.write_text("", encoding="utf-8")
    monkeypatch.chdir(tmp_path)

    assert resolve_env_file_path() == home_env_path


def test_resolve_env_file_path_prefers_app_specific_file(monkeypatch, tmp_path):
    app_env_path = tmp_path / ".env_coding_agent_telegram"
    app_env_path.write_text("", encoding="utf-8")
    monkeypatch.setattr(Path, "home", lambda: tmp_path / "home")
    monkeypatch.chdir(tmp_path)

    assert resolve_env_file_path() == app_env_path


def test_resolve_env_file_path_uses_home_default_when_cwd_file_is_missing(monkeypatch, tmp_path):
    home = tmp_path / "home"
    monkeypatch.setattr(Path, "home", lambda: tmp_path / "home")
    monkeypatch.chdir(tmp_path)

    assert resolve_env_file_path() == home / ".coding-agent-telegram" / ".env_coding_agent_telegram"


def test_load_config_uses_env_file_and_overrides_empty_process_values(monkeypatch, tmp_path):
    env_path = tmp_path / ".env"
    env_path.write_text(
        "\n".join(
            (
                "WORKSPACE_ROOT=~/git",
                "TELEGRAM_BOT_TOKENS=token-a",
                "ALLOWED_CHAT_IDS=123",
            )
        )
        + "\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("WORKSPACE_ROOT", "")
    monkeypatch.chdir(tmp_path)

    cfg = load_config(env_path)

    assert cfg.workspace_root.name == "git"
    assert cfg.telegram_bot_tokens == ("token-a",)
    assert cfg.allowed_chat_ids == {123}


def test_load_config_prefers_home_internal_app_root(monkeypatch, tmp_path):
    _isolate_env(monkeypatch, tmp_path)
    home = tmp_path / "home"
    monkeypatch.setattr(Path, "home", lambda: home)
    home_internal_root = home / ".coding-agent-telegram"
    home_internal_root.mkdir(parents=True)
    monkeypatch.setenv("WORKSPACE_ROOT", str(tmp_path / "workspace"))
    monkeypatch.setenv("TELEGRAM_BOT_TOKENS", "token-a")
    monkeypatch.setenv("ALLOWED_CHAT_IDS", "123")

    cfg = load_config()

    assert cfg.app_internal_root == home_internal_root


def test_resolve_user_home_uses_current_user_when_not_running_under_sudo(monkeypatch, tmp_path):
    real_home = tmp_path / "real-home"
    monkeypatch.delenv("SUDO_USER", raising=False)
    monkeypatch.setattr(Path, "home", lambda: real_home)

    assert resolve_user_home() == real_home


def test_default_app_internal_root_uses_sudo_user_home(monkeypatch, tmp_path):
    root_home = tmp_path / "root-home"
    sudo_home = tmp_path / "sudo-home"
    monkeypatch.setattr(Path, "home", lambda: root_home)
    monkeypatch.setenv("SUDO_USER", "exampleuser")
    monkeypatch.setattr(config_module.pwd, "getpwnam", lambda _user: SimpleNamespace(pw_dir=str(sudo_home)))

    assert config_module.default_app_internal_root() == sudo_home / ".coding-agent-telegram"


def test_resolve_user_home_falls_back_to_current_user_when_sudo_user_is_missing(monkeypatch, tmp_path):
    root_home = tmp_path / "root-home"
    monkeypatch.setattr(Path, "home", lambda: root_home)
    monkeypatch.setenv("SUDO_USER", "missinguser")

    def _raise_key_error(_user):
        raise KeyError("missing user")

    monkeypatch.setattr(config_module.pwd, "getpwnam", _raise_key_error)

    assert resolve_user_home() == root_home


def test_load_config_falls_back_to_workspace_internal_app_root(monkeypatch, tmp_path):
    _isolate_env(monkeypatch, tmp_path)
    home = tmp_path / "home"
    monkeypatch.setattr(Path, "home", lambda: home)
    workspace_root = tmp_path / "workspace"
    workspace_internal_root = workspace_root / ".coding-agent-telegram"
    workspace_internal_root.mkdir(parents=True)
    monkeypatch.setenv("WORKSPACE_ROOT", str(workspace_root))
    monkeypatch.setenv("TELEGRAM_BOT_TOKENS", "token-a")
    monkeypatch.setenv("ALLOWED_CHAT_IDS", "123")

    cfg = load_config()

    assert cfg.app_internal_root == workspace_internal_root


def test_resolve_app_internal_root_defaults_to_home_when_neither_exists(monkeypatch, tmp_path):
    home = tmp_path / "home"
    workspace_root = tmp_path / "workspace"
    monkeypatch.setattr(Path, "home", lambda: home)

    assert resolve_app_internal_root(workspace_root) == home / ".coding-agent-telegram"


def test_resolve_default_state_file_path_prefers_home_file(monkeypatch, tmp_path):
    home = tmp_path / "home"
    monkeypatch.setattr(Path, "home", lambda: home)
    home_state = home / ".coding-agent-telegram" / "state.json"
    home_state.parent.mkdir(parents=True, exist_ok=True)
    home_state.write_text("{}", encoding="utf-8")
    monkeypatch.chdir(tmp_path)

    assert resolve_default_state_file_path("state.json") == home_state


def test_resolve_default_state_file_path_falls_back_to_cwd_file(monkeypatch, tmp_path):
    home = tmp_path / "home"
    monkeypatch.setattr(Path, "home", lambda: home)
    cwd_state = tmp_path / "state.json"
    cwd_state.write_text("{}", encoding="utf-8")
    monkeypatch.chdir(tmp_path)

    assert resolve_default_state_file_path("state.json") == cwd_state


def test_resolve_default_state_file_path_defaults_to_home_when_neither_exists(monkeypatch, tmp_path):
    home = tmp_path / "home"
    monkeypatch.setattr(Path, "home", lambda: home)
    monkeypatch.chdir(tmp_path)

    assert resolve_default_state_file_path("state.json") == home / ".coding-agent-telegram" / "state.json"


# ---------------------------------------------------------------------------
# _parse_bool edge cases
# ---------------------------------------------------------------------------


def test_parse_bool_accepts_truthy_values():
    from coding_agent_telegram.config import _parse_bool

    for val in ("1", "true", "True", "TRUE", "yes", "on"):
        assert _parse_bool(val) is True, f"Expected True for {val!r}"


def test_parse_bool_treats_none_as_default():
    from coding_agent_telegram.config import _parse_bool

    assert _parse_bool(None, default=True) is True
    assert _parse_bool(None, default=False) is False


def test_parse_bool_rejects_unknown_string():
    from coding_agent_telegram.config import _parse_bool

    assert _parse_bool("maybe") is False
    assert _parse_bool("0") is False


def test_resolve_env_file_path_returns_default_path_when_neither_file_exists(tmp_path, monkeypatch):
    from coding_agent_telegram.config import resolve_env_file_path, DEFAULT_ENV_FILE_NAME

    home = tmp_path / "home"
    monkeypatch.setattr(Path, "home", lambda: home)
    monkeypatch.chdir(tmp_path)
    path = resolve_env_file_path()
    assert path.name == DEFAULT_ENV_FILE_NAME
    assert path.parent == home / ".coding-agent-telegram"


def test_detect_system_locale_prefers_shell_locale_env(monkeypatch):
    monkeypatch.setenv("LANG", "zh_TW.UTF-8")
    monkeypatch.delenv("LC_ALL", raising=False)
    monkeypatch.delenv("LC_MESSAGES", raising=False)
    monkeypatch.delenv("LANGUAGE", raising=False)

    assert detect_system_locale() == "zh-TW"


def test_create_initial_env_file_initializes_app_locale_from_system_language(tmp_path, monkeypatch):
    env_path = tmp_path / ".env_coding_agent_telegram"
    template_path = tmp_path / ".env.example"
    template_path.write_text("APP_LOCALE=en\nWORKSPACE_ROOT=\n", encoding="utf-8")
    monkeypatch.setenv("LANG", "ja_JP.UTF-8")
    monkeypatch.delenv("LC_ALL", raising=False)
    monkeypatch.delenv("LC_MESSAGES", raising=False)
    monkeypatch.delenv("LANGUAGE", raising=False)

    app_locale = create_initial_env_file(env_path, template_path)

    assert app_locale == "ja"
    assert "APP_LOCALE=ja" in env_path.read_text(encoding="utf-8")


def test_create_initial_env_file_fills_in_detected_provider_bin_paths(tmp_path, monkeypatch):
    env_path = tmp_path / ".env_coding_agent_telegram"
    template_path = tmp_path / ".env.example"
    template_path.write_text(
        "APP_LOCALE=en\nCODEX_BIN=codex\nCOPILOT_BIN=copilot\nCLAUDE_BIN=~/.local/bin/claude\n",
        encoding="utf-8",
    )

    detected = {
        "codex": "/opt/homebrew/bin/codex",
        "claude": "/usr/local/bin/claude",
    }
    monkeypatch.setattr(config_module, "detect_installed_bin", lambda bin_name: detected.get(bin_name))

    create_initial_env_file(env_path, template_path)

    written = env_path.read_text(encoding="utf-8")
    assert "CODEX_BIN=/opt/homebrew/bin/codex" in written
    assert "CLAUDE_BIN=/usr/local/bin/claude" in written
    # copilot wasn't detected, so the template value is left untouched.
    assert "COPILOT_BIN=copilot" in written


def test_detect_installed_bin_prefers_path_then_falls_back_to_candidate_dirs(tmp_path, monkeypatch):
    from coding_agent_telegram.config import detect_installed_bin

    monkeypatch.setattr(config_module.shutil, "which", lambda name: None)
    fake_home = tmp_path / "home"
    local_bin = fake_home / ".local" / "bin"
    local_bin.mkdir(parents=True)
    claude_bin = local_bin / "claude"
    claude_bin.write_text("#!/bin/sh\n", encoding="utf-8")
    claude_bin.chmod(0o755)
    monkeypatch.setenv("HOME", str(fake_home))

    assert detect_installed_bin("claude") == str(claude_bin.absolute())
    assert detect_installed_bin("nonexistent-bin-xyz") is None


def test_detect_installed_bin_preserves_symlink_instead_of_resolving_target(tmp_path, monkeypatch):
    from coding_agent_telegram.config import detect_installed_bin

    # Mirrors real installs where a version manager symlinks a stable path
    # (e.g. ~/.local/bin/claude) to a versioned target that changes on upgrade.
    versions_dir = tmp_path / "versions"
    versions_dir.mkdir()
    real_bin = versions_dir / "2.1.214"
    real_bin.write_text("#!/bin/sh\n", encoding="utf-8")
    real_bin.chmod(0o755)

    path_dir = tmp_path / "path_bin"
    path_dir.mkdir()
    symlink_bin = path_dir / "claude"
    symlink_bin.symlink_to(real_bin)

    monkeypatch.setattr(config_module.shutil, "which", lambda name: str(symlink_bin))

    detected = detect_installed_bin("claude")

    assert detected == str(symlink_bin.absolute())
    assert detected != str(real_bin)


# ---------------------------------------------------------------------------
# _parse_allowed_chat_ids: malformed value raises clear ValueError
# ---------------------------------------------------------------------------


def test_load_config_invalid_chat_id_raises_clear_error(monkeypatch, tmp_path):
    _isolate_env(monkeypatch, tmp_path)
    monkeypatch.setenv("WORKSPACE_ROOT", "~/git")
    monkeypatch.setenv("TELEGRAM_BOT_TOKENS", "token-a")
    monkeypatch.setenv("ALLOWED_CHAT_IDS", "123,abc,456")

    with pytest.raises(ValueError, match="Invalid chat ID in ALLOWED_CHAT_IDS"):
        load_config()
