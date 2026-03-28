from __future__ import annotations

import asyncio

from telegram import Update
from telegram.ext import ContextTypes

from coding_agent_telegram.filters import resolve_project_path
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
            (
                f"Current session: {session['name']}\n"
                f"Session ID: {active_id}\n"
                f"Project: {session['project_folder']}\n"
                f"Provider: {session.get('provider', 'codex')}\n"
                f"Branch: {session.get('branch_name') or '(current branch)'}"
            ),
        )

    @require_allowed_chat()
    async def handle_abort(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if context.args:
            await send_text(update, context, "Usage: /abort")
            return

        chat_id = update.effective_chat.id
        chat_state = self.deps.store.get_chat_state(self.deps.bot_id, chat_id)
        project_folder = str(chat_state.get("current_project_folder") or "").strip()
        if not project_folder:
            await send_text(update, context, "No project selected.\nPlease run /project <project_folder> first.")
            return

        project_path = resolve_project_path(self.deps.cfg.workspace_root, project_folder)
        if not project_path.exists() or not project_path.is_dir():
            await send_text(update, context, f"Project folder does not exist: {project_folder}\nRun /project {project_folder} again.")
            return

        aborted = await asyncio.to_thread(self.deps.agent_runner.abort_running_process, project_path)
        if not aborted:
            await send_text(update, context, "No running agent process was found for the current project.")
            return
        await send_text(update, context, "Abort signal sent for the current project run.")

    @require_allowed_chat(answer_callback=True)
    async def handle_queue_continue_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        query = update.callback_query
        if query is None or query.data is None:
            return

        await query.answer()
        _, _, decision = query.data.partition("queuecontinue:")
        chat_id = update.effective_chat.id
        if decision == "yes":
            await query.edit_message_text("Continuing with the pending queued questions.")
            await self._drain_chat_message_queue(chat_id, context)
            return
        if decision == "no":
            self._clear_chat_message_queue(chat_id)
            await query.edit_message_text("Pending queued questions were discarded.")

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
            await query.edit_message_text("No queued batch is waiting for a decision.")
            return

        queue_file, queued_messages = pending
        if decision == "group":
            await query.edit_message_text("Processing the queued questions as one batch.")
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
            await query.edit_message_text("Processing the queued questions one by one.")
            await self._dispatch_queued_questions(
                chat_id,
                context,
                queue_file=queue_file,
                queued_messages=queued_messages,
                grouped=False,
            )
            await self._drain_chat_message_queue(chat_id, context)
