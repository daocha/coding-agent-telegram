from __future__ import annotations

import asyncio
import logging
import secrets
from dataclasses import dataclass, field

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from coding_agent_telegram.i18n import locale_from_update, translate
from coding_agent_telegram.telegram_sender import send_text

logger = logging.getLogger(__name__)


@dataclass
class PendingQuestion:
    chat_id: int
    payload: dict
    future: asyncio.Future
    selected: list[set[int]]
    session_id: str | None = None
    messages: list[int] = field(default_factory=list)


class ClaudeQuestions:
    """Question state belongs to a live Claude request, never a chat queue gate."""

    def __init__(self):
        self.pending: dict[str, PendingQuestion] = {}

    async def ask(self, update, context, payload: dict, *, session_id: str | None = None) -> dict:
        questions = payload.get("questions") if isinstance(payload, dict) else None
        if not isinstance(questions, list) or not 1 <= len(questions) <= 4:
            raise ValueError("Invalid Claude question list")
        for question in questions:
            if not isinstance(question, dict) or not isinstance(question.get("question"), str):
                raise ValueError("Invalid Claude question")
            options = question.get("options")
            if not isinstance(options, list) or not 2 <= len(options) <= 4:
                raise ValueError("Invalid Claude options")
            if any(not isinstance(option, dict) or not isinstance(option.get("label"), str) for option in options):
                raise ValueError("Invalid Claude option label")
        token = secrets.token_hex(6)
        entry = PendingQuestion(update.effective_chat.id, payload, asyncio.get_running_loop().create_future(),
                                [set() for _ in questions], session_id=session_id)
        self.pending[token] = entry
        try:
            await send_text(update, context, translate(locale_from_update(update), "claude.questions_hint"))
            for index, question in enumerate(questions):
                body = [question["question"]]
                for number, option in enumerate(question["options"], 1):
                    body.append(f"{number}. {option['label']}\n{option.get('description', '')}")
                # send_text handles long/localized content safely. Buttons carry
                # indexes only; full labels and descriptions remain in the prose.
                await send_text(update, context, "\n\n".join(body))
                message = await context.bot.send_message(
                    chat_id=entry.chat_id, text=f"{index + 1}/{len(questions)}",
                    reply_markup=self.keyboard(token, entry, index, locale_from_update(update)))
                if message is not None:
                    entry.messages.append(message.message_id)
            return await entry.future
        finally:
            self.pending.pop(token, None)
            if not entry.future.done():
                entry.future.cancel()
            if hasattr(context.bot, "edit_message_reply_markup"):
                for message_id in entry.messages:
                    try:
                        await context.bot.edit_message_reply_markup(
                            chat_id=entry.chat_id, message_id=message_id, reply_markup=None)
                    except Exception:
                        logger.debug("Could not remove expired Claude question buttons.", exc_info=True)

    def keyboard(self, token: str, entry: PendingQuestion, index: int, locale: str):
        rows = []
        for option_index, option in enumerate(entry.payload["questions"][index]["options"]):
            selected = option_index in entry.selected[index]
            label = ("☑ " if selected else "☐ ") + option["label"][:60]
            rows.append([InlineKeyboardButton(label, callback_data=f"claudeq:{token}:{index}:{option_index}")])
        rows.append([InlineKeyboardButton(translate(locale, "claude.questions_submit"),
                                          callback_data=f"claudeq:{token}:submit"),
                     InlineKeyboardButton(translate(locale, "git.cancel_button"),
                                          callback_data=f"claudeq:{token}:cancel")])
        return InlineKeyboardMarkup(rows)

    def redirect(self, chat_id: int, text: str, *, session_id: str | None = None) -> bool:
        entries = [entry for entry in self.pending.values()
                   if entry.chat_id == chat_id and not entry.future.done()
                   and (entry.session_id is None or entry.session_id == session_id)]
        if not entries:
            return False
        # Do not guess whether free text is an answer or a new question. Return it
        # verbatim as feedback, letting Claude respond without waiting for clicks.
        for entry in entries:
            entry.future.set_result({"behavior": "deny", "message":
                "The user replied in text instead of selecting options. Respond to their message now; "
                "do not keep waiting for these selections. Their message is:\n" + text})
        return True

    async def handle_callback(self, update, context):
        query = update.callback_query
        if query is None or not query.data:
            return
        parts = (query.data or "").split(":")
        entry = self.pending.get(parts[1]) if len(parts) >= 3 else None
        if entry is None or entry.future.done() or entry.chat_id != update.effective_chat.id:
            await query.answer()
            return
        action = parts[2]
        if action == "submit":
            if not all(entry.selected):
                await query.answer(translate(locale_from_update(update), "claude.questions_incomplete"))
                return
            answers = {}
            for question, selected in zip(entry.payload["questions"], entry.selected):
                answers[question["question"]] = ", ".join(question["options"][i]["label"] for i in sorted(selected))
            entry.future.set_result({"behavior": "allow", "updatedInput": {**entry.payload, "answers": answers}})
        elif action == "cancel":
            entry.future.set_result({"behavior": "deny", "message":
                "The user dismissed these questions. Do not choose options on their behalf; acknowledge and wait for instructions."})
        elif len(parts) == 4:
            try:
                index, option_index = int(action), int(parts[3])
                if not 0 <= index < len(entry.selected):
                    raise ValueError
                question = entry.payload["questions"][index]
                if not 0 <= option_index < len(question["options"]):
                    raise ValueError
            except (ValueError, IndexError):
                await query.answer()
                return
            selected = entry.selected[index]
            if option_index in selected:
                selected.remove(option_index)
            else:
                if not question.get("multiSelect"):
                    selected.clear()
                selected.add(option_index)
            await query.answer()
            await query.edit_message_reply_markup(
                reply_markup=self.keyboard(parts[1], entry, index, locale_from_update(update)))
            return
        await query.answer()
