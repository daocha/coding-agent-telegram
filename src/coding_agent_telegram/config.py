from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


@dataclass(frozen=True)
class AppConfig:
    workspace_root: Path
    state_file: Path
    state_backup_file: Path
    log_level: str
    log_dir: Path
    telegram_bot_tokens: tuple[str, ...]
    allowed_chat_ids: set[int]
    codex_bin: str
    copilot_bin: str
    codex_model: str
    copilot_model: str
    copilot_autopilot: bool
    copilot_no_ask_user: bool
    copilot_allow_all: bool
    copilot_allow_all_tools: bool
    copilot_allow_tools: tuple[str, ...]
    copilot_deny_tools: tuple[str, ...]
    copilot_available_tools: tuple[str, ...]
    codex_approval_policy: str
    codex_sandbox_mode: str
    codex_skip_git_repo_check: bool
    enable_commit_command: bool
    snapshot_text_file_max_bytes: int
    max_telegram_message_length: int
    enable_sensitive_diff_filter: bool
    default_agent_provider: str


def _parse_bool(value: str, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _parse_csv_env(name: str) -> list[str]:
    raw = os.getenv(name, "").strip()
    if not raw:
        return []
    return [item.strip() for item in raw.split(",") if item.strip()]


def _parse_allowed_chat_ids() -> set[int]:
    values = _parse_csv_env("ALLOWED_CHAT_IDS")

    out: set[int] = set()
    for item in values:
        out.add(int(item))
    return out


def _parse_bot_tokens() -> tuple[str, ...]:
    return tuple(_parse_csv_env("TELEGRAM_BOT_TOKENS"))


def load_config() -> AppConfig:
    load_dotenv()

    workspace_root_raw = os.getenv("WORKSPACE_ROOT")
    tokens = _parse_bot_tokens()
    allowed_ids = _parse_allowed_chat_ids()
    provider = os.getenv("DEFAULT_AGENT_PROVIDER", "codex").strip().lower()

    if not workspace_root_raw:
        raise ValueError("Missing required config: WORKSPACE_ROOT")
    if not tokens:
        raise ValueError("Missing required config: TELEGRAM_BOT_TOKENS")
    if not allowed_ids:
        raise ValueError("Missing required config: ALLOWED_CHAT_IDS")
    if provider not in {"codex", "copilot"}:
        raise ValueError("DEFAULT_AGENT_PROVIDER must be either codex or copilot")

    workspace_root = Path(workspace_root_raw).expanduser().resolve()

    return AppConfig(
        workspace_root=workspace_root,
        state_file=Path(os.getenv("STATE_FILE", "./state.json")),
        state_backup_file=Path(os.getenv("STATE_BACKUP_FILE", "./state.json.bak")),
        log_level=os.getenv("LOG_LEVEL", "INFO"),
        log_dir=Path(os.getenv("LOG_DIR", "./logs")),
        telegram_bot_tokens=tokens,
        allowed_chat_ids=allowed_ids,
        codex_bin=os.getenv("CODEX_BIN", "codex"),
        copilot_bin=os.getenv("COPILOT_BIN", "copilot"),
        codex_model=os.getenv("CODEX_MODEL", "").strip(),
        copilot_model=os.getenv("COPILOT_MODEL", "").strip(),
        copilot_autopilot=_parse_bool(os.getenv("COPILOT_AUTOPILOT", "true"), default=True),
        copilot_no_ask_user=_parse_bool(os.getenv("COPILOT_NO_ASK_USER", "true"), default=True),
        copilot_allow_all=_parse_bool(os.getenv("COPILOT_ALLOW_ALL", "true"), default=True),
        copilot_allow_all_tools=_parse_bool(os.getenv("COPILOT_ALLOW_ALL_TOOLS", "false")),
        copilot_allow_tools=tuple(_parse_csv_env("COPILOT_ALLOW_TOOLS")),
        copilot_deny_tools=tuple(_parse_csv_env("COPILOT_DENY_TOOLS")),
        copilot_available_tools=tuple(_parse_csv_env("COPILOT_AVAILABLE_TOOLS")),
        codex_approval_policy=os.getenv("CODEX_APPROVAL_POLICY", "never"),
        codex_sandbox_mode=os.getenv("CODEX_SANDBOX_MODE", "workspace-write"),
        codex_skip_git_repo_check=_parse_bool(os.getenv("CODEX_SKIP_GIT_REPO_CHECK", "false")),
        enable_commit_command=_parse_bool(os.getenv("ENABLE_COMMIT_COMMAND", "false")),
        snapshot_text_file_max_bytes=int(os.getenv("SNAPSHOT_TEXT_FILE_MAX_BYTES", "200000")),
        max_telegram_message_length=int(os.getenv("MAX_TELEGRAM_MESSAGE_LENGTH", "3000")),
        enable_sensitive_diff_filter=_parse_bool(os.getenv("ENABLE_SENSITIVE_DIFF_FILTER", "true"), default=True),
        default_agent_provider=provider,
    )
