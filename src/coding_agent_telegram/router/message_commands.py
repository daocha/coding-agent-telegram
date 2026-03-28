from __future__ import annotations

from telegram import Update
from telegram.ext import ContextTypes

from coding_agent_telegram.session_runtime import PhotoAttachmentError
from coding_agent_telegram.telegram_sender import send_text

from .base import require_allowed_chat


class MessageCommandMixin:
    @require_allowed_chat()
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if update.message is None or not update.message.text:
            return
        user_message = update.message.text
        chat_id = update.effective_chat.id
        if self._is_project_busy(chat_id) or self._has_pending_queue_decision(chat_id):
            _queue_file, question_number = self._enqueue_chat_message(chat_id, user_message)
            await send_text(
                update,
                context,
                self._t(update, "message.question_queued", question_number=question_number),
            )
            return
        self._store_pending_action(
            chat_id,
            {
                "kind": "message",
                "user_message": user_message,
            },
        )
        try:
            if await self._continue_pending_action(update, context):
                return
        finally:
            await self._drain_chat_message_queue(chat_id, context)

    @require_allowed_chat()
    async def handle_photo(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if update.message is None or not update.message.photo:
            return

        session, project_path = await self._active_session_project_or_notify(update, context)
        if session is None or project_path is None:
            return

        if session.get("provider", "codex") != "codex":
            await send_text(update, context, self._t(update, "message.photo_only_codex"))
            return

        caption = update.message.caption or ""
        try:
            attachment_path = await self.photo_attachments.store_photo(update, session["project_folder"])
        except PhotoAttachmentError as exc:
            error_text = self._t(update, "runtime.photo_too_large") if exc.code == "photo_too_large" else str(exc)
            await send_text(update, context, error_text)
            return
        prompt = self.photo_attachments.build_prompt(attachment_path, project_path, caption)
        await self.runtime.run_active_session(update, context, user_message=prompt, image_paths=(attachment_path,))

    @require_allowed_chat()
    async def handle_unsupported_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        await send_text(
            update,
            context,
            self._t(update, "message.unsupported_message_type"),
        )
