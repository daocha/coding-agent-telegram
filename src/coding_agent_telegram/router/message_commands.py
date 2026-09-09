from __future__ import annotations

import asyncio
import logging
import tempfile
import time
from pathlib import Path
from types import SimpleNamespace
from typing import NamedTuple, Optional, Sequence

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

from coding_agent_telegram.session_gap import gap_seconds_since, humanize_gap_seconds, native_session_activity
from coding_agent_telegram.session_runtime import PhotoAttachmentError
from coding_agent_telegram.speech_to_text import SpeechToTextError
from coding_agent_telegram.telegram_sender import send_text

from .base import require_allowed_chat


logger = logging.getLogger(__name__)
MAX_STT_AUDIO_BYTES = 20 * 1024 * 1024
# Size at which the long-gap cache is swept for expired entries before the next insert.
_GAP_CACHE_PRUNE_AT_ENTRIES = 256


class _LongGapProviderConfig(NamedTuple):
    threshold_field: str  # AppConfig attribute holding the idle-seconds threshold
    size_gate_tokens: Optional[int]  # below this, skip the warning even past threshold


# Single source of truth for per-provider long-gap tuning, keyed by provider. A
# provider missing here has the warning disabled outright (fails closed, unlike a
# lookup that silently no-ops one half of the check). size_gate_tokens is in the same
# units session_gap.py reports for that provider (see its module docstring); None
# means no cheap size signal exists, so the idle-time check alone decides.
_LONG_GAP_PROVIDER_CONFIG: dict[str, _LongGapProviderConfig] = {
    "claude": _LongGapProviderConfig("claude_long_gap_seconds", 20_000),  # cache_creation + cache_read + input tokens
    "codex": _LongGapProviderConfig("codex_long_gap_seconds", 50_000),  # cumulative tokens_used from Codex's session db
    "copilot": _LongGapProviderConfig("copilot_long_gap_seconds", None),  # no local size signal; see session_gap.py
}


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
        pending_action = self._pending_action(chat_id)
        should_prioritize_existing_queue = (
            self._has_pending_queue_files(chat_id)
            and not self._is_project_busy(chat_id)
            and not self._has_pending_queue_decision(chat_id)
            and not isinstance(pending_action, dict)
        )
        if self._should_queue_incoming_message(chat_id):
            await self._queue_incoming_message(
                update,
                context,
                user_message,
                separate_batch=should_prioritize_existing_queue,
                drain_after=should_prioritize_existing_queue,
            )
            return
        if await self._maybe_warn_long_gap(update, context, user_message, suppress_working_notice):
            return
        # Handlers run concurrently (block=False), and _maybe_warn_long_gap may have
        # awaited provider I/O above. That await is the only gap between "nothing else
        # is handling this chat" and this message claiming it below, so another message
        # for the same chat can have claimed it meanwhile -- queue behind it instead of
        # racing it. Everything from here to the claim inside
        # _dispatch_pending_message_now is synchronous, so this re-check holds.
        if self._should_queue_incoming_message(chat_id):
            await self._queue_incoming_message(update, context, user_message, separate_batch=False)
            return
        await self._dispatch_pending_message_now(
            update, context, user_message, suppress_working_notice=suppress_working_notice
        )

    async def _queue_incoming_message(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        user_message: str,
        *,
        separate_batch: bool,
        drain_after: bool = False,
    ) -> None:
        chat_id = update.effective_chat.id
        reply_to_message_id = getattr(update.message, "message_id", None)
        _queue_file, question_number = self._enqueue_chat_message(
            chat_id,
            user_message,
            reply_to_message_id=reply_to_message_id,
            separate_batch=separate_batch,
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
            reply_to_message_id=reply_to_message_id,
        )
        if drain_after:
            await self._drain_chat_message_queue(chat_id, context)

    async def _dispatch_pending_message_now(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        user_message: str,
        *,
        suppress_working_notice: bool = False,
    ) -> None:
        """Run *user_message* now, skipping the *queue-behind-other-queued-messages* and
        long-gap checks -- but still deferring to a genuinely busy workspace so a message
        is never silently dropped.

        Used both by the normal (already-checked) path in ``_process_user_message`` and
        to replay a message that was held for a confirmation button (long-gap
        compact/proceed). For a held message, re-running the full should-queue check
        would be wrong: it would push this older, already-approved message behind newer
        messages that queued up while the confirmation prompt was waiting for a reply.
        A currently-busy workspace is different -- that's not a queue-ordering nicety,
        it's the only thing standing between this call and a dropped message, so it's
        still checked explicitly.
        """
        chat_id = update.effective_chat.id
        if self._is_project_busy(chat_id):
            reply_to_message_id = getattr(getattr(update, "message", None), "message_id", None)
            _queue_file, question_number = self._enqueue_chat_message(
                chat_id,
                user_message,
                reply_to_message_id=reply_to_message_id,
            )
            logger.info(
                "Project busy: queued held user message for chat %s as Q%s. Preview: %.120r",
                chat_id,
                question_number,
                user_message,
            )
            await send_text(
                update,
                context,
                self._t(update, "message.question_queued", question_number=question_number),
                reply_to_message_id=reply_to_message_id,
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

    async def _dispatch_active_session_message(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        user_message: str,
        *,
        image_paths: Sequence[Path] = (),
    ) -> None:
        """Run *user_message* (optionally with attachments) directly against the active
        session, bypassing the queueing/long-gap machinery. Mirrors what ``handle_photo``
        already did, factored out so a held photo message can be replayed identically
        after a long-gap confirmation."""
        chat_id = update.effective_chat.id
        try:
            self._last_run_results[chat_id] = await self.runtime.run_active_session(
                update,
                context,
                user_message=user_message,
                image_paths=image_paths,
            )
        finally:
            await self._drain_chat_message_queue(chat_id, context)

    def _prune_session_gap_cache(self, now_monotonic: float) -> None:
        """Drop expired entries so a long-lived bot's cache can't grow without bound.

        Only runs once the dict is big enough for the scan to be worth it; entries are
        tiny, so the cap is about keeping memory flat over months of uptime, not about
        the check itself being hot.
        """
        if len(self._session_gap_safe_until) < _GAP_CACHE_PRUNE_AT_ENTRIES:
            return
        self._session_gap_safe_until = {
            key: safe_until
            for key, safe_until in self._session_gap_safe_until.items()
            if safe_until > now_monotonic
        }

    def _long_gap_threshold_seconds(self, provider: str) -> int:
        provider_config = _LONG_GAP_PROVIDER_CONFIG.get(provider)
        if provider_config is None:
            return 0
        return getattr(self.deps.cfg, provider_config.threshold_field, 0)

    async def _maybe_warn_long_gap(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        user_message: str,
        suppress_working_notice: bool,
        *,
        image_paths: Sequence[Path] = (),
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
        provider_config = _LONG_GAP_PROVIDER_CONFIG.get(provider)
        threshold_seconds = self._long_gap_threshold_seconds(provider)
        if threshold_seconds <= 0:
            return False

        # A burst of quick messages on an already-active session would otherwise hit
        # native_session_activity's filesystem/sqlite lookup on every single one. Skip
        # it only while the session provably *cannot* have crossed the threshold yet:
        # the cached value is the monotonic time the gap measured last check would
        # reach the threshold, so a session checked at (threshold - 1s) idle is cached
        # for 1s, not for another full threshold. Fresh activity only pushes that
        # crossing time further out, so the shortcut can never hide a real long gap.
        cache_key = f"{provider}:{active_id}"
        now_monotonic = time.monotonic()
        safe_until = self._session_gap_safe_until.get(cache_key)
        if safe_until is not None and now_monotonic < safe_until:
            return False

        # native_session_activity does blocking filesystem/sqlite I/O; keep it off the
        # event loop so one chat's check can't stall every other chat's bot.
        last_activity, size_tokens = await asyncio.to_thread(native_session_activity, provider, active_id)
        gap_seconds = gap_seconds_since(last_activity)
        if gap_seconds is None:
            # Activity is unknowable (no transcript/db row), so no warning can ever fire
            # for it. Deliberately not cached: a future check may find the session once
            # its native files appear.
            return False
        if gap_seconds < threshold_seconds:
            self._prune_session_gap_cache(now_monotonic)
            self._session_gap_safe_until[cache_key] = now_monotonic + (threshold_seconds - gap_seconds)
            return False

        # Avoid nagging about sessions too small for a full reprocess to matter, when
        # the provider exposes a cheap size signal at all (session_gap.py returns None
        # for providers/situations it can't determine one for -- fail open there rather
        # than suppressing a legitimate warning).
        size_gate = provider_config.size_gate_tokens if provider_config else None
        if size_gate is not None and size_tokens is not None and size_tokens < size_gate:
            logger.info(
                "Skipping long-gap warning for chat %s session '%s' (%s): idle %.0fs but only "
                "~%s tokens accumulated (below the %s-token gate for provider %s).",
                chat_id,
                session.get("name"),
                active_id,
                gap_seconds,
                size_tokens,
                size_gate,
                provider,
            )
            return False

        # The activity lookup above awaited, so a concurrently-handled message for this
        # chat may have claimed it in the meantime. Storing our own pending action now
        # would overwrite whatever it is holding -- orphaning that message and its
        # buttons, and putting a second warning in the chat. Bail out instead; the
        # caller re-checks and queues this message behind the winner.
        if self._pending_action(chat_id) is not None:
            logger.info(
                "Skipping long-gap warning for chat %s session '%s': another message claimed the "
                "chat while the idle check was running.",
                chat_id,
                session.get("name"),
            )
            return False

        logger.info(
            "Long idle gap detected for chat %s on session '%s' (%s): %.0fs since last activity "
            "(threshold %ss, ~%s tokens accumulated, provider %s). Asking user to compact or proceed.",
            chat_id,
            session.get("name"),
            active_id,
            gap_seconds,
            threshold_seconds,
            size_tokens if size_tokens is not None else "unknown",
            provider,
        )
        self._store_pending_action(
            chat_id,
            {
                "kind": "long_gap_confirm",
                "user_message": user_message,
                "suppress_working_notice": suppress_working_notice,
                "image_paths": [str(path) for path in image_paths],
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
        image_paths = tuple(Path(path) for path in pending_action.get("image_paths") or ())
        self._store_pending_action(chat_id, None)

        async def replay() -> None:
            # Deliberately bypasses _process_user_message: re-running the should-queue
            # and long-gap checks here is wrong for a held message (see
            # _dispatch_pending_message_now's docstring).
            if image_paths:
                await self._dispatch_active_session_message(update, context, user_message, image_paths=image_paths)
            else:
                await self._dispatch_pending_message_now(
                    update, context, user_message, suppress_working_notice=suppress_working_notice
                )

        if action == "longgap:proceed":
            await query.edit_message_text(self._t(update, "runtime.long_gap_proceeding"))
            await replay()
            return

        if action == "longgap:compact":
            await query.edit_message_text(self._t(update, "runtime.long_gap_compacting"))
            # Whether compaction succeeds, fails, or can't start because the workspace is
            # busy, still replay the held message rather than silently dropping it:
            # - success: runs on the new, freshly-compacted session.
            # - failure: compact_active_session already reported the error; replaying
            #   still delivers the user's message instead of losing it.
            # - busy (returns None, no message sent by compact_active_session): the
            #   text-message path still queues correctly via _continue_pending_action;
            #   the photo path shares the same busy-handling as handle_photo already had.
            await self.runtime.compact_active_session(update, context)
            await replay()

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

        chat_id = update.effective_chat.id
        if isinstance(self._pending_action(chat_id), dict):
            # Unlike text (which routes through _process_user_message and queues
            # behind a pending action), a photo can't be queued -- _enqueue_chat_message
            # only stores text. Proceeding anyway would silently overwrite whatever the
            # pending action is holding (e.g. a long-gap compact/proceed confirmation
            # for an earlier message), orphaning its buttons and losing that message.
            await send_text(update, context, self._t(update, "message.photo_blocked_by_pending_action"))
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
        if await self._maybe_warn_long_gap(
            update, context, prompt, suppress_working_notice=False, image_paths=(attachment_path,)
        ):
            return
        # Downloading the photo and running the idle check both awaited, so re-run the
        # guard from the top of this handler: a pending action may have appeared since.
        # A photo can't be queued, so blocking is the only way not to run it behind
        # another message's back (see the top of this handler).
        if self._pending_action(chat_id) is not None:
            await send_text(update, context, self._t(update, "message.photo_blocked_by_pending_action"))
            return
        await self._dispatch_active_session_message(update, context, prompt, image_paths=(attachment_path,))

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
