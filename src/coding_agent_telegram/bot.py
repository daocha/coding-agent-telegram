from __future__ import annotations

import logging

from telegram import BotCommand, BotCommandScopeChat, BotCommandScopeDefault
from telegram.request import HTTPXRequest
from telegram.ext import Application, CallbackQueryHandler, CommandHandler, MessageHandler, filters as tg_filters

from coding_agent_telegram.command_router import CommandRouter
from coding_agent_telegram.i18n import DEFAULT_LOCALE, translate
from coding_agent_telegram.session_store import SessionStoreError


logger = logging.getLogger(__name__)
TELEGRAM_CONNECT_TIMEOUT_SECONDS = 10.0
TELEGRAM_READ_TIMEOUT_SECONDS = 30.0
TELEGRAM_WRITE_TIMEOUT_SECONDS = 30.0
TELEGRAM_POOL_TIMEOUT_SECONDS = 10.0
TELEGRAM_REQUEST_CONNECTION_POOL_SIZE = 20
TELEGRAM_GET_UPDATES_CONNECTION_POOL_SIZE = 2


def _describe_message_types(message) -> list[str]:
    types: list[str] = []
    for field_name in (
        "text",
        "photo",
        "voice",
        "audio",
        "document",
        "video",
        "video_note",
        "animation",
        "sticker",
    ):
        value = getattr(message, field_name, None)
        if value:
            types.append(field_name)
    return types


def default_bot_commands(*, enable_commit_command: bool, locale: str = DEFAULT_LOCALE) -> list[BotCommand]:
    commands = [
        BotCommand("provider", translate(locale, "bot.command.provider")),
        BotCommand("project", translate(locale, "bot.command.project")),
        BotCommand("branch", translate(locale, "bot.command.branch")),
        BotCommand("current", translate(locale, "bot.command.current")),
        BotCommand("new", translate(locale, "bot.command.new")),
        BotCommand("switch", translate(locale, "bot.command.switch")),
        BotCommand("compact", translate(locale, "bot.command.compact")),
    ]
    if enable_commit_command:
        commands.append(BotCommand("commit", translate(locale, "bot.command.commit")))
    commands.append(BotCommand("pull", translate(locale, "bot.command.pull")))
    commands.append(BotCommand("push", translate(locale, "bot.command.push")))
    commands.append(BotCommand("abort", translate(locale, "bot.command.abort")))
    return commands


def allowed_private_chat_filter(allowed_chat_ids: set[int]):
    return tg_filters.Chat(chat_id=sorted(allowed_chat_ids)) & tg_filters.ChatType.PRIVATE


async def initialize_bot_commands(
    app: Application,
    *,
    enable_commit_command: bool,
    allowed_chat_ids: set[int],
    locale: str = DEFAULT_LOCALE,
) -> None:
    async def set_commands(commands, scope) -> None:
        await app.bot.set_my_commands(commands, scope=scope)

    await app.bot.delete_my_commands(scope=BotCommandScopeDefault())
    base_commands = default_bot_commands(enable_commit_command=enable_commit_command, locale=locale)
    await set_commands(base_commands, BotCommandScopeDefault())
    for chat_id in sorted(allowed_chat_ids):
        await set_commands(base_commands, BotCommandScopeChat(chat_id))


def build_error_handler(locale: str):
    async def handle_error(update, context) -> None:
        resolved_locale = locale or DEFAULT_LOCALE
        if isinstance(context.error, SessionStoreError):
            logger.warning("Session store lock conflict: %s", context.error)
            if update is not None and getattr(update, "effective_chat", None) is not None:
                await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text=translate(resolved_locale, "bot.error.session_store", error=context.error),
                )
            return
        logger.exception("Telegram handler failed.", exc_info=context.error)
        if update is not None and getattr(update, "effective_chat", None) is not None:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=translate(resolved_locale, "bot.error.command_failed"),
            )

    return handle_error


async def handle_error(update, context) -> None:
    await build_error_handler(DEFAULT_LOCALE)(update, context)

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
    )

    async def log_incoming_private_message(update, _context) -> None:
        message = getattr(update, "message", None)
        chat = getattr(update, "effective_chat", None)
        if message is None or chat is None:
            return
        logger.info(
            "Incoming Telegram message chat=%s message_id=%s types=%s text_preview=%.120r",
            chat.id,
            getattr(message, "message_id", None),
            ",".join(_describe_message_types(message)) or "unknown",
            getattr(message, "text", None) or "",
        )

    app.add_handler(MessageHandler(allowed_private, log_incoming_private_message, block=False), group=-1)
    app.add_handler(CommandHandler("provider", router.handle_provider, filters=allowed_private))
    app.add_handler(CommandHandler("project", router.handle_project, filters=allowed_private))
    app.add_handler(CommandHandler("branch", router.handle_branch, filters=allowed_private))
    app.add_handler(CommandHandler("current", router.handle_current, filters=allowed_private))
    app.add_handler(CommandHandler("new", router.handle_new, filters=allowed_private, block=False))
    app.add_handler(CommandHandler("switch", router.handle_switch, filters=allowed_private))
    app.add_handler(CommandHandler("compact", router.handle_compact, filters=allowed_private))
    app.add_handler(CommandHandler("commit", router.handle_commit, filters=allowed_private))
    app.add_handler(CommandHandler("pull", router.handle_pull, filters=allowed_private))
    app.add_handler(CommandHandler("push", router.handle_push, filters=allowed_private))
    app.add_handler(CommandHandler("abort", router.handle_abort, filters=allowed_private))
    app.add_handler(CallbackQueryHandler(router.handle_provider_callback, pattern=r"^provider:set:(codex|copilot)$", block=False))
    app.add_handler(CallbackQueryHandler(router.handle_queue_batch_callback, pattern=r"^queuebatch:(group|single|cancel)$", block=False))
    app.add_handler(CallbackQueryHandler(router.handle_queue_continue_callback, pattern=r"^queuecontinue:(yes|no)$", block=False))
    app.add_handler(CallbackQueryHandler(router.handle_branch_source_callback, pattern=r"^branchsource:[0-9a-f]{12}$", block=False))
    app.add_handler(CallbackQueryHandler(router.handle_branch_discrepancy_callback, pattern=r"^branchdiscrepancy:(stored|current)$", block=False))
    app.add_handler(CallbackQueryHandler(router.handle_pull_callback, pattern=r"^pull:(confirm|cancel)$"))
    app.add_handler(CallbackQueryHandler(router.handle_push_callback, pattern=r"^push:(confirm|cancel)$"))
    app.add_handler(CallbackQueryHandler(router.handle_trust_project_callback, pattern=r"^trustproject:(yes|no):"))
    app.add_handler(MessageHandler(allowed_private & tg_filters.PHOTO, router.handle_photo, block=False))
    app.add_handler(MessageHandler(allowed_private & tg_filters.AUDIO, router.handle_audio, block=False))
    app.add_handler(MessageHandler(allowed_private & tg_filters.VOICE, router.handle_voice, block=False))
    app.add_handler(MessageHandler(allowed_private & tg_filters.TEXT & ~tg_filters.COMMAND, router.handle_message, block=False))
    app.add_handler(MessageHandler(allowed_private & unsupported_media, router.handle_unsupported_message))
    app.add_error_handler(build_error_handler(router.deps.cfg.locale))

    return app
