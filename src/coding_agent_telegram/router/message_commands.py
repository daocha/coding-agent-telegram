from __future__ import annotations

import asyncio
import logging
import tempfile
from pathlib import Path
from types import SimpleNamespace

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

from coding_agent_telegram.session_gap import gap_seconds_since_last_activity, humanize_gap_seconds
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
        skip_long_gap_check: bool = False,
    ) -> None:
        chat_id = update.effective_chat.id
        pending_action = self._pending_action(chat_id)
        should_prioritize_existing_queue = (
            self._has_pending_queue_files(chat_id)
            and not self._is_project_busy(chat_id)
            and not self._has_pending_queue_decision(chat_id)
            and not isinstance(pending_action, dict)
        )
        if self._should_queue_incoming_message(chat_id):
            _queue_file, question_number = self._enqueue_chat_message(
                chat_id,
                user_message,
                reply_to_message_id=getattr(update.message, "message_id", None),
                separate_batch=should_prioritize_existing_queue,
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
            if should_prioritize_existing_queue:
                await self._drain_chat_message_queue(chat_id, context)
            return
        if not skip_long_gap_check and await self._maybe_warn_long_gap(
            update, context, user_message, suppress_working_notice
        ):
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

    def _long_gap_threshold_seconds(self, provider: str) -> int:
        cfg = self.deps.cfg
        if provider == "claude":
            return cfg.claude_long_gap_seconds
        if provider == "codex":
            return cfg.codex_long_gap_seconds
        if provider == "copilot":
            return cfg.copilot_long_gap_seconds
        return 0

    async def _maybe_warn_long_gap(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        user_message: str,
        suppress_working_notice: bool,
    ) -> bool:
        """Ask before resuming a session idle long enough to risk a costly cache miss.

        Returns True if a warning was sent and *user_message* is now held pending a
        button response (caller must not dispatch it), False if it's safe to proceed.
        """
        if not self.deps.cfg.long_gap_warning_enabled:
            return False
        chat_id = update.effective_chat.id
        active_id, session, _project_path = self._active_session_context(chat_id)
        if active_id is None or session is None:
            return False

        provider = str(session.get("provider") or "codex").strip().lower() or "codex"
        threshold_seconds = self._long_gap_threshold_seconds(provider)
        if threshold_seconds <= 0:
            return False

        # gap_seconds_since_last_activity does blocking filesystem/sqlite I/O; keep it
        # off the event loop so one chat's check can't stall every other chat's bot.
        gap_seconds = await asyncio.to_thread(gap_seconds_since_last_activity, provider, active_id)
        if gap_seconds is None or gap_seconds < threshold_seconds:
            return False

        logger.info(
            "Long idle gap detected for chat %s on session '%s' (%s): %.0fs since last activity "
            "(threshold %ss for provider %s). Asking user to compact or proceed.",
            chat_id,
            session.get("name"),
            active_id,
            gap_seconds,
            threshold_seconds,
            provider,
        )
        self._store_pending_action(
            chat_id,
            {
                "kind": "long_gap_confirm",
                "user_message": user_message,
                "suppress_working_notice": suppress_working_notice,
            },
        )
        markup = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        self._t(update, "runtime.long_gap_compact_button"),
                        callback_data="longgap:compact",
                        **self._affirmative_inline_button_kwargs(),
                    ),
                    InlineKeyboardButton(
                        self._t(update, "runtime.long_gap_proceed_button"),
                        callback_data="longgap:proceed",
                        **self._negative_inline_button_kwargs(),
                    ),
                ]
            ]
        )
        await context.bot.send_message(
            chat_id=chat_id,
            text=self._t(update, "runtime.long_gap_warning", gap=humanize_gap_seconds(gap_seconds)),
            reply_markup=markup,
        )
        return True

    @require_allowed_chat(answer_callback=True)
    async def handle_long_gap_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        query = update.callback_query
        if query is None:
            return
        await query.answer()
        action = (query.data or "").strip()
        chat_id = update.effective_chat.id
        pending_action = self._pending_action(chat_id)
        if not isinstance(pending_action, dict) or pending_action.get("kind") != "long_gap_confirm":
            if hasattr(query, "edit_message_reply_markup"):
                await query.edit_message_reply_markup(reply_markup=None)
            return

        user_message = str(pending_action.get("user_message") or "")
        suppress_working_notice = bool(pending_action.get("suppress_working_notice"))
        self._store_pending_action(chat_id, None)

        if action == "longgap:proceed":
            await query.edit_message_text(self._t(update, "runtime.long_gap_proceeding"))
            await self._process_user_message(
                update,
                context,
                user_message,
                suppress_working_notice=suppress_working_notice,
                skip_long_gap_check=True,
            )
            return

        if action == "longgap:compact":
            await query.edit_message_text(self._t(update, "runtime.long_gap_compacting"))
            # Whether compaction succeeds, fails, or can't start because the workspace is
            # busy, still replay the held message rather than silently dropping it:
            # - success: runs on the new, freshly-compacted session.
            # - failure: compact_active_session already reported the error; falling
            #   through still delivers the user's message instead of losing it.
            # - busy (returns None, no message sent by compact_active_session): the
            #   normal queueing path in _process_user_message picks it up and tells
            #   the user it was queued.
            await self.runtime.compact_active_session(update, context)
            await self._process_user_message(
                update,
                context,
                user_message,
                suppress_working_notice=suppress_working_notice,
                skip_long_gap_check=True,
            )

    @require_allowed_chat(answer_callback=True)
    async def handle_agent_reply_option_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        query = update.callback_query
        if query is None or not query.data:
            return

        await query.answer()
        parts = query.data.split(":", 2)
        if len(parts) != 3:
            return
        _, token, index_text = parts
        entry = self._agent_reply_option_tokens.pop(token, None)
        if entry is None:
            if hasattr(query, "edit_message_reply_markup"):
                await query.edit_message_reply_markup(reply_markup=None)
            return

        chat_id, options = entry
        if update.effective_chat is None or update.effective_chat.id != chat_id:
            return
        try:
            option_text = options[int(index_text)]
        except (ValueError, IndexError):
            return

        if hasattr(query, "edit_message_reply_markup"):
            await query.edit_message_reply_markup(reply_markup=None)

        await send_text(update, context, self._t(update, "runtime.reply_option_selected", choice=option_text))
        await self._process_user_message(update, context, option_text)

    @require_allowed_chat()
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if update.message is None or not update.message.text:
            return
        is_create_session, session_name = self._parse_create_session_text(update.message.text)
        if is_create_session:
            await self.handle_new(
                update,
                SimpleNamespace(args=[session_name] if session_name else [], bot=context.bot),
            )
            return
        await self._process_user_message(update, context, update.message.text)

    @require_allowed_chat()
    async def handle_photo(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if update.message is None or not update.message.photo:
            return

        session, project_path = await self._active_session_project_or_notify(update, context)
        if session is None or project_path is None:
            return

        if session.get("provider", "codex") not in ("codex", "claude"):
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
        chat_id = update.effective_chat.id
        try:
            self._last_run_results[chat_id] = await self.runtime.run_active_session(
                update,
                context,
                user_message=prompt,
                image_paths=(attachment_path,),
            )
        finally:
            await self._drain_chat_message_queue(chat_id, context)

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
