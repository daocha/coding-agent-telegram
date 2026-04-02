from __future__ import annotations

import asyncio
import html
import os
from types import SimpleNamespace

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

from coding_agent_telegram.diff_utils import chunk_fenced_diff, collect_diffs, split_changed_files
from coding_agent_telegram.telegram_sender import send_code_block, send_html_text, send_text, split_assistant_output

from .base import require_allowed_chat


class GitCommandMixin:
    DIFF_BUTTON_PAGE_SIZE = 10
    COMMIT_GENERATION_PROMPT = (
        'Execute: Analyze and compare to git HEAD, then Generate a git commit command for the files you changed in this task, with a detailed changelog-style commit message. '
        'Only include files you intentionally modified for this task. '
        'Do not include unrelated changed files. '
        'Do not include untracked files unless they were created for this task and are clearly required. '
        'Output only a single executable command in this format with \\ if there is line break: git add <files> && git commit -m "<message>".'
    )

    @staticmethod
    def _diff_button_label(index: int, path: str, *, max_name_length: int = 20) -> str:
        name = os.path.basename(path.rstrip("/")) or path
        if len(name) > max_name_length:
            name = f"{name[: max_name_length - 1]}…"
        return f"{index}. {name}"

    def _build_diff_button_rows(self, update: Update, tracked_files: list[str], *, page: int) -> list[list[InlineKeyboardButton]]:
        rows: list[list[InlineKeyboardButton]] = []
        total_pages = max(1, (len(tracked_files) + self.DIFF_BUTTON_PAGE_SIZE - 1) // self.DIFF_BUTTON_PAGE_SIZE)
        page = min(max(page, 0), total_pages - 1)
        start = page * self.DIFF_BUTTON_PAGE_SIZE
        page_files = tracked_files[start : start + self.DIFF_BUTTON_PAGE_SIZE]
        row: list[InlineKeyboardButton] = []
        for offset, path in enumerate(page_files, start=1):
            absolute_index = start + offset
            row.append(
                InlineKeyboardButton(
                    self._diff_button_label(absolute_index, path),
                    callback_data=f"diffshow:{absolute_index - 1}",
                )
            )
            if len(row) == 2:
                rows.append(row)
                row = []
        if row:
            rows.append(row)
        nav_row: list[InlineKeyboardButton] = []
        if page > 0:
            nav_row.append(InlineKeyboardButton(self._t(update, "diff.button_prev_page"), callback_data=f"diffpage:{page - 1}"))
        if page < total_pages - 1:
            nav_row.append(InlineKeyboardButton(self._t(update, "diff.button_next_page"), callback_data=f"diffpage:{page + 1}"))
        if nav_row:
            rows.append(nav_row)
        return rows

    def _build_diff_message(
        self,
        update: Update,
        session: dict[str, object],
        *,
        branch_name: str,
        tracked_files: list[str],
        untracked_files: list[str],
        page: int,
    ) -> tuple[str, InlineKeyboardMarkup | None]:
        total_pages = max(1, (len(tracked_files) + self.DIFF_BUTTON_PAGE_SIZE - 1) // self.DIFF_BUTTON_PAGE_SIZE)
        page = min(max(page, 0), total_pages - 1)
        start = page * self.DIFF_BUTTON_PAGE_SIZE
        page_files = tracked_files[start : start + self.DIFF_BUTTON_PAGE_SIZE]
        lines = [
            self._t(update, "diff.session_label", session_name=session["name"]),
            f"{self._t(update, 'diff.project_label', project_folder=session['project_folder'])} <{branch_name}>",
            "",
            self._t(update, "diff.tracked_files"),
        ]
        if page_files:
            if len(tracked_files) > len(page_files):
                lines.append(
                    self._t(
                        update,
                        "diff.tracked_files_page_info",
                        start=start + 1,
                        end=start + len(page_files),
                        total=len(tracked_files),
                    )
                )
            lines.extend(f"{start + index}. {path}" for index, path in enumerate(page_files, start=1))
        else:
            lines.append(f"- {self._t(update, 'diff.none')}")
        lines.extend(["", self._t(update, "diff.untracked_files")])
        if untracked_files:
            lines.extend(f"- {path}" for path in untracked_files)
        else:
            lines.append(f"- {self._t(update, 'diff.none')}")
        if tracked_files:
            lines.extend(["", self._t(update, "diff.click_button_to_see_file_diff")])
        reply_markup = InlineKeyboardMarkup(self._build_diff_button_rows(update, tracked_files, page=page)) if tracked_files else None
        return "\n".join(lines), reply_markup

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

    def _generated_commit_commands(self) -> dict[int, dict[str, str]]:
        commands = getattr(self, "_chat_generated_commit_commands", None)
        if not isinstance(commands, dict):
            commands = {}
            self._chat_generated_commit_commands = commands
        return commands

    def _extract_generated_commit_command(self, assistant_text: str) -> str | None:
        for segment in split_assistant_output(assistant_text or ""):
            if segment.kind != "code":
                continue
            lines = [line.strip() for line in segment.text.splitlines() if line.strip()]
            if not lines or not lines[0].startswith("git add "):
                continue
            command = " ".join(line.removesuffix("\\").strip() for line in lines)
            if "git commit " in command:
                return command
        stripped_lines = [line.strip() for line in (assistant_text or "").splitlines() if line.strip()]
        if stripped_lines and stripped_lines[0].startswith("git add "):
            command = " ".join(line.removesuffix("\\").strip() for line in stripped_lines)
            if "git commit " in command:
                return command
        return None

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
            session, project_path = await self._active_session_project_or_notify(
                update,
                context,
                require_git_repo=True,
            )
            if session is None or project_path is None:
                return
            confirm_markup = InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            self._t(update, "git.commit_generate_button"),
                            callback_data="commitgen:confirm",
                            **self._affirmative_inline_button_kwargs(),
                        ),
                        InlineKeyboardButton(
                            self._t(update, "git.cancel_button"),
                            callback_data="commitgen:cancel",
                            **self._negative_inline_button_kwargs(),
                        ),
                    ]
                ]
            )
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=f"{self._t(update, 'git.usage_commit')}\n\n{self._t(update, 'git.commit_generate_prompt')}",
                reply_markup=confirm_markup,
            )
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
        text, reply_markup = self._build_diff_message(
            update,
            session,
            branch_name=branch_name,
            tracked_files=tracked_files,
            untracked_files=untracked_files,
            page=0,
        )
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=html.escape(text),
            parse_mode="HTML",
            reply_markup=reply_markup,
        )

    @require_allowed_chat(answer_callback=True)
    async def handle_diff_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        query = update.callback_query
        if query is None:
            return

        await query.answer()
        data = (query.data or "").strip()
        if data.startswith("diffpage:"):
            try:
                page = int(data.partition(":")[2])
            except ValueError:
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
            text, reply_markup = self._build_diff_message(
                update,
                session,
                branch_name=branch_name,
                tracked_files=tracked_files,
                untracked_files=untracked_files,
                page=page,
            )
            await query.edit_message_text(
                text=html.escape(text),
                parse_mode="HTML",
                reply_markup=reply_markup,
            )
            return
        if not data.startswith("diffshow:"):
            return
        try:
            file_index = int(data.partition(":")[2])
        except ValueError:
            return

        session, project_path = await self._active_session_project_or_notify(
            update,
            context,
            require_git_repo=True,
        )
        if session is None or project_path is None:
            return

        tracked_files, _ = split_changed_files(project_path)
        if file_index < 0 or file_index >= len(tracked_files):
            await send_text(update, context, self._t(update, "diff.none"))
            return

        file_path = tracked_files[file_index]
        diffs = collect_diffs(project_path, [file_path], include_cached=True)
        if not diffs:
            await send_text(update, context, self._t(update, "diff.none"))
            return

        chunks = chunk_fenced_diff(
            file_path,
            diffs[0].diff,
            self.deps.cfg.max_telegram_message_length,
            locale=self._locale(update),
        )
        if not chunks:
            await send_text(update, context, self._t(update, "diff.none"))
            return
        for chunk in chunks:
            await send_code_block(
                update,
                context,
                chunk.header,
                chunk.code,
                language=chunk.language,
            )

    @require_allowed_chat(answer_callback=True)
    async def handle_commit_generate_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        query = update.callback_query
        if query is None:
            return

        await query.answer()
        action = (query.data or "").strip()
        if action == "commitgen:cancel":
            await query.edit_message_text(self._t(update, "git.commit_generate_cancelled"))
            return
        if action != "commitgen:confirm":
            return

        generated_command = await self._generate_commit_command_with_provider(update, context)
        if generated_command is None:
            await query.edit_message_text(self._t(update, "git.no_valid_commit_commands"))
            return

        chat_state = self.deps.store.get_chat_state(self.deps.bot_id, update.effective_chat.id)
        active_session_id = str(chat_state.get("active_session_id") or "").strip()
        if not active_session_id:
            await query.edit_message_text(self._t(update, "common.no_active_session"))
            return
        session = chat_state.get("sessions", {}).get(active_session_id)
        if not isinstance(session, dict):
            await query.edit_message_text(self._t(update, "common.no_active_session"))
            return

        self._generated_commit_commands()[update.effective_chat.id] = {
            "command": generated_command,
            "session_id": active_session_id,
            "project_folder": str(session.get("project_folder") or ""),
        }
        execute_markup = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        self._t(update, "git.commit_execute_button"),
                        callback_data="commitexec:confirm",
                        **self._affirmative_inline_button_kwargs(),
                    ),
                    InlineKeyboardButton(
                        self._t(update, "git.cancel_button"),
                        callback_data="commitexec:cancel",
                        **self._negative_inline_button_kwargs(),
                    ),
                ]
            ]
        )
        await query.edit_message_text(self._t(update, "git.commit_generated_below"))
        await context.bot.send_message(chat_id=update.effective_chat.id, text=self._t(update, "git.commit_execute_prompt"), reply_markup=execute_markup)

    async def _generate_commit_command_with_provider(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> str | None:
        session, project_path = await self._active_session_project_or_notify(
            update,
            context,
            require_git_repo=True,
        )
        if session is None or project_path is None:
            return

        result = await self.runtime.run_active_session(update, context, user_message=self.COMMIT_GENERATION_PROMPT)
        if result is None or not result.success:
            return None
        return self._extract_generated_commit_command(result.assistant_text)

    @require_allowed_chat(answer_callback=True)
    async def handle_commit_execute_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        query = update.callback_query
        if query is None:
            return

        await query.answer()
        action = (query.data or "").strip()
        if action == "commitexec:cancel":
            await query.edit_message_text(self._t(update, "git.commit_generate_cancelled"))
            return
        if action != "commitexec:confirm":
            return

        payload = self._generated_commit_commands().get(update.effective_chat.id)
        if payload is None:
            await query.edit_message_text(self._t(update, "git.no_valid_commit_commands"))
            return
        chat_state = self.deps.store.get_chat_state(self.deps.bot_id, update.effective_chat.id)
        active_session_id = str(chat_state.get("active_session_id") or "").strip()
        active_session = chat_state.get("sessions", {}).get(active_session_id) if active_session_id else None
        active_project_folder = str(active_session.get("project_folder") or "") if isinstance(active_session, dict) else ""
        if (
            active_session_id != str(payload.get("session_id") or "")
            or active_project_folder != str(payload.get("project_folder") or "")
        ):
            self._generated_commit_commands().pop(update.effective_chat.id, None)
            await query.edit_message_text(self._t(update, "git.commit_execute_context_changed"))
            return
        command = str(payload.get("command") or "").strip()
        if not command:
            self._generated_commit_commands().pop(update.effective_chat.id, None)
            await query.edit_message_text(self._t(update, "git.no_valid_commit_commands"))
            return

        await query.edit_message_text(self._t(update, "git.commit_execute_confirmed"))
        synthetic_update = SimpleNamespace(
            effective_chat=update.effective_chat,
            message=SimpleNamespace(text=f"/commit {command}"),
        )
        synthetic_context = SimpleNamespace(args=[], bot=context.bot)
        try:
            await self.handle_commit(synthetic_update, synthetic_context)
        finally:
            self._generated_commit_commands().pop(update.effective_chat.id, None)

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
