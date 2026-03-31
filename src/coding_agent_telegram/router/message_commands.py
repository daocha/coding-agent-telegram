from __future__ import annotations

import logging
import tempfile
from pathlib import Path

from telegram import Update
from telegram.ext import ContextTypes

from coding_agent_telegram.session_runtime import PhotoAttachmentError
from coding_agent_telegram.speech_to_text import SpeechToTextError
from coding_agent_telegram.telegram_sender import send_text

from .base import require_allowed_chat


logger = logging.getLogger(__name__)
MAX_STT_AUDIO_BYTES = 20 * 1024 * 1024


class MessageCommandMixin:
    async def _process_user_message(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        user_message: str,
        *,
        suppress_working_notice: bool = False,
    ) -> None:
        chat_id = update.effective_chat.id
        if self._should_queue_incoming_message(chat_id):
            _queue_file, question_number = self._enqueue_chat_message(
                chat_id,
                user_message,
                reply_to_message_id=getattr(update.message, "message_id", None),
            )
            logger.info(
                "Queued user message for chat %s as Q%s. Preview: %.120r",
                chat_id,
                question_number,
                user_message,
            )
            await send_text(
                update,
                context,
                self._t(update, "message.question_queued", question_number=question_number),
                reply_to_message_id=getattr(update.message, "message_id", None),
            )
            return
        logger.info("Processing user message immediately for chat %s. Preview: %.120r", chat_id, user_message)
        self._store_pending_action(
            chat_id,
            {
                "kind": "message",
                "user_message": user_message,
                "suppress_working_notice": suppress_working_notice,
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

    async def _handle_audio_like(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        telegram_media,
        *,
        media_kind: str,
    ) -> None:
        if update.message is None or telegram_media is None:
            return
        logger.info(
            "Received Telegram %s message for speech-to-text in chat %s.",
            media_kind,
            update.effective_chat.id if update.effective_chat is not None else "unknown",
        )
        if not self.speech_to_text.enabled:
            await send_text(update, context, self._t(update, "message.voice_speech_to_text_disabled"))
            return

        suffix = Path(
            getattr(telegram_media, "file_name", "") or getattr(telegram_media, "file_unique_id", "") or media_kind
        ).suffix or ".ogg"
        telegram_file = await telegram_media.get_file()
        logger.debug(
            "Speech-to-text input prepared for chat %s: media_kind=%s file_path=%r initial_suffix=%r model=%s timeout=%ss",
            update.effective_chat.id if update.effective_chat is not None else "unknown",
            media_kind,
            getattr(telegram_file, "file_path", None),
            suffix,
            self.speech_to_text.model,
            self.speech_to_text.timeout_seconds,
        )
        if suffix == ".ogg" and getattr(telegram_file, "file_path", None):
            resolved_suffix = Path(telegram_file.file_path).suffix.lower()
            if resolved_suffix:
                suffix = resolved_suffix

        declared_size = getattr(telegram_media, "file_size", None)
        if isinstance(declared_size, int) and declared_size > MAX_STT_AUDIO_BYTES:
            await send_text(
                update,
                context,
                self._t(
                    update,
                    "runtime.voice_audio_too_large",
                    max_size_mb=MAX_STT_AUDIO_BYTES // (1024 * 1024),
                ),
            )
            return

        with tempfile.NamedTemporaryFile(prefix="coding-agent-telegram-voice-", suffix=suffix, delete=False) as handle:
            temp_path = Path(handle.name)
        try:
            content = bytes(await telegram_file.download_as_bytearray())
            if len(content) > MAX_STT_AUDIO_BYTES:
                await send_text(
                    update,
                    context,
                    self._t(
                        update,
                        "runtime.voice_audio_too_large",
                        max_size_mb=MAX_STT_AUDIO_BYTES // (1024 * 1024),
                    ),
                )
                return
            temp_path.write_bytes(content)
            logger.debug(
                "Downloaded Telegram %s message for chat %s to %s (%s bytes).",
                media_kind,
                update.effective_chat.id if update.effective_chat is not None else "unknown",
                temp_path,
                len(content),
            )
            result = await self._run_with_typing(
                update,
                context,
                self.speech_to_text.transcribe_file,
                temp_path,
            )
        except SpeechToTextError as exc:
            logger.warning(
                "Telegram %s speech-to-text failed for chat %s: code=%s detail=%s",
                media_kind,
                update.effective_chat.id if update.effective_chat is not None else "unknown",
                exc.code,
                exc.detail or "(none)",
            )
            if exc.code == "timeout":
                message = self._t(update, "runtime.voice_conversion_timed_out")
            else:
                message = self._t(update, "runtime.voice_conversion_failed")
            if exc.likely_first_download:
                message = f"{message}\n\n{self._t(update, 'runtime.voice_model_initial_download_note')}"
            await send_text(update, context, message)
            return
        except Exception:
            logger.exception(
                "Unexpected Telegram %s speech-to-text failure for chat %s.",
                media_kind,
                update.effective_chat.id if update.effective_chat is not None else "unknown",
            )
            await send_text(update, context, self._t(update, "runtime.voice_conversion_failed"))
            return
        finally:
            temp_path.unlink(missing_ok=True)

        if result is None:
            return
        chat_id = update.effective_chat.id
        logger.info(
            "Speech-to-text succeeded for Telegram %s message in chat %s. Transcript preview: %.120r",
            media_kind,
            chat_id,
            result.text,
        )
        logger.debug(
            "Transcript metadata for chat %s: media_kind=%s chars=%s reply_to_message_id=%s",
            chat_id,
            media_kind,
            len(result.text),
            getattr(update.message, "message_id", None),
        )
        if self._should_queue_incoming_message(chat_id):
            _queue_file, question_number = self._enqueue_chat_message(
                chat_id,
                result.text,
                reply_to_message_id=getattr(update.message, "message_id", None),
            )
            logger.info(
                "Queued transcript from Telegram %s message for chat %s as Q%s.",
                media_kind,
                chat_id,
                question_number,
            )
            await send_text(
                update,
                context,
                self._t(
                    update,
                    "runtime.voice_transcript_queued_preview",
                    transcript=result.text,
                    question_number=question_number,
                ),
            )
            return
        logger.info("Dispatching transcript from Telegram %s message immediately for chat %s.", media_kind, chat_id)
        await send_text(
            update,
            context,
            self._t(update, "runtime.voice_transcript_preview", transcript=result.text),
        )
        await self._process_user_message(update, context, result.text, suppress_working_notice=True)

    @require_allowed_chat()
    async def handle_voice(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if update.message is None or not update.message.voice:
            return
        await self._handle_audio_like(update, context, update.message.voice, media_kind="voice")

    @require_allowed_chat()
    async def handle_audio(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if update.message is None or not update.message.audio:
            return
        await self._handle_audio_like(update, context, update.message.audio, media_kind="audio")

    @require_allowed_chat()
    async def handle_unsupported_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if update.message is not None:
            unsupported_types = [
                field_name
                for field_name in ("animation", "audio", "document", "sticker", "video", "video_note")
                if getattr(update.message, field_name, None) is not None
            ]
            logger.info(
                "Unsupported Telegram message type from chat %s: %s",
                update.effective_chat.id if update.effective_chat is not None else "unknown",
                ", ".join(unsupported_types) or "unknown",
            )
        await send_text(
            update,
            context,
            self._t(update, "message.unsupported_message_type"),
        )
