from __future__ import annotations

"""Application configuration loading and shared default limits."""

import importlib.resources
import os
import pwd
import re
import locale as system_locale
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from coding_agent_telegram.i18n import DEFAULT_LOCALE, normalize_locale

DEFAULT_SNAPSHOT_TEXT_FILE_MAX_BYTES = 200_000
DEFAULT_MAX_TELEGRAM_MESSAGE_LENGTH = 3_000
DEFAULT_MAX_PHOTO_ATTACHMENT_BYTES = 5 * 1024 * 1024
DEFAULT_INTERNAL_APP_DIR_NAME = ".coding-agent-telegram"
DEFAULT_ENV_FILE_NAME = ".env_coding_agent_telegram"
# 0 = disabled. Set to a positive value to kill runaway agent processes.
DEFAULT_AGENT_HARD_TIMEOUT_SECONDS = 0
DEFAULT_OPENAI_WHISPER_MODEL = "base"
DEFAULT_OPENAI_WHISPER_TIMEOUT_SECONDS = 120


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
    enable_secret_scrub_filter: bool
    enable_openai_whisper_speech_to_text: bool
    openai_whisper_model: str
    openai_whisper_timeout_seconds: int
    default_agent_provider: str
    agent_hard_timeout_seconds: int
    app_internal_root: Path
    locale: str = DEFAULT_LOCALE


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
        try:
            out.add(int(item))
        except ValueError:
            raise ValueError(f"Invalid chat ID in ALLOWED_CHAT_IDS: {item!r}") from None
    return out


def _parse_bot_tokens() -> tuple[str, ...]:
    return tuple(_parse_csv_env("TELEGRAM_BOT_TOKENS"))


def default_app_internal_root() -> Path:
    return resolve_user_home() / DEFAULT_INTERNAL_APP_DIR_NAME


def resolve_user_home() -> Path:
    sudo_user = os.getenv("SUDO_USER", "").strip()
    if sudo_user and sudo_user != "root":
        try:
            return Path(pwd.getpwnam(sudo_user).pw_dir)
        except KeyError:
            pass
    return Path.home()


def detect_system_locale() -> str:
    for env_name in ("LC_ALL", "LC_MESSAGES", "LANGUAGE", "LANG"):
        raw = os.getenv(env_name, "").strip()
        if not raw:
            continue
        for candidate in raw.split(":"):
            normalized = normalize_locale(candidate)
            if normalized:
                return normalized
    try:
        language_code, _encoding = system_locale.getlocale()
    except (ValueError, TypeError):
        language_code = None
    return normalize_locale(language_code)


def _apply_initial_app_locale(template_text: str, app_locale: str) -> str:
    replacement = f"APP_LOCALE={normalize_locale(app_locale)}"
    if re.search(r"(?m)^APP_LOCALE=.*$", template_text):
        return re.sub(r"(?m)^APP_LOCALE=.*$", replacement, template_text, count=1)
    return f"{replacement}\n{template_text}"


def create_initial_env_file(env_path: Path, template_path: Optional[Path] = None) -> str:
    if template_path is None:
        template_text = importlib.resources.files("coding_agent_telegram").joinpath("resources/.env.example").read_text(
            encoding="utf-8"
        )
    else:
        template_text = template_path.read_text(encoding="utf-8")
    app_locale = detect_system_locale()
    env_path.parent.mkdir(parents=True, exist_ok=True)
    env_path.write_text(_apply_initial_app_locale(template_text, app_locale), encoding="utf-8")
    return app_locale


def resolve_env_file_path(env_file: Optional[Path] = None) -> Path:
    if env_file is not None:
        return env_file

    env_file_override = os.getenv("CODING_AGENT_TELEGRAM_ENV_FILE", "").strip()
    if env_file_override:
        return Path(env_file_override).expanduser()

    home_default_env = default_app_internal_root() / DEFAULT_ENV_FILE_NAME
    cwd = Path.cwd()
    default_env = cwd / DEFAULT_ENV_FILE_NAME
    if home_default_env.exists():
        return home_default_env
    if default_env.exists():
        return default_env
    return home_default_env


def resolve_app_internal_root(workspace_root: Path) -> Path:
    home_root = default_app_internal_root()
    workspace_root_candidate = workspace_root / DEFAULT_INTERNAL_APP_DIR_NAME
    if home_root.exists():
        return home_root
    if workspace_root_candidate.exists():
        return workspace_root_candidate
    return home_root


def resolve_default_state_file_path(file_name: str) -> Path:
    home_path = default_app_internal_root() / file_name
    cwd_path = Path.cwd() / file_name
    if home_path.exists():
        return home_path
    if cwd_path.exists():
        return cwd_path
    return home_path


def default_log_dir_path() -> Path:
    return default_app_internal_root() / "logs"


def load_config(env_file: Optional[Path] = None) -> AppConfig:
    """Load application configuration from the environment and the resolved env file."""
    load_dotenv(dotenv_path=resolve_env_file_path(env_file), override=True)

    workspace_root_raw = os.getenv("WORKSPACE_ROOT")
    tokens = _parse_bot_tokens()
    allowed_ids = _parse_allowed_chat_ids()
    provider = os.getenv("DEFAULT_AGENT_PROVIDER", "codex").strip().lower()
    locale = normalize_locale(os.getenv("APP_LOCALE", DEFAULT_LOCALE).strip() or DEFAULT_LOCALE)

    if not workspace_root_raw:
        raise ValueError("Missing required config: WORKSPACE_ROOT")
    if not tokens:
        raise ValueError("Missing required config: TELEGRAM_BOT_TOKENS")
    if not allowed_ids:
        raise ValueError("Missing required config: ALLOWED_CHAT_IDS")
    if provider not in {"codex", "copilot"}:
        raise ValueError("DEFAULT_AGENT_PROVIDER must be either codex or copilot")
    workspace_root = Path(workspace_root_raw).expanduser().resolve()
    app_internal_root = resolve_app_internal_root(workspace_root)

    return AppConfig(
        workspace_root=workspace_root,
        state_file=resolve_default_state_file_path("state.json"),
        state_backup_file=resolve_default_state_file_path("state.json.bak"),
        log_level=os.getenv("LOG_LEVEL", "INFO"),
        log_dir=default_log_dir_path(),
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
        snapshot_text_file_max_bytes=int(
            os.getenv("SNAPSHOT_TEXT_FILE_MAX_BYTES", str(DEFAULT_SNAPSHOT_TEXT_FILE_MAX_BYTES))
        ),
        max_telegram_message_length=int(
            os.getenv("MAX_TELEGRAM_MESSAGE_LENGTH", str(DEFAULT_MAX_TELEGRAM_MESSAGE_LENGTH))
        ),
        enable_sensitive_diff_filter=_parse_bool(os.getenv("ENABLE_SENSITIVE_DIFF_FILTER", "true"), default=True),
        enable_secret_scrub_filter=_parse_bool(os.getenv("ENABLE_SECRET_SCRUB_FILTER", "true"), default=True),
        enable_openai_whisper_speech_to_text=_parse_bool(
            os.getenv("ENABLE_OPENAI_WHISPER_SPEECH_TO_TEXT", "false")
        ),
        openai_whisper_model=os.getenv("OPENAI_WHISPER_MODEL", DEFAULT_OPENAI_WHISPER_MODEL).strip()
        or DEFAULT_OPENAI_WHISPER_MODEL,
        openai_whisper_timeout_seconds=max(
            1,
            int(os.getenv("OPENAI_WHISPER_TIMEOUT_SECONDS", str(DEFAULT_OPENAI_WHISPER_TIMEOUT_SECONDS))),
        ),
        default_agent_provider=provider,
        agent_hard_timeout_seconds=int(
            os.getenv("AGENT_HARD_TIMEOUT_SECONDS", str(DEFAULT_AGENT_HARD_TIMEOUT_SECONDS))
        ),
        app_internal_root=app_internal_root,
        locale=locale,
    )
