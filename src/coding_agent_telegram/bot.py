from __future__ import annotations

import logging

from telegram import BotCommand
from telegram.ext import Application, CommandHandler, MessageHandler, filters as tg_filters

from coding_agent_telegram.command_router import CommandRouter


logger = logging.getLogger(__name__)


def default_bot_commands() -> list[BotCommand]:
    return [
        BotCommand("project", "Set the current project folder"),
        BotCommand("branch", "Create and switch to a git work branch"),
        BotCommand("new", "Create a new session"),
        BotCommand("switch", "List sessions or switch to one"),
        BotCommand("current", "Show the active session"),
        BotCommand("commit", "Run validated git commit commands"),
        BotCommand("push", "Push the current session branch"),
    ]


async def initialize_bot_commands(app: Application) -> None:
    await app.bot.set_my_commands(default_bot_commands())


async def handle_error(update, context) -> None:
    logger.exception("Telegram handler failed.", exc_info=context.error)
    if update is not None and getattr(update, "effective_chat", None) is not None:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="⚠️ Command failed. Check the server log for details.",
        )


def build_application(token: str, router: CommandRouter) -> Application:
    app = Application.builder().token(token).build()
    unsupported_media = (
        tg_filters.ANIMATION
        | tg_filters.AUDIO
        | tg_filters.Document.ALL
        | tg_filters.Sticker.ALL
        | tg_filters.VIDEO
        | tg_filters.VIDEO_NOTE
        | tg_filters.VOICE
    )

    app.add_handler(CommandHandler("project", router.handle_project))
    app.add_handler(CommandHandler("branch", router.handle_branch))
    app.add_handler(CommandHandler("new", router.handle_new))
    app.add_handler(CommandHandler("switch", router.handle_switch))
    app.add_handler(CommandHandler("current", router.handle_current))
    app.add_handler(CommandHandler("commit", router.handle_commit))
    app.add_handler(CommandHandler("push", router.handle_push))
    app.add_handler(MessageHandler(tg_filters.PHOTO, router.handle_photo))
    app.add_handler(MessageHandler(tg_filters.TEXT & ~tg_filters.COMMAND, router.handle_message))
    app.add_handler(MessageHandler(unsupported_media, router.handle_unsupported_message))
    app.add_error_handler(handle_error)

    return app
