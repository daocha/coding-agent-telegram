from __future__ import annotations

from telegram.ext import Application, CommandHandler, MessageHandler, filters as tg_filters

from coding_agent_telegram.command_router import CommandRouter


def build_application(token: str, router: CommandRouter) -> Application:
    app = Application.builder().token(token).build()

    app.add_handler(CommandHandler("project", router.handle_project))
    app.add_handler(CommandHandler("new", router.handle_new))
    app.add_handler(CommandHandler("switch", router.handle_switch))
    app.add_handler(CommandHandler("current", router.handle_current))
    app.add_handler(MessageHandler(tg_filters.TEXT & ~tg_filters.COMMAND, router.handle_message))

    return app
