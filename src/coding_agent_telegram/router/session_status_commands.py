from __future__ import annotations

import asyncio

from telegram import Update
from telegram.ext import ContextTypes

from coding_agent_telegram.filters import resolve_project_path
from coding_agent_telegram.i18n import translate
from coding_agent_telegram.telegram_sender import send_text

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
        await send_text(
            update,
            context,
            self._t(
                update,
                "status.current_session_details",
                session_name=session["name"],
                session_id=active_id,
                project_folder=session["project_folder"],
                provider=session.get("provider", "codex"),
                branch_name=session.get("branch_name") or self._t(update, "status.current_branch_placeholder"),
            ),
        )

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
