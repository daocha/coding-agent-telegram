from __future__ import annotations

from telegram import BotCommand
from telegram.ext import Application, CommandHandler, MessageHandler, filters as tg_filters

from coding_agent_telegram.command_router import CommandRouter


def default_bot_commands() -> list[BotCommand]:
    return [
        BotCommand("project", "Set the current project folder"),
        BotCommand("new", "Create a new session"),
        BotCommand("switch", "List sessions or switch to one"),
        BotCommand("current", "Show the active session"),
    ]


async def initialize_bot_commands(app: Application) -> None:
    await app.bot.set_my_commands(default_bot_commands())


def build_application(token: str, router: CommandRouter) -> Application:
    app = Application.builder().token(token).build()

    app.add_handler(CommandHandler("project", router.handle_project))
    app.add_handler(CommandHandler("new", router.handle_new))
    app.add_handler(CommandHandler("switch", router.handle_switch))
    app.add_handler(CommandHandler("current", router.handle_current))
    app.add_handler(MessageHandler(tg_filters.TEXT & ~tg_filters.COMMAND, router.handle_message))

    return app
