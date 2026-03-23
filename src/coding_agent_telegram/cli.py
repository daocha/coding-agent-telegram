from __future__ import annotations

import asyncio
import hashlib
import logging
from typing import Sequence

from coding_agent_telegram.agent_runner import MultiAgentRunner
from coding_agent_telegram.bot import build_application, initialize_bot_commands
from coding_agent_telegram.command_router import CommandRouter, RouterDeps
from coding_agent_telegram.config import load_config
from coding_agent_telegram.logging_utils import setup_logging
from coding_agent_telegram.session_store import SessionStore


logger = logging.getLogger(__name__)


def _bot_id_from_token(token: str) -> str:
    return f"bot-{hashlib.sha256(token.encode('utf-8')).hexdigest()[:12]}"


async def _run_polling_apps(apps: Sequence) -> None:
    started_apps = []
    try:
        for app in apps:
            await app.initialize()
            await initialize_bot_commands(app)
            await app.start()
            if app.updater is None:
                raise RuntimeError("Telegram updater is not available.")
            await app.updater.start_polling()
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
        apps.append(build_application(token, router))

    await _run_polling_apps(apps)


def main() -> None:
    cfg = load_config()
    setup_logging(cfg.log_level)

    store = SessionStore(cfg.state_file, cfg.state_backup_file)
    runner = MultiAgentRunner(
        codex_bin=cfg.codex_bin,
        copilot_bin=cfg.copilot_bin,
        approval_policy=cfg.codex_approval_policy,
        sandbox_mode=cfg.codex_sandbox_mode,
    )
    try:
        asyncio.run(_run(cfg, store, runner))
    except KeyboardInterrupt:
        logger.info("Stopping Telegram bot polling.")
