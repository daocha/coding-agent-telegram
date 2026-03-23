from __future__ import annotations

from coding_agent_telegram.agent_runner import MultiAgentRunner
from coding_agent_telegram.bot import build_application
from coding_agent_telegram.command_router import CommandRouter, RouterDeps
from coding_agent_telegram.config import load_config
from coding_agent_telegram.logging_utils import setup_logging
from coding_agent_telegram.session_store import SessionStore


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
    router = CommandRouter(RouterDeps(cfg=cfg, store=store, agent_runner=runner))

    app = build_application(cfg.telegram_bot_token, router)
    app.run_polling()
