from __future__ import annotations

import tempfile
from pathlib import Path

from telegram import Update
from telegram.ext import ContextTypes

from coding_agent_telegram.session_runtime import PhotoAttachmentError
from coding_agent_telegram.speech_to_text import SpeechToTextError
from coding_agent_telegram.telegram_sender import send_text

from .base import require_allowed_chat


class MessageCommandMixin:
    async def _process_user_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user_message: str) -> None:
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
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if update.message is None or not update.message.text:
            return
        await self._process_user_message(update, context, update.message.text)

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
    async def handle_voice(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if update.message is None or not update.message.voice:
            return
        if not self.speech_to_text.enabled:
            await send_text(update, context, self._t(update, "message.voice_speech_to_text_disabled"))
            return

        suffix = Path(update.message.voice.file_unique_id or "voice").suffix or ".ogg"
        telegram_file = await update.message.voice.get_file()
        if suffix == ".ogg" and telegram_file.file_path:
            resolved_suffix = Path(telegram_file.file_path).suffix.lower()
            if resolved_suffix:
                suffix = resolved_suffix

        with tempfile.NamedTemporaryFile(prefix="coding-agent-telegram-voice-", suffix=suffix, delete=False) as handle:
            temp_path = Path(handle.name)
        try:
            content = bytes(await telegram_file.download_as_bytearray())
            temp_path.write_bytes(content)
            result = await self._run_with_typing(
                update,
                context,
                self.speech_to_text.transcribe_file,
                temp_path,
            )
        except SpeechToTextError as exc:
            if exc.code == "timeout":
                message = self._t(update, "runtime.voice_conversion_timed_out")
            else:
                message = self._t(update, "runtime.voice_conversion_failed")
            if exc.likely_first_download:
                message = f"{message}\n\n{self._t(update, 'runtime.voice_model_initial_download_note')}"
            await send_text(update, context, message)
            return
        except Exception:
            await send_text(update, context, self._t(update, "runtime.voice_conversion_failed"))
            return
        finally:
            temp_path.unlink(missing_ok=True)

        if result is None:
            return
        await send_text(
            update,
            context,
            self._t(update, "runtime.voice_transcript_preview", transcript=result.text),
        )
        await self._process_user_message(update, context, result.text)

    @require_allowed_chat()
    async def handle_unsupported_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        await send_text(
            update,
            context,
            self._t(update, "message.unsupported_message_type"),
        )
