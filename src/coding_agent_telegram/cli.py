from __future__ import annotations

import asyncio
import hashlib
import importlib.resources
import logging
import sys
from pathlib import Path
from typing import Sequence

from coding_agent_telegram.agent_runner import MultiAgentRunner
from coding_agent_telegram.bot import build_application, default_bot_commands, initialize_bot_commands
from coding_agent_telegram.command_router import CommandRouter, RouterDeps
from coding_agent_telegram.config import load_config
from coding_agent_telegram.logging_utils import setup_logging
from coding_agent_telegram.session_store import SessionStore


logger = logging.getLogger(__name__)
BOT_ID_HASH_PREFIX_LENGTH = 12


def _ensure_env_file() -> Path:
    env_path = Path.cwd() / ".env"
    if not env_path.exists():
        template = importlib.resources.files("coding_agent_telegram").joinpath("resources/.env.example").read_text(
            encoding="utf-8"
        )
        env_path.write_text(template, encoding="utf-8")
    return env_path


def _bot_id_from_token(token: str) -> str:
    return f"bot-{hashlib.sha256(token.encode('utf-8')).hexdigest()[:BOT_ID_HASH_PREFIX_LENGTH]}"


async def _run_polling_apps(apps: Sequence) -> None:
    started_apps = []
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
            )
            logger.info(
                "Registered %d Telegram commands for %d allowed chat(s) on @%s",
                len(default_bot_commands(enable_commit_command=enable_commit_command)),
                len(allowed_chat_ids),
                me.username or "unknown",
            )
            await app.start()
            if app.updater is None:
                raise RuntimeError("Telegram updater is not available.")
            await app.updater.start_polling()
            logger.info("Started polling for @%s", me.username or "unknown")
            started_apps.append(app)

        logger.info("Started %d Telegram bot(s).", len(started_apps))
        await asyncio.Event().wait()
    finally:
        for app in reversed(started_apps):
            if app.updater is not None:
                await app.updater.stop()
            await app.stop()
            await app.shutdown()


async def _run(cfg, store: SessionStore, runner: MultiAgentRunner) -> None:
    apps = []
    for token in cfg.telegram_bot_tokens:
        router = CommandRouter(RouterDeps(cfg=cfg, store=store, agent_runner=runner, bot_id=_bot_id_from_token(token)))
        app = build_application(token, router, allowed_chat_ids=cfg.allowed_chat_ids)
        app.bot_data["enable_commit_command"] = cfg.enable_commit_command
        app.bot_data["allowed_chat_ids"] = set(cfg.allowed_chat_ids)
        apps.append(app)

    await _run_polling_apps(apps)


def main() -> None:
    try:
        cfg = load_config()
    except ValueError as exc:
        env_path = _ensure_env_file()
        print(str(exc), file=sys.stderr)
        print("", file=sys.stderr)
        print(f"Created {env_path} if it did not already exist.", file=sys.stderr)
        print("Update these fields in .env:", file=sys.stderr)
        print("- WORKSPACE_ROOT", file=sys.stderr)
        print("- TELEGRAM_BOT_TOKENS", file=sys.stderr)
        print("- ALLOWED_CHAT_IDS", file=sys.stderr)
        print("- LOG_DIR", file=sys.stderr)
        print("", file=sys.stderr)
        print("Then run: coding-agent-telegram", file=sys.stderr)
        raise SystemExit(1)

    log_file = setup_logging(cfg.log_level, cfg.log_dir)
    logger.info("Logging to %s", log_file)

    store = SessionStore(cfg.state_file, cfg.state_backup_file)
    runner = MultiAgentRunner(
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
    )
    try:
        asyncio.run(_run(cfg, store, runner))
    except KeyboardInterrupt:
        logger.info("Stopping Telegram bot polling.")
