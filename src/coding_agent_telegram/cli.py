from __future__ import annotations

import asyncio
import hashlib
import logging
import os
import sys
from pathlib import Path
from typing import Optional, Sequence

from coding_agent_telegram.agent_runner import MultiAgentRunner
from coding_agent_telegram.bot import build_application, default_bot_commands, initialize_bot_commands
from coding_agent_telegram.claude_health import check_claude_auth
from coding_agent_telegram.command_router import CommandRouter, RouterDeps
from coding_agent_telegram.config import (
    AppConfig,
    create_initial_env_file,
    load_config,
    read_env_value,
    remove_env_value,
    resolve_env_file_path,
    upsert_env_value,
)
from coding_agent_telegram.i18n import translate
from coding_agent_telegram.logging_utils import setup_logging
from coding_agent_telegram.polling_heartbeat import touch_heartbeat
from coding_agent_telegram.session_store import SessionStore
from coding_agent_telegram.stt_setup import ensure_stt_runtime_or_exit, offer_stt_install_for_new_env
from coding_agent_telegram.usage_status import configure_persistence


logger = logging.getLogger(__name__)
BOT_ID_HASH_PREFIX_LENGTH = 12
POLLING_HEARTBEAT_INTERVAL_SECONDS = 60.0


def _ensure_env_file() -> tuple[Path, str | None]:
    env_path = resolve_env_file_path()
    env_path.parent.mkdir(parents=True, exist_ok=True)
    if not env_path.exists():
        return env_path, create_initial_env_file(env_path)
    return env_path, None


def _bot_id_from_token(token: str) -> str:
    return f"bot-{hashlib.sha256(token.encode('utf-8')).hexdigest()[:BOT_ID_HASH_PREFIX_LENGTH]}"


def _env_locale_for_messages(env_path: Path) -> str:
    try:
        for raw_line in env_path.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            if key.strip() == "APP_LOCALE":
                return value.strip() or "en"
    except OSError:
        pass
    return "en"


async def _poll_heartbeat_loop(app, bot_label: str, heartbeat_file: Path) -> None:
    """Periodically pings Telegram and touches the heartbeat file on success.

    python-telegram-bot's own get_updates loop gives no external hook to observe
    success/failure, so this issues its own lightweight, independent call on the
    same event loop -- if the loop or the HTTP stack is wedged, this stops
    touching the file too, which is exactly the staleness supervise.sh watches
    for (it owns the decision to restart; this only reports liveness).
    """
    touch_heartbeat(heartbeat_file)
    while True:
        await asyncio.sleep(POLLING_HEARTBEAT_INTERVAL_SECONDS)
        try:
            await app.bot.get_me()
        except Exception:
            logger.warning("Heartbeat check failed for @%s; will retry.", bot_label, exc_info=True)
            continue
        touch_heartbeat(heartbeat_file)


async def _run_polling_apps(apps: Sequence, heartbeat_file: Path) -> None:
    started_apps = []
    heartbeat_tasks = []
    try:
        for app in apps:
            await app.initialize()
            me = await app.bot.get_me()
            logger.info(
                "Connected Telegram bot: @%s (id=%s, name=%s)",
                me.username or "unknown",
                me.id,
                me.first_name,
            )
            enable_commit_command = bool(app.bot_data.get("enable_commit_command", False))
            allowed_chat_ids = set(app.bot_data.get("allowed_chat_ids", set()))
            await initialize_bot_commands(
                app,
                enable_commit_command=enable_commit_command,
                allowed_chat_ids=allowed_chat_ids,
                locale=app.bot_data.get("locale", "en"),
            )
            logger.info(
                "Registered %d Telegram commands for %d allowed chat(s) on @%s",
                len(default_bot_commands(enable_commit_command=enable_commit_command, locale=app.bot_data.get("locale", "en"))),
                len(allowed_chat_ids),
                me.username or "unknown",
            )
            await app.start()
            if app.updater is None:
                raise RuntimeError("Telegram updater is not available.")
            await app.updater.start_polling()
            logger.info("Started polling for @%s", me.username or "unknown")
            started_apps.append(app)
            heartbeat_tasks.append(
                asyncio.create_task(_poll_heartbeat_loop(app, me.username or "unknown", heartbeat_file))
            )

        logger.info("Started %d Telegram bot(s).", len(started_apps))
        await asyncio.Event().wait()
    finally:
        for task in heartbeat_tasks:
            task.cancel()
        for app in reversed(started_apps):
            if app.updater is not None:
                await app.updater.stop()
            await app.stop()
            await app.shutdown()


async def _run(cfg, store: SessionStore, runner: MultiAgentRunner) -> None:
    apps = []
    heartbeat_file = cfg.app_internal_root / "polling.heartbeat"
    for token in cfg.telegram_bot_tokens:
        router = CommandRouter(RouterDeps(cfg=cfg, store=store, agent_runner=runner, bot_id=_bot_id_from_token(token)))
        app = build_application(token, router, allowed_chat_ids=cfg.allowed_chat_ids)
        app.bot_data["enable_commit_command"] = cfg.enable_commit_command
        app.bot_data["allowed_chat_ids"] = set(cfg.allowed_chat_ids)
        app.bot_data["locale"] = cfg.locale
        app.bot_data["max_telegram_message_length"] = cfg.max_telegram_message_length
        apps.append(app)

    await _run_polling_apps(apps, heartbeat_file)


def _build_runner(cfg: AppConfig, *, claude_model: Optional[str] = None) -> MultiAgentRunner:
    return MultiAgentRunner(
        codex_bin=cfg.codex_bin,
        copilot_bin=cfg.copilot_bin,
        approval_policy=cfg.codex_approval_policy,
        sandbox_mode=cfg.codex_sandbox_mode,
        codex_model=cfg.codex_model,
        copilot_model=cfg.copilot_model,
        copilot_autopilot=cfg.copilot_autopilot,
        copilot_no_ask_user=cfg.copilot_no_ask_user,
        copilot_allow_all=cfg.copilot_allow_all,
        copilot_allow_all_tools=cfg.copilot_allow_all_tools,
        copilot_allow_tools=cfg.copilot_allow_tools,
        copilot_deny_tools=cfg.copilot_deny_tools,
        copilot_available_tools=cfg.copilot_available_tools,
        claude_bin=cfg.claude_bin,
        claude_model=claude_model if claude_model is not None else cfg.claude_model,
        claude_permission_mode=cfg.claude_permission_mode,
        claude_allowed_tools=cfg.claude_allowed_tools,
        claude_disallowed_tools=cfg.claude_disallowed_tools,
        hard_timeout_seconds=cfg.agent_hard_timeout_seconds,
    )


CLAUDE_AUTH_SUBCOMMAND = "claude-auth"
# Deliberately not cfg.claude_model: an operator may have that set to a
# premium/expensive alias (e.g. "fable" or "opus"), and this check only needs
# a trivial reply -- Haiku is the cheapest current tier and is enough to prove
# auth works end-to-end.
CLAUDE_AUTH_VERIFY_MODEL = "haiku"


def _prompt_yes_no(prompt: str, *, default: bool = True) -> bool:
    suffix = "[Y/n]" if default else "[y/N]"
    try:
        answer = input(f"{prompt} {suffix} ").strip().lower()
    except EOFError:
        return default
    if not answer:
        return default
    return answer in {"y", "yes"}


def _run_claude_auth_subcommand(argv: list[str]) -> None:
    """Handles `coding-agent-telegram claude-auth <token>` (and the equivalent
    `./startup.sh claude-auth <token>`): saves a `claude setup-token` result as
    CLAUDE_CODE_OAUTH_TOKEN, optionally verifying it immediately so the operator
    gets a clear pass/fail instead of a blind restart-and-hope. Verification is
    opt-in and clearly costed up front since it's a real, billable API call
    (see check_claude_auth's docstring for why a cheap `claude auth status`-style
    check isn't a substitute).
    """
    if len(argv) != 1 or not argv[0].strip():
        print(f"Usage: coding-agent-telegram {CLAUDE_AUTH_SUBCOMMAND} <token>", file=sys.stderr)
        print("Get <token> by running: claude setup-token", file=sys.stderr)
        print(
            "Approve access in the browser it opens, then copy the token it prints in the TERMINAL",
            file=sys.stderr,
        )
        print(
            "afterwards (starts with sk-ant-oat01-) -- not anything shown on the browser page itself.",
            file=sys.stderr,
        )
        raise SystemExit(2)
    token = argv[0].strip()

    if not token.startswith("sk-ant-"):
        print(
            "Warning: that doesn't look like a Claude token (expected it to start with sk-ant-oat01-).",
            file=sys.stderr,
        )
        print(
            "Make sure you copied the token `claude setup-token` printed in the TERMINAL after you",
            file=sys.stderr,
        )
        print(
            "approved access in the browser -- not anything shown on the browser page itself.",
            file=sys.stderr,
        )
        print("Saving and verifying it anyway in case this is a valid but unexpected format...", file=sys.stderr)

    env_path, _ = _ensure_env_file()
    previous_token = read_env_value(env_path, "CLAUDE_CODE_OAUTH_TOKEN")

    should_verify = _prompt_yes_no(
        f"Verify this token now? This sends one small request to Claude (using '{CLAUDE_AUTH_VERIFY_MODEL}', "
        "the cheapest model, regardless of your configured default) to confirm it actually authenticates -- "
        "a small amount of real API usage, typically a fraction of a cent.",
        default=True,
    )

    upsert_env_value(
        env_path,
        "CLAUDE_CODE_OAUTH_TOKEN",
        token,
        comments=[
            "# Long-lived token from `claude setup-token`, used instead of the interactive",
            "# OAuth session for headless Claude session creation.",
        ],
    )
    print(f"Saved CLAUDE_CODE_OAUTH_TOKEN to {env_path}.")

    if not should_verify:
        print("Skipped verification. Restart the bot for the token to take effect.")
        return

    try:
        cfg = load_config(env_path)
    except ValueError as exc:
        print(f"Saved, but could not load the config to verify it: {exc}", file=sys.stderr)
        print("Restart the bot for the token to take effect.")
        return

    os.environ["CLAUDE_CODE_OAUTH_TOKEN"] = token
    print(f"Verifying with {CLAUDE_AUTH_VERIFY_MODEL}...")
    verify_runner = _build_runner(cfg, claude_model=CLAUDE_AUTH_VERIFY_MODEL)
    result = check_claude_auth(verify_runner, cfg.app_internal_root / "claude_health_check")
    if result.healthy:
        print("Verified: Claude can authenticate headless sessions now.")
        print("Restart the bot for the running process to pick it up.")
        return

    print(f"Verification failed: {result.detail}", file=sys.stderr)
    if previous_token is not None:
        upsert_env_value(env_path, "CLAUDE_CODE_OAUTH_TOKEN", previous_token)
        print("Rolled back CLAUDE_CODE_OAUTH_TOKEN to its previous value.", file=sys.stderr)
    else:
        remove_env_value(env_path, "CLAUDE_CODE_OAUTH_TOKEN")
        print("Removed the unverified token (no CLAUDE_CODE_OAUTH_TOKEN was set before).", file=sys.stderr)
    print("Double-check the token, or see the README's Claude Auth Troubleshooting section.", file=sys.stderr)
    raise SystemExit(1)


def main() -> None:
    argv = sys.argv[1:]
    if argv and argv[0] == CLAUDE_AUTH_SUBCOMMAND:
        _run_claude_auth_subcommand(argv[1:])
        return

    env_path, created_locale = _ensure_env_file()
    if created_locale is not None:
        print(
            translate(
                created_locale,
                "bootstrap.env_created_locale_line",
                env_path=env_path,
                app_locale=created_locale,
            ),
            file=sys.stderr,
        )
        print(
            translate(
                created_locale,
                "bootstrap.env_created_change_line",
                env_path=env_path,
            ),
            file=sys.stderr,
        )
        offer_stt_install_for_new_env(
            env_file=str(env_path),
            python_bin=sys.executable,
            installer_label="coding-agent-telegram-stt-install",
        )
    try:
        cfg = load_config(env_path)
    except ValueError as exc:
        locale = created_locale or _env_locale_for_messages(env_path)
        print(str(exc), file=sys.stderr)
        print("", file=sys.stderr)
        print(translate(locale, "cli.created_env_if_missing", env_path=env_path), file=sys.stderr)
        print(translate(locale, "cli.update_fields_in_env", env_path=env_path), file=sys.stderr)
        print("- WORKSPACE_ROOT", file=sys.stderr)
        print("- TELEGRAM_BOT_TOKENS", file=sys.stderr)
        print("- ALLOWED_CHAT_IDS", file=sys.stderr)
        print("", file=sys.stderr)
        print(translate(locale, "cli.then_run"), file=sys.stderr)
        raise SystemExit(1)

    log_file = setup_logging(cfg.log_level, cfg.log_dir)
    logger.info("Logging to %s", log_file)
    try:
        ensure_stt_runtime_or_exit(cfg.enable_openai_whisper_speech_to_text)
    except SystemExit as exc:
        logger.error("%s", exc)
        raise

    store = SessionStore(cfg.state_file, cfg.state_backup_file)
    # Its own small file, deliberately separate from state.json -- see the
    # module-level comment in usage_status.py for why (write frequency and
    # lock-contention mismatch with session bookkeeping).
    configure_persistence(cfg.state_file.parent / "claude_rate_limit.json")
    cleared_pending_actions = store.clear_all_pending_actions()
    if cleared_pending_actions:
        logger.warning(
            "Cleared %d stale pending_action entr%s left over from a previous run "
            "(likely an unclean shutdown mid-message); affected chats can send messages again.",
            cleared_pending_actions,
            "y" if cleared_pending_actions == 1 else "ies",
        )
    runner = _build_runner(cfg)
    try:
        asyncio.run(_run(cfg, store, runner))
    except KeyboardInterrupt:
        logger.info("Stopping Telegram bot polling.")
