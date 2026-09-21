from __future__ import annotations

import asyncio
import time

from telegram import Update
from telegram.ext import ContextTypes

from coding_agent_telegram.filters import resolve_project_path
from coding_agent_telegram.i18n import translate
from coding_agent_telegram.providers import provider_label
from coding_agent_telegram.session_gap import humanize_gap_seconds
from coding_agent_telegram.telegram_sender import send_text
from coding_agent_telegram.usage_status import (
    ProviderUsage,
    RateWindow,
    fetch_codex_usage,
    fetch_copilot_usage,
    get_claude_usage,
)

from .base import logger, require_allowed_chat


class SessionStatusCommandMixin:
    @require_allowed_chat()
    async def handle_current(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        chat_id = update.effective_chat.id
        active_id, session = await self._active_session_or_notify(update, context)
        if active_id is None or session is None:
            return

        logger.info(
            "Reported current session '%s' (%s) for chat %s.",
            session["name"],
            active_id,
            chat_id,
        )
        details = self._t(
            update,
            "status.current_session_details",
            session_name=session["name"],
            session_id=active_id,
            project_folder=session["project_folder"],
            provider=session.get("provider", "codex"),
            branch_name=session.get("branch_name") or self._t(update, "status.current_branch_placeholder"),
        )
        activity_line = await self._switch_activity_line(chat_id, session.get("provider", "codex"), active_id)
        if activity_line:
            details = f"{details}\n{activity_line}"
        await send_text(update, context, details)

    @require_allowed_chat()
    async def handle_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if context.args:
            await send_text(update, context, self._t(update, "status.usage_status"))
            return

        def fetch_all() -> tuple[ProviderUsage, ProviderUsage, ProviderUsage]:
            claude_usage = get_claude_usage()
            codex_usage = fetch_codex_usage(self.deps.cfg.codex_bin)
            copilot_usage = fetch_copilot_usage()
            return claude_usage, codex_usage, copilot_usage

        claude_usage, codex_usage, copilot_usage = await self._run_with_typing(update, context, fetch_all)

        locale = self._chat_locale(update.effective_chat.id)
        lines = [self._t(update, "status.usage_title")]
        for usage in (claude_usage, codex_usage, copilot_usage):
            lines.append("")
            lines.append(self._format_provider_usage(locale, usage))

        logger.info(
            "Reported provider usage status for chat %s (claude=%s, codex=%s, copilot=%s).",
            update.effective_chat.id,
            claude_usage.available,
            codex_usage.available,
            copilot_usage.available,
        )
        await send_text(update, context, "\n".join(lines))

    def _format_provider_usage(self, locale: str, usage: ProviderUsage) -> str:
        label = provider_label(usage.provider)
        if usage.plan:
            label = f"{label} ({usage.plan})"
        if not usage.available:
            detail = usage.error or translate(locale, "status.usage_unknown")
            return f"{label}\n  {translate(locale, 'status.usage_unavailable', detail=detail)}"

        five_hour_label = translate(locale, "status.usage_five_hour")
        weekly_label = translate(locale, "status.usage_weekly")
        lines = [label]
        if usage.observed_at is not None:
            age = max(0.0, time.time() - usage.observed_at)
            lines.append(f"  {translate(locale, 'status.usage_last_observed', duration=humanize_gap_seconds(age))}")
        lines.append(f"  {self._format_rate_window(locale, five_hour_label, usage.five_hour, usage.five_hour_note)}")
        lines.append(f"  {self._format_rate_window(locale, weekly_label, usage.weekly, usage.weekly_note)}")
        return "\n".join(lines)

    def _format_rate_window(self, locale: str, label: str, window: RateWindow | None, note: str | None) -> str:
        if window is None:
            detail = note or translate(locale, "status.usage_unknown")
            return f"{label}: {translate(locale, 'status.usage_na', detail=detail)}"
        text = f"{label}: {window.used_percent:g}%"
        if window.resets_at:
            remaining = window.resets_at - time.time()
            if remaining > 0:
                text += f" ({translate(locale, 'status.usage_resets_in', duration=humanize_gap_seconds(remaining))})"
        return text

    @require_allowed_chat()
    async def handle_abort(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if context.args:
            await send_text(update, context, self._t(update, "status.usage_abort"))
            return

        chat_id = update.effective_chat.id
        chat_state = self.deps.store.get_chat_state(self.deps.bot_id, chat_id)
        project_folder = str(chat_state.get("current_project_folder") or "").strip()
        if not project_folder:
            await send_text(update, context, self._t(update, "common.no_project_selected"))
            return

        project_path = resolve_project_path(self.deps.cfg.workspace_root, project_folder)
        if not project_path.exists() or not project_path.is_dir():
            await send_text(update, context, self._t(update, "project.project_folder_missing_retry", project_folder=project_folder))
            return

        aborted = await asyncio.to_thread(self.deps.agent_runner.abort_running_process, project_path)
        if not aborted:
            await send_text(update, context, self._t(update, "status.no_running_agent"))
            return
        await send_text(update, context, self._t(update, "status.abort_signal_sent"))

    @require_allowed_chat()
    async def handle_compact(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if context.args:
            await send_text(update, context, self._t(update, "status.usage_compact"))
            return

        active_id, session = await self._active_session_or_notify(update, context)
        if active_id is None or session is None:
            return
        if await self._notify_if_current_project_busy(update, context):
            return

        await self.runtime.compact_active_session(update, context)

    @require_allowed_chat(answer_callback=True)
    async def handle_queue_continue_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        query = update.callback_query
        if query is None or query.data is None:
            return

        await query.answer()
        _, _, decision = query.data.partition("queuecontinue:")
        chat_id = update.effective_chat.id
        if decision == "yes":
            await query.edit_message_text(translate(self._chat_locale(chat_id), "queue.continuing"))
            await self._drain_chat_message_queue(chat_id, context)
            return
        if decision == "no":
            self._clear_chat_message_queue(chat_id)
            await query.edit_message_text(translate(self._chat_locale(chat_id), "queue.discarded"))

    @require_allowed_chat(answer_callback=True)
    async def handle_queue_batch_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        query = update.callback_query
        if query is None or query.data is None:
            return

        await query.answer()
        _, _, decision = query.data.partition("queuebatch:")
        chat_id = update.effective_chat.id
        pending = self._chat_pending_queue_decisions.pop(chat_id, None)
        if pending is None:
            await query.edit_message_text(translate(self._chat_locale(chat_id), "queue.no_batch_pending"))
            return

        queue_file, queued_messages = pending
        if decision == "group":
            self._chat_queue_batch_modes.pop(chat_id, None)
            await query.edit_message_text(translate(self._chat_locale(chat_id), "queue.processing_grouped"))
            await self._dispatch_queued_questions(
                chat_id,
                context,
                queue_file=queue_file,
                queued_messages=queued_messages,
                grouped=True,
            )
            await self._drain_chat_message_queue(chat_id, context)
            return
        if decision == "single":
            self._chat_queue_batch_modes[chat_id] = "single"
            await query.edit_message_text(translate(self._chat_locale(chat_id), "queue.processing_single"))
            await self._dispatch_queued_questions(
                chat_id,
                context,
                queue_file=queue_file,
                queued_messages=queued_messages,
                grouped=False,
            )
            await self._drain_chat_message_queue(chat_id, context)
            return
        if decision == "cancel":
            self._chat_queue_batch_modes.pop(chat_id, None)
            queue_file.unlink(missing_ok=True)
            self._queue_lock_path(queue_file).unlink(missing_ok=True)
            await query.edit_message_text(translate(self._chat_locale(chat_id), "queue.cancelled"))
            await self._drain_chat_message_queue(chat_id, context)
