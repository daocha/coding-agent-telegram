from __future__ import annotations

from telegram import Update
from telegram.ext import ContextTypes


async def send_text(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str) -> None:
    if update.effective_chat is None:
        return
    await context.bot.send_message(chat_id=update.effective_chat.id, text=text)
