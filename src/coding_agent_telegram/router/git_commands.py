from __future__ import annotations

import asyncio

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

from coding_agent_telegram.diff_utils import split_changed_files
from coding_agent_telegram.telegram_sender import send_html_text, send_text

from .base import require_allowed_chat


class GitCommandMixin:
    async def _refresh_branch_with_checkout(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        *,
        project_path,
        branch_name: str,
    ) -> tuple[bool, str | None, tuple[str, ...]]:
        current_branch = self.git.current_branch(project_path)
        if current_branch != branch_name:
            checkout = await asyncio.to_thread(self.git.checkout_branch, project_path, branch_name)
            if not checkout.success:
                return False, checkout.message, ()

        result = await asyncio.to_thread(self.git.refresh_current_branch, project_path)
        if not result.success:
            return False, result.message, ()
        return True, result.message, tuple(result.warnings)

    @require_allowed_chat()
    async def handle_commit(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if await self._notify_if_current_project_busy(update, context):
            return
        if not self.deps.cfg.enable_commit_command:
            await send_text(
                update,
                context,
                self._t(update, "git.commit_disabled"),
            )
            return

        if update.message is None or not update.message.text:
            await send_text(update, context, self._t(update, "git.usage_commit"))
            return

        raw = update.message.text.partition(" ")[2].strip()
        if not raw:
            await send_text(update, context, self._t(update, "git.usage_commit"))
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
            await send_text(update, context, self._t(update, "git.no_valid_commit_commands"))
            return
        if self._requires_trusted_project(commands) and not self.deps.store.is_project_trusted(session["project_folder"]):
            await send_text(
                update,
                context,
                self._t(update, "git.project_not_trusted_for_mutation"),
            )
            return
        if not self._commands_use_only_project_paths(project_path, commands):
            await send_text(update, context, self._t(update, "git.unsafe_path_arguments"))
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
    async def handle_diff(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if context.args:
            await send_text(update, context, self._t(update, "git.usage_diff"))
            return

        session, project_path = await self._active_session_project_or_notify(
            update,
            context,
            require_git_repo=True,
        )
        if session is None or project_path is None:
            return

        branch_name = session.get("branch_name") or self.git.current_branch(project_path) or self._t(
            update,
            "status.current_branch_placeholder",
        )
        tracked_files, untracked_files = split_changed_files(project_path)
        lines = [
            self._t(update, "diff.session_label", session_name=session["name"]),
            f"{self._t(update, 'diff.project_label', project_folder=session['project_folder'])} <{branch_name}>",
            "",
            self._t(update, "diff.tracked_files"),
        ]
        if tracked_files:
            lines.extend(f"- {path}" for path in tracked_files)
        else:
            lines.append(f"- {self._t(update, 'diff.none')}")
        lines.extend(["", self._t(update, "diff.untracked_files")])
        if untracked_files:
            lines.extend(f"- {path}" for path in untracked_files)
        else:
            lines.append(f"- {self._t(update, 'diff.none')}")
        await send_text(update, context, "\n".join(lines))

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
                    InlineKeyboardButton(
                        self._t(update, "git.push_confirm_button"),
                        callback_data="push:confirm",
                        **self._affirmative_inline_button_kwargs(),
                    ),
                    InlineKeyboardButton(
                        self._t(update, "git.cancel_button"),
                        callback_data="push:cancel",
                        **self._negative_inline_button_kwargs(),
                    ),
                ]
            ]
        )
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=self._t(update, "git.push_confirm_prompt", branch_name=branch_name),
            parse_mode="Markdown",
            reply_markup=confirm_markup,
        )

    @require_allowed_chat()
    async def handle_pull(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if await self._notify_if_current_project_busy(update, context):
            return
        if context.args:
            await send_text(update, context, self._t(update, "git.usage_pull"))
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

        default_branch = self.git.default_branch(project_path) or branch_name
        prompt_key = "git.pull_confirm_prompt_with_default" if default_branch and default_branch != branch_name else "git.pull_confirm_prompt"

        confirm_markup = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        self._t(update, "git.pull_confirm_button"),
                        callback_data="pull:confirm",
                        **self._affirmative_inline_button_kwargs(),
                    ),
                    InlineKeyboardButton(
                        self._t(update, "git.cancel_button"),
                        callback_data="pull:cancel",
                        **self._negative_inline_button_kwargs(),
                    ),
                ]
            ]
        )
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=self._t(
                update,
                prompt_key,
                branch_name=branch_name,
                default_branch=default_branch,
            ),
            parse_mode="Markdown",
            reply_markup=confirm_markup,
        )

    @require_allowed_chat(answer_callback=True)
    async def handle_pull_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        query = update.callback_query
        if query is None:
            return

        action = (query.data or "").strip()
        if action == "pull:cancel":
            await query.edit_message_text(self._t(update, "git.pull_cancelled"))
            return
        if action != "pull:confirm":
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

        default_branch = self.git.default_branch(project_path) or branch_name
        prompt_key = "git.pull_in_progress_with_default" if default_branch and default_branch != branch_name else "git.pull_in_progress"
        await query.edit_message_text(
            self._t(
                update,
                prompt_key,
                branch_name=branch_name,
                default_branch=default_branch,
            ),
            parse_mode="Markdown",
        )

        completed_messages: list[str] = []
        warnings: list[str] = []

        if default_branch and default_branch != branch_name:
            ok, message, branch_warnings = await self._refresh_branch_with_checkout(
                update,
                context,
                project_path=project_path,
                branch_name=default_branch,
            )
            if not ok:
                await send_text(update, context, message or self._t(update, "bot.error.command_failed"))
                return
            if message:
                completed_messages.append(message)
            warnings.extend(branch_warnings)

        ok, message, branch_warnings = await self._refresh_branch_with_checkout(
            update,
            context,
            project_path=project_path,
            branch_name=branch_name,
        )
        if not ok:
            await send_text(update, context, message or self._t(update, "bot.error.command_failed"))
            return
        if message:
            completed_messages.append(message)
        warnings.extend(branch_warnings)

        lines = completed_messages or [self._t(update, "git.pull_completed")]
        if warnings:
            lines.extend(["", self._t(update, "project.refresh_warnings")])
            lines.extend(f"- {warning}" for warning in warnings)
        await send_text(update, context, "\n".join(lines))

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
