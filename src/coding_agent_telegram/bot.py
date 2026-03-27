from __future__ import annotations

import logging

from telegram import BotCommand, BotCommandScopeChat, BotCommandScopeDefault
from telegram.request import HTTPXRequest
from telegram.ext import Application, CallbackQueryHandler, CommandHandler, MessageHandler, filters as tg_filters

from coding_agent_telegram.command_router import CommandRouter
from coding_agent_telegram.session_store import SessionStoreError


logger = logging.getLogger(__name__)
TELEGRAM_CONNECT_TIMEOUT_SECONDS = 10.0
TELEGRAM_READ_TIMEOUT_SECONDS = 30.0
TELEGRAM_WRITE_TIMEOUT_SECONDS = 30.0
TELEGRAM_POOL_TIMEOUT_SECONDS = 10.0
TELEGRAM_REQUEST_CONNECTION_POOL_SIZE = 20
TELEGRAM_GET_UPDATES_CONNECTION_POOL_SIZE = 2


def default_bot_commands(*, enable_commit_command: bool) -> list[BotCommand]:
    commands = [
        BotCommand("project", "Set the current project folder"),
        BotCommand("branch", "Create and switch to a git work branch"),
        BotCommand("provider", "Choose the provider for new sessions"),
        BotCommand("new", "Create a new session"),
        BotCommand("switch", "List sessions or switch to one"),
        BotCommand("current", "Show the active session"),
        BotCommand("abort", "Abort the current agent run"),
    ]
    if enable_commit_command:
        commands.append(BotCommand("commit", "Run validated git commit commands"))
    commands.append(BotCommand("push", "Push the current session branch"))
    return commands


def allowed_private_chat_filter(allowed_chat_ids: set[int]):
    return tg_filters.Chat(chat_id=sorted(allowed_chat_ids)) & tg_filters.ChatType.PRIVATE


async def initialize_bot_commands(app: Application, *, enable_commit_command: bool, allowed_chat_ids: set[int]) -> None:
    commands = default_bot_commands(enable_commit_command=enable_commit_command)
    await app.bot.delete_my_commands(scope=BotCommandScopeDefault())
    for chat_id in sorted(allowed_chat_ids):
        await app.bot.set_my_commands(commands, scope=BotCommandScopeChat(chat_id))


async def handle_error(update, context) -> None:
    if isinstance(context.error, SessionStoreError):
        logger.warning("Session store lock conflict: %s", context.error)
        if update is not None and getattr(update, "effective_chat", None) is not None:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=f"⚠️ {context.error}",
            )
        return
    logger.exception("Telegram handler failed.", exc_info=context.error)
    if update is not None and getattr(update, "effective_chat", None) is not None:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="⚠️ Command failed. Check the server log for details.",
        )


def build_application(token: str, router: CommandRouter, *, allowed_chat_ids: set[int]) -> Application:
    request = HTTPXRequest(
        connect_timeout=TELEGRAM_CONNECT_TIMEOUT_SECONDS,
        read_timeout=TELEGRAM_READ_TIMEOUT_SECONDS,
        write_timeout=TELEGRAM_WRITE_TIMEOUT_SECONDS,
        pool_timeout=TELEGRAM_POOL_TIMEOUT_SECONDS,
        connection_pool_size=TELEGRAM_REQUEST_CONNECTION_POOL_SIZE,
    )
    get_updates_request = HTTPXRequest(
        connect_timeout=TELEGRAM_CONNECT_TIMEOUT_SECONDS,
        read_timeout=TELEGRAM_READ_TIMEOUT_SECONDS,
        write_timeout=TELEGRAM_WRITE_TIMEOUT_SECONDS,
        pool_timeout=TELEGRAM_POOL_TIMEOUT_SECONDS,
        connection_pool_size=TELEGRAM_GET_UPDATES_CONNECTION_POOL_SIZE,
    )
    app = Application.builder().token(token).request(request).get_updates_request(get_updates_request).build()
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
    app.add_handler(CommandHandler("provider", router.handle_provider, filters=allowed_private))
    app.add_handler(CommandHandler("new", router.handle_new, filters=allowed_private, block=False))
    app.add_handler(CommandHandler("switch", router.handle_switch, filters=allowed_private))
    app.add_handler(CommandHandler("current", router.handle_current, filters=allowed_private))
    app.add_handler(CommandHandler("abort", router.handle_abort, filters=allowed_private))
    app.add_handler(CommandHandler("commit", router.handle_commit, filters=allowed_private))
    app.add_handler(CommandHandler("push", router.handle_push, filters=allowed_private))
    app.add_handler(CallbackQueryHandler(router.handle_provider_callback, pattern=r"^provider:set:(codex|copilot)$", block=False))
    app.add_handler(CallbackQueryHandler(router.handle_queue_continue_callback, pattern=r"^queuecontinue:(yes|no)$", block=False))
    app.add_handler(CallbackQueryHandler(router.handle_branch_source_callback, pattern=r"^branchsource:(local|origin):", block=False))
    app.add_handler(CallbackQueryHandler(router.handle_branch_discrepancy_callback, pattern=r"^branchdiscrepancy:(stored|current)$", block=False))
    app.add_handler(CallbackQueryHandler(router.handle_push_callback, pattern=r"^push:(confirm|cancel)$"))
    app.add_handler(CallbackQueryHandler(router.handle_trust_project_callback, pattern=r"^trustproject:(yes|no):"))
    app.add_handler(MessageHandler(allowed_private & tg_filters.PHOTO, router.handle_photo, block=False))
    app.add_handler(MessageHandler(allowed_private & tg_filters.TEXT & ~tg_filters.COMMAND, router.handle_message, block=False))
    app.add_handler(MessageHandler(allowed_private & unsupported_media, router.handle_unsupported_message))
    app.add_error_handler(handle_error)

    return app
