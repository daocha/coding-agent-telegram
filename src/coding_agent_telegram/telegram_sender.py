from __future__ import annotations

import html
from typing import Optional

from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes


async def send_text(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str) -> None:
    if update.effective_chat is None:
        return
    await context.bot.send_message(chat_id=update.effective_chat.id, text=text)


async def send_markdown_text(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str) -> None:
    if update.effective_chat is None:
        return
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=text,
        parse_mode=ParseMode.MARKDOWN,
    )


async def send_html_text(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str) -> None:
    if update.effective_chat is None:
        return
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=text,
        parse_mode=ParseMode.HTML,
    )


async def send_code_block(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    header: str,
    code: str,
    *,
    language: Optional[str] = None,
) -> None:
    if update.effective_chat is None:
        return
    escaped_code = html.escape(code)
    await context.bot.send_message(chat_id=update.effective_chat.id, text=header)
    if language:
        text = f"<pre><code class=\"language-{html.escape(language)}\">{escaped_code}</code></pre>"
    else:
        text = f"<pre><code>{escaped_code}</code></pre>"
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=text,
        parse_mode=ParseMode.HTML,
    )
