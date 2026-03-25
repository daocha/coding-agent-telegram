from __future__ import annotations

import logging

from telegram import BotCommand, BotCommandScopeChat, BotCommandScopeDefault
from telegram.ext import Application, CallbackQueryHandler, CommandHandler, MessageHandler, filters as tg_filters

from coding_agent_telegram.command_router import CommandRouter


logger = logging.getLogger(__name__)


def default_bot_commands(*, enable_commit_command: bool) -> list[BotCommand]:
    commands = [
        BotCommand("project", "Set the current project folder"),
        BotCommand("branch", "Create and switch to a git work branch"),
        BotCommand("new", "Create a new session"),
        BotCommand("switch", "List sessions or switch to one"),
        BotCommand("current", "Show the active session"),
        BotCommand("push", "Push the current session branch"),
    ]
    if enable_commit_command:
        commands.insert(5, BotCommand("commit", "Run validated git commit commands"))
    return commands


def allowed_private_chat_filter(allowed_chat_ids: set[int]):
    return tg_filters.Chat(chat_id=sorted(allowed_chat_ids)) & tg_filters.ChatType.PRIVATE


async def initialize_bot_commands(app: Application, *, enable_commit_command: bool, allowed_chat_ids: set[int]) -> None:
    commands = default_bot_commands(enable_commit_command=enable_commit_command)
    await app.bot.delete_my_commands(scope=BotCommandScopeDefault())
    for chat_id in sorted(allowed_chat_ids):
        await app.bot.set_my_commands(commands, scope=BotCommandScopeChat(chat_id))


async def handle_error(update, context) -> None:
    logger.exception("Telegram handler failed.", exc_info=context.error)
    if update is not None and getattr(update, "effective_chat", None) is not None:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="⚠️ Command failed. Check the server log for details.",
        )


def build_application(token: str, router: CommandRouter, *, allowed_chat_ids: set[int]) -> Application:
    app = Application.builder().token(token).build()
    allowed_private = allowed_private_chat_filter(allowed_chat_ids)
    unsupported_media = (
        tg_filters.ANIMATION
        | tg_filters.AUDIO
        | tg_filters.Document.ALL
        | tg_filters.Sticker.ALL
        | tg_filters.VIDEO
        | tg_filters.VIDEO_NOTE
        | tg_filters.VOICE
    )

    app.add_handler(CommandHandler("project", router.handle_project, filters=allowed_private))
    app.add_handler(CommandHandler("branch", router.handle_branch, filters=allowed_private))
    app.add_handler(CommandHandler("new", router.handle_new, filters=allowed_private))
    app.add_handler(CommandHandler("switch", router.handle_switch, filters=allowed_private))
    app.add_handler(CommandHandler("current", router.handle_current, filters=allowed_private))
    app.add_handler(CommandHandler("commit", router.handle_commit, filters=allowed_private))
    app.add_handler(CommandHandler("push", router.handle_push, filters=allowed_private))
    app.add_handler(CallbackQueryHandler(router.handle_trust_project_callback, pattern=r"^trustproject:(yes|no):"))
    app.add_handler(MessageHandler(allowed_private & tg_filters.PHOTO, router.handle_photo))
    app.add_handler(MessageHandler(allowed_private & tg_filters.TEXT & ~tg_filters.COMMAND, router.handle_message))
    app.add_handler(MessageHandler(allowed_private & unsupported_media, router.handle_unsupported_message))
    app.add_error_handler(handle_error)

    return app
