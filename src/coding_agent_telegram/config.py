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
    telegram_bot_token: str
    allowed_chat_ids: set[int]
    codex_bin: str
    copilot_bin: str
    codex_approval_policy: str
    codex_sandbox_mode: str
    max_telegram_message_length: int
    enable_group_chats: bool
    enable_sensitive_diff_filter: bool
    default_agent_provider: str


def _parse_bool(value: str, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _parse_allowed_chat_ids() -> set[int]:
    ids_raw = os.getenv("ALLOWED_CHAT_IDS", "").strip()
    single = os.getenv("ALLOWED_CHAT_ID", "").strip()

    values: list[str] = []
    if single:
        values.append(single)
    if ids_raw:
        values.extend([s.strip() for s in ids_raw.split(",") if s.strip()])

    out: set[int] = set()
    for item in values:
        out.add(int(item))
    return out


def load_config() -> AppConfig:
    load_dotenv()

    workspace_root_raw = os.getenv("WORKSPACE_ROOT")
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    allowed_ids = _parse_allowed_chat_ids()
    provider = os.getenv("DEFAULT_AGENT_PROVIDER", "codex").strip().lower()

    if not workspace_root_raw:
        raise ValueError("Missing required config: WORKSPACE_ROOT")
    if not token:
        raise ValueError("Missing required config: TELEGRAM_BOT_TOKEN")
    if not allowed_ids:
        raise ValueError("Missing required config: ALLOWED_CHAT_ID or ALLOWED_CHAT_IDS")
    if provider not in {"codex", "copilot"}:
        raise ValueError("DEFAULT_AGENT_PROVIDER must be either codex or copilot")

    workspace_root = Path(workspace_root_raw).expanduser().resolve()

    return AppConfig(
        workspace_root=workspace_root,
        state_file=Path(os.getenv("STATE_FILE", "./state.json")),
        state_backup_file=Path(os.getenv("STATE_BACKUP_FILE", "./state.json.bak")),
        log_level=os.getenv("LOG_LEVEL", "INFO"),
        telegram_bot_token=token,
        allowed_chat_ids=allowed_ids,
        codex_bin=os.getenv("CODEX_BIN", "codex"),
        copilot_bin=os.getenv("COPILOT_BIN", "copilot"),
        codex_approval_policy=os.getenv("CODEX_APPROVAL_POLICY", "never"),
        codex_sandbox_mode=os.getenv("CODEX_SANDBOX_MODE", "workspace-write"),
        max_telegram_message_length=int(os.getenv("MAX_TELEGRAM_MESSAGE_LENGTH", "3000")),
        enable_group_chats=_parse_bool(os.getenv("ENABLE_GROUP_CHATS", "false")),
        enable_sensitive_diff_filter=_parse_bool(os.getenv("ENABLE_SENSITIVE_DIFF_FILTER", "true"), default=True),
        default_agent_provider=provider,
    )
