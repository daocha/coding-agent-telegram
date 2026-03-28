from __future__ import annotations

import asyncio

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

from coding_agent_telegram.telegram_sender import send_html_text, send_text

from .base import require_allowed_chat


class GitCommandMixin:
    @require_allowed_chat()
    async def handle_commit(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if await self._notify_if_current_project_busy(update, context):
            return
        if not self.deps.cfg.enable_commit_command:
            await send_text(
                update,
                context,
                "/commit is disabled.\nSet ENABLE_COMMIT_COMMAND=true in the bot environment to enable it.",
            )
            return

        if update.message is None or not update.message.text:
            await send_text(update, context, "Usage: /commit git add ... && git commit ...")
            return

        raw = update.message.text.partition(" ")[2].strip()
        if not raw:
            await send_text(update, context, "Usage: /commit git add ... && git commit ...")
            return

        session, project_path = await self._active_session_project_or_notify(
            update,
            context,
            require_git_repo=True,
        )
        if session is None or project_path is None:
            return

        commands, ignored = self._validated_commit_commands(raw)
        if not commands:
            await send_text(update, context, "No valid git commit commands were found.")
            return
        if self._requires_trusted_project(commands) and not self.deps.store.is_project_trusted(session["project_folder"]):
            await send_text(
                update,
                context,
                "This project is not trusted for mutating git operations. Use a project created by /project or mark it trusted first.",
            )
            return
        if not self._commands_use_only_project_paths(project_path, commands):
            await send_text(update, context, "Unsafe path arguments are not allowed. Only files inside the current project may be used.")
            return

        command_results: list[tuple[list[str], object]] = []
        for args in commands:
            executed_args = self._effective_git_args(args)
            result = await asyncio.to_thread(self.git.run_safe_commit_command, project_path, executed_args)
            command_results.append((executed_args, result))
            if not result.success:
                await send_html_text(
                    update,
                    context,
                    self._bash_block(self._format_git_response(command_results, ignored)),
                )
                return

        await send_html_text(update, context, self._bash_block(self._format_git_response(command_results, ignored)))

    @require_allowed_chat()
    async def handle_push(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if await self._notify_if_current_project_busy(update, context):
            return
        if context.args:
            await send_text(update, context, self._t(update, "git.usage_push"))
            return

        session, project_path = await self._active_session_project_or_notify(
            update,
            context,
            require_git_repo=True,
        )
        if session is None or project_path is None:
            return

        branch_name = session.get("branch_name") or self.git.current_branch(project_path)
        if not branch_name:
            await send_text(update, context, self._t(update, "git.branch_unknown"))
            return

        confirm_markup = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(self._t(update, "git.push_confirm_button"), callback_data="push:confirm"),
                    InlineKeyboardButton(self._t(update, "git.cancel_button"), callback_data="push:cancel"),
                ]
            ]
        )
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=self._t(update, "git.push_confirm_prompt", branch_name=branch_name),
            parse_mode="Markdown",
            reply_markup=confirm_markup,
        )

    @require_allowed_chat(answer_callback=True)
    async def handle_push_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        query = update.callback_query
        if query is None:
            return

        action = (query.data or "").strip()
        if action == "push:cancel":
            await query.edit_message_text(self._t(update, "git.push_cancelled"))
            return
        if action != "push:confirm":
            return

        session, project_path = await self._active_session_project_or_notify(
            update,
            context,
            require_git_repo=True,
        )
        if session is None or project_path is None:
            return

        branch_name = session.get("branch_name") or self.git.current_branch(project_path)
        if not branch_name:
            await query.edit_message_text(self._t(update, "git.branch_unknown"))
            return

        current_branch = self.git.current_branch(project_path)
        if current_branch != branch_name:
            checkout = await asyncio.to_thread(self.git.checkout_branch, project_path, branch_name)
            if not checkout.success:
                await query.edit_message_text(
                    self._t(update, "git.push_cancelled_checkout_failed", branch_name=branch_name),
                    parse_mode="Markdown",
                )
                await send_html_text(update, context, self._bash_block(self._format_git_response([(["checkout", branch_name], checkout)], [])))
                return

        await query.edit_message_text(self._t(update, "git.push_in_progress", branch_name=branch_name), parse_mode="Markdown")
        result = await asyncio.to_thread(self.git.push_branch, project_path, branch_name)
        await send_html_text(
            update,
            context,
            self._bash_block(self._format_git_response([(["push", "origin", branch_name], result)], [])),
        )
