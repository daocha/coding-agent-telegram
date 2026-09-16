from __future__ import annotations

import asyncio
import html
import os
import secrets
from contextlib import asynccontextmanager
from types import SimpleNamespace

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

from coding_agent_telegram.diff_utils import chunk_fenced_diff, collect_diffs, split_changed_files
from coding_agent_telegram.filters import resolve_project_path
from coding_agent_telegram.telegram_sender import send_code_block, send_html_text, send_text, split_assistant_output

from .base import require_allowed_chat


class GitCommandMixin:
    DIFF_BUTTON_PAGE_SIZE = 10
    MAX_DIFF_SNAPSHOTS = 500
    MAX_COMMIT_GENERATION_PROMPTS = 500
    MAX_GENERATED_COMMIT_COMMANDS = 500
    MAX_GIT_CONFIRMATIONS = 500
    MAX_RESET_PROMPTS = 500
    MAX_RESET_SELECTIONS = 500
    COMMIT_GENERATION_PROMPT = (
        'Execute: Analyze and compare to git HEAD, then Generate a git commit command for the files you changed in this task, with a detailed changelog-style commit message. '
        'Only include files you intentionally modified for this task. '
        'Do not include unrelated changed files. '
        'Do not include untracked files unless they were created for this task and are clearly required. '
        'Write the message as plain text: use one -m "<line>" flag per summary or bullet line (git joins multiple -m values into separate paragraphs automatically) instead of embedding literal newlines inside a single -m value. '
        'Do not use $(...), backticks, heredocs (<<EOF), printf, or echo to build the command or message — every part must be plain, directly readable text. '
        'Output only a single executable command in a fenced bash code block, in this exact form: git add <files> && git commit -m "<summary line>" -m "<detail line>" -m "<detail line>" ... '
        'If the file list is long, you may wrap it across lines with a trailing \\ for readability, but keep every -m value on its own single line.'
    )

    @staticmethod
    def _diff_button_label(index: int, path: str, *, max_name_length: int = 20) -> str:
        name = os.path.basename(path.rstrip("/")) or path
        if len(name) > max_name_length:
            name = f"{name[: max_name_length - 1]}…"
        return f"{index}. {name}"

    @staticmethod
    def _diff_display_path(path: str, *, max_length: int = 100) -> str:
        display = path.replace("\n", "\\n").replace("\r", "\\r")
        if len(display) > max_length:
            return f"{display[: max_length - 1]}…"
        return display

    def _build_diff_button_rows(
        self,
        update: Update,
        tracked_files: list[str],
        *,
        page: int,
        token: str,
        total_pages: int,
    ) -> list[list[InlineKeyboardButton]]:
        rows: list[list[InlineKeyboardButton]] = []
        page = min(max(page, 0), total_pages - 1)
        start = page * self.DIFF_BUTTON_PAGE_SIZE
        page_files = tracked_files[start : start + self.DIFF_BUTTON_PAGE_SIZE]
        for offset, path in enumerate(page_files, start=1):
            absolute_index = start + offset
            rows.append(
                [
                InlineKeyboardButton(
                    self._diff_button_label(absolute_index, path),
                    callback_data=f"diffshow:{token}:{absolute_index - 1}",
                )
                ]
            )
        nav_row: list[InlineKeyboardButton] = []
        if page > 0:
            nav_row.append(InlineKeyboardButton(self._t(update, "diff.button_prev_page"), callback_data=f"diffpage:{token}:{page - 1}"))
        if page < total_pages - 1:
            nav_row.append(InlineKeyboardButton(self._t(update, "diff.button_next_page"), callback_data=f"diffpage:{token}:{page + 1}"))
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
        token: str,
    ) -> tuple[str, InlineKeyboardMarkup | None]:
        tracked_pages = (len(tracked_files) + self.DIFF_BUTTON_PAGE_SIZE - 1) // self.DIFF_BUTTON_PAGE_SIZE
        untracked_pages = (len(untracked_files) + self.DIFF_BUTTON_PAGE_SIZE - 1) // self.DIFF_BUTTON_PAGE_SIZE
        total_pages = max(1, tracked_pages, untracked_pages)
        page = min(max(page, 0), total_pages - 1)
        start = page * self.DIFF_BUTTON_PAGE_SIZE
        page_files = tracked_files[start : start + self.DIFF_BUTTON_PAGE_SIZE]
        page_untracked_files = untracked_files[start : start + self.DIFF_BUTTON_PAGE_SIZE]
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
            lines.extend(
                f"{start + index}. {self._diff_display_path(path)}"
                for index, path in enumerate(page_files, start=1)
            )
        else:
            lines.append(f"- {self._t(update, 'diff.none')}")
        lines.extend(["", self._t(update, "diff.untracked_files")])
        if page_untracked_files:
            if len(untracked_files) > len(page_untracked_files):
                lines.append(
                    self._t(
                        update,
                        "diff.tracked_files_page_info",
                        start=start + 1,
                        end=start + len(page_untracked_files),
                        total=len(untracked_files),
                    )
                )
            lines.extend(f"- {self._diff_display_path(path)}" for path in page_untracked_files)
        else:
            lines.append(f"- {self._t(update, 'diff.none')}")
        if page_files:
            lines.extend(["", self._t(update, "diff.click_button_to_see_file_diff")])
        rows = self._build_diff_button_rows(
            update,
            tracked_files,
            page=page,
            token=token,
            total_pages=total_pages,
        )
        reply_markup = InlineKeyboardMarkup(rows) if rows else None
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

    def _generated_commit_commands(self) -> dict[str, dict[str, str]]:
        commands = getattr(self, "_chat_generated_commit_commands", None)
        if not isinstance(commands, dict):
            commands = {}
            self._chat_generated_commit_commands = commands
        return commands

    def _commit_generation_prompts(self) -> dict[str, dict[str, str]]:
        prompts = getattr(self, "_chat_commit_generation_prompts", None)
        if not isinstance(prompts, dict):
            prompts = {}
            self._chat_commit_generation_prompts = prompts
        return prompts

    def _diff_snapshots(self) -> dict[str, dict[str, object]]:
        snapshots = getattr(self, "_chat_diff_snapshots", None)
        if not isinstance(snapshots, dict):
            snapshots = {}
            self._chat_diff_snapshots = snapshots
        return snapshots

    def _git_confirmations(self) -> dict[str, dict[str, str]]:
        confirmations = getattr(self, "_chat_git_confirmations", None)
        if not isinstance(confirmations, dict):
            confirmations = {}
            self._chat_git_confirmations = confirmations
        return confirmations

    @staticmethod
    def _new_unique_token(records: dict[str, object]) -> str:
        while True:
            token = secrets.token_hex(6)
            if token not in records:
                return token

    @staticmethod
    def _escape_markdown_code_value(value: object) -> str:
        return str(value).replace("\\", "\\\\").replace("`", "\\`")

    @staticmethod
    def _store_bounded_record(records: dict[str, object], token: str, payload: object, *, limit: int) -> None:
        if len(records) >= limit:
            records.pop(next(iter(records)), None)
        records[token] = payload

    def _register_git_confirmation(
        self,
        *,
        chat_id: int,
        session: dict[str, object],
        action: str,
        branch_name: str,
        default_branch: str = "",
    ) -> str:
        chat_state = self.deps.store.get_chat_state(self.deps.bot_id, chat_id)
        confirmations = self._git_confirmations()
        token = self._new_unique_token(confirmations)
        self._store_bounded_record(
            confirmations,
            token,
            {
                "action": action,
                "chat_id": str(chat_id),
                "session_id": str(chat_state.get("active_session_id") or ""),
                "project_folder": str(session["project_folder"]),
                "branch_name": branch_name,
                "default_branch": default_branch,
            },
            limit=self.MAX_GIT_CONFIRMATIONS,
        )
        return token

    def _get_git_confirmation(self, token: str, *, chat_id: int, action: str) -> dict[str, str] | None:
        confirmation = self._git_confirmations().get(token)
        if (
            confirmation is None
            or confirmation.get("chat_id") != str(chat_id)
            or confirmation.get("action") != action
        ):
            return None
        return confirmation

    def _reset_selections(self) -> dict[str, dict[str, str]]:
        selections = getattr(self, "_chat_reset_selections", None)
        if not isinstance(selections, dict):
            selections = {}
            self._chat_reset_selections = selections
        return selections

    def _reset_prompts(self) -> dict[str, dict[str, str]]:
        prompts = getattr(self, "_chat_reset_prompts", None)
        if not isinstance(prompts, dict):
            prompts = {}
            self._chat_reset_prompts = prompts
        return prompts

    @asynccontextmanager
    async def _workspace_git_operation_lock(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        project_folder: str,
    ):
        lock = self._workspace_locks.setdefault(project_folder, asyncio.Lock())
        if lock.locked():
            await send_text(
                update,
                context,
                self._t(update, "common.project_busy", project_folder=project_folder),
            )
            yield False
            return
        async with lock:
            yield True

    def _new_reset_selection_token(self) -> str:
        selections = self._reset_selections()
        while True:
            token = secrets.token_hex(6)
            if token not in selections:
                return token

    @staticmethod
    def _reset_target(current_branch: str, default_branch: str, target_kind: str) -> tuple[str, bool] | None:
        targets = {
            "local-default": (default_branch, False),
            "origin-default": (f"origin/{default_branch}", True),
            "local-current": (current_branch, False),
            "origin-current": (f"origin/{current_branch}", True),
        }
        target = targets.get(target_kind)
        if target is None or not target[0] or target[0] == "origin/":
            return None
        return target

    async def _restore_reset_branch(
        self,
        project_path,
        branch_name: str,
    ) -> tuple[bool, str | None]:
        if self.git.current_branch(project_path) == branch_name:
            return True, None
        checkout = await asyncio.to_thread(self.git.checkout_branch, project_path, branch_name)
        if checkout.success:
            return True, None
        return False, checkout.message

    async def _warn_if_session_branch_discrepancy(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        session: dict[str, object],
        project_path,
    ) -> bool:
        session_branch = str(session.get("branch_name") or "").strip()
        checked_out_branch = str(self.git.current_branch(project_path) or "").strip()
        if not session_branch or session_branch == checked_out_branch:
            return False
        checked_out_label = checked_out_branch or self._t(update, "git.detached_head_label")
        buttons = [
            [
                InlineKeyboardButton(
                    self._t(update, "git.branch_discrepancy_switch_to_session", branch_name=session_branch),
                    callback_data="gitbranchdiscrepancy:stored",
                )
            ]
        ]
        # There is no branch that can be recorded for a detached HEAD, so only
        # offer the safe restoration action in that case.
        if checked_out_branch:
            buttons.append(
                [
                    InlineKeyboardButton(
                        self._t(update, "git.branch_discrepancy_use_current", branch_name=checked_out_branch),
                        callback_data="gitbranchdiscrepancy:current",
                    )
                ]
            )
        await send_text(
            update,
            context,
            self._t(
                update,
                "git.branch_discrepancy_warning",
                session_branch=session_branch,
                checked_out_branch=checked_out_label,
            ),
            reply_markup=InlineKeyboardMarkup(buttons),
        )
        return True

    @require_allowed_chat(answer_callback=True)
    async def handle_git_branch_discrepancy_callback(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """Resolve a discrepancy reported by a Git command via the /branch path."""
        query = update.callback_query
        if query is None or query.data is None:
            return
        await query.answer()

        choice = query.data.partition("gitbranchdiscrepancy:")[2]
        if choice not in {"stored", "current"}:
            return

        chat_id = update.effective_chat.id
        chat_state = self.deps.store.get_chat_state(self.deps.bot_id, chat_id)
        active_session_id = chat_state.get("active_session_id")
        session = chat_state.get("sessions", {}).get(active_session_id) if active_session_id else None
        if not isinstance(session, dict):
            await query.edit_message_text(self._t(update, "branch_resolution.no_active_session"))
            return

        project_folder = str(session.get("project_folder") or "").strip()
        project_path = resolve_project_path(self.deps.cfg.workspace_root, project_folder)
        if not project_path.exists() or not project_path.is_dir():
            await query.edit_message_text(
                self._t(update, "project.project_folder_missing_retry", project_folder=project_folder)
            )
            return
        if self._is_project_busy(chat_id):
            await query.edit_message_text(self._t(update, "common.project_busy", project_folder=project_folder))
            return

        stored_branch = str(session.get("branch_name") or "").strip()
        current_branch = str(self.git.current_branch(project_path) or "").strip()
        target_branch = stored_branch if choice == "stored" else current_branch
        if not target_branch:
            await query.edit_message_text(self._t(update, "git.branch_unknown"))
            return

        # This is the operation performed by /branch <target_branch>: prefer a
        # local branch, otherwise prepare the matching origin branch.
        source_kind = "local" if self.git.local_branch_exists(project_path, target_branch) else "origin"
        result = await asyncio.to_thread(
            self.git.prepare_branch_from_source,
            project_path,
            source_kind=source_kind,
            source_branch=target_branch,
            new_branch=target_branch,
        )
        if not result.success:
            await query.edit_message_text(result.message)
            return

        self.deps.store.set_current_branch(self.deps.bot_id, chat_id, result.current_branch)
        self.deps.store.set_active_session_branch(self.deps.bot_id, chat_id, result.current_branch or "")
        await query.edit_message_text(
            "\n".join(
                [
                    result.message,
                    self._t(update, "project.current_branch_html", branch_name=result.current_branch),
                ]
            )
        )

    async def _execute_confirmed_reset(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        query,
        selection: dict[str, str],
        project_path,
    ) -> None:
        target_ref = selection["target_ref"]
        if selection["is_origin"] == "True":
            await query.edit_message_text(
                self._t(update, "git.reset_pull_in_progress", target_ref=self._escape_markdown_code_value(target_ref)),
                parse_mode="Markdown",
            )
            ok, message, warnings = await self._refresh_branch_with_checkout(
                update,
                context,
                project_path=project_path,
                branch_name=selection["target_branch"],
            )
            restored, restore_message = await self._restore_reset_branch(project_path, selection["reset_branch"])
            if not restored:
                await send_text(update, context, restore_message or self._t(update, "bot.error.command_failed"))
                return
            if not ok:
                await send_text(update, context, message or self._t(update, "bot.error.command_failed"))
                return
            if warnings:
                await send_text(update, context, "\n".join([self._t(update, "project.refresh_warnings"), *[f"- {warning}" for warning in warnings]]))
                return
        else:
            restored, restore_message = await self._restore_reset_branch(project_path, selection["reset_branch"])
            if not restored:
                await query.edit_message_text(restore_message or self._t(update, "bot.error.command_failed"))
                return

        await query.edit_message_text(
            self._t(update, "git.reset_in_progress", target_ref=self._escape_markdown_code_value(target_ref)),
            parse_mode="Markdown",
        )
        result = await asyncio.to_thread(self.git.run_git_command, project_path, ["reset", "--hard", target_ref])
        await send_html_text(
            update,
            context,
            self._bash_block(self._format_git_response([(["reset", "--hard", target_ref], result)], [])),
        )

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
            if await self._warn_if_session_branch_discrepancy(update, context, session, project_path):
                return
            chat_state = self.deps.store.get_chat_state(self.deps.bot_id, update.effective_chat.id)
            prompts = self._commit_generation_prompts()
            token = self._new_unique_token(prompts)
            self._store_bounded_record(
                prompts,
                token,
                {
                    "chat_id": str(update.effective_chat.id),
                    "session_id": str(chat_state.get("active_session_id") or ""),
                    "project_folder": str(session["project_folder"]),
                    "branch_name": str(session.get("branch_name") or self.git.current_branch(project_path) or ""),
                },
                limit=self.MAX_COMMIT_GENERATION_PROMPTS,
            )
            confirm_markup = InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            self._t(update, "git.commit_generate_button"),
                            callback_data=f"commitgen:confirm:{token}",
                            **self._affirmative_inline_button_kwargs(),
                        ),
                        InlineKeyboardButton(
                            self._t(update, "git.cancel_button"),
                            callback_data=f"commitgen:cancel:{token}",
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
        if await self._warn_if_session_branch_discrepancy(update, context, session, project_path):
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

        async with self._workspace_git_operation_lock(
            update,
            context,
            str(session["project_folder"]),
        ) as acquired:
            if not acquired:
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
        if await self._warn_if_session_branch_discrepancy(update, context, session, project_path):
            return

        branch_name = session.get("branch_name") or self.git.current_branch(project_path) or self._t(
            update,
            "status.current_branch_placeholder",
        )
        tracked_files, untracked_files = split_changed_files(project_path)
        chat_state = self.deps.store.get_chat_state(self.deps.bot_id, update.effective_chat.id)
        snapshots = self._diff_snapshots()
        token = self._new_unique_token(snapshots)
        self._store_bounded_record(
            snapshots,
            token,
            {
                "chat_id": str(update.effective_chat.id),
                "session_id": str(chat_state.get("active_session_id") or ""),
                "project_folder": str(session["project_folder"]),
                "branch_name": str(branch_name),
                "tracked_files": tuple(tracked_files),
                "untracked_files": tuple(untracked_files),
            },
            limit=self.MAX_DIFF_SNAPSHOTS,
        )
        text, reply_markup = self._build_diff_message(
            update,
            session,
            branch_name=branch_name,
            tracked_files=tracked_files,
            untracked_files=untracked_files,
            page=0,
            token=token,
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
        parts = data.split(":")
        if len(parts) != 3:
            return
        action, token, raw_index = parts
        snapshot = self._diff_snapshots().get(token)
        if snapshot is None or snapshot.get("chat_id") != str(update.effective_chat.id):
            await query.edit_message_text(self._t(update, "common.button_expired"))
            return
        try:
            index = int(raw_index)
        except ValueError:
            return

        session, project_path = await self._active_session_project_or_notify(
            update,
            context,
            require_git_repo=True,
        )
        if session is None or project_path is None:
            return
        chat_state = self.deps.store.get_chat_state(self.deps.bot_id, update.effective_chat.id)
        active_branch = str(session.get("branch_name") or self.git.current_branch(project_path) or "").strip()
        if (
            str(chat_state.get("active_session_id") or "") != snapshot.get("session_id")
            or str(session["project_folder"]) != snapshot.get("project_folder")
            or active_branch != snapshot.get("branch_name")
        ):
            await query.edit_message_text(self._t(update, "common.button_expired"))
            return
        if await self._warn_if_session_branch_discrepancy(update, context, session, project_path):
            return

        tracked_files = list(snapshot.get("tracked_files") or ())
        untracked_files = list(snapshot.get("untracked_files") or ())
        if action == "diffpage":
            branch_name = session.get("branch_name") or self.git.current_branch(project_path) or self._t(
                update,
                "status.current_branch_placeholder",
            )
            text, reply_markup = self._build_diff_message(
                update,
                session,
                branch_name=branch_name,
                tracked_files=tracked_files,
                untracked_files=untracked_files,
                page=index,
                token=token,
            )
            await query.edit_message_text(
                text=html.escape(text),
                parse_mode="HTML",
                reply_markup=reply_markup,
            )
            return
        if action != "diffshow":
            return
        if index < 0 or index >= len(tracked_files):
            await send_text(update, context, self._t(update, "diff.none"))
            return

        file_path = tracked_files[index]
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
        parts = action.split(":")
        if len(parts) != 3 or parts[0] != "commitgen" or parts[1] not in {"confirm", "cancel"}:
            return
        _, choice, token = parts
        prompt = self._commit_generation_prompts().get(token)
        if prompt is None or prompt.get("chat_id") != str(update.effective_chat.id):
            await query.edit_message_text(self._t(update, "common.button_expired"))
            return
        if choice == "cancel":
            self._commit_generation_prompts().pop(token, None)
            await query.edit_message_text(self._t(update, "git.commit_generate_cancelled"))
            return
        if await self._notify_if_current_project_busy(update, context):
            return

        session, project_path = await self._active_session_project_or_notify(
            update,
            context,
            require_git_repo=True,
        )
        if session is None or project_path is None:
            return
        chat_state = self.deps.store.get_chat_state(self.deps.bot_id, update.effective_chat.id)
        active_session_id = str(chat_state.get("active_session_id") or "").strip()
        active_branch = str(session.get("branch_name") or self.git.current_branch(project_path) or "").strip()
        if (
            active_session_id != prompt["session_id"]
            or str(session["project_folder"]) != prompt["project_folder"]
            or active_branch != prompt["branch_name"]
        ):
            self._commit_generation_prompts().pop(token, None)
            await query.edit_message_text(self._t(update, "git.commit_execute_context_changed"))
            return
        if await self._warn_if_session_branch_discrepancy(update, context, session, project_path):
            return
        self._commit_generation_prompts().pop(token, None)

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
        generated_branch = str(session.get("branch_name") or self.git.current_branch(project_path) or "").strip()
        if (
            active_session_id != prompt["session_id"]
            or str(session.get("project_folder") or "") != prompt["project_folder"]
            or generated_branch != prompt["branch_name"]
        ):
            await query.edit_message_text(self._t(update, "git.commit_execute_context_changed"))
            return
        commands = self._generated_commit_commands()
        command_token = self._new_unique_token(commands)
        self._store_bounded_record(
            commands,
            command_token,
            {
                "chat_id": str(update.effective_chat.id),
                "command": generated_command,
                "session_id": active_session_id,
                "project_folder": str(session.get("project_folder") or ""),
                "branch_name": generated_branch,
            },
            limit=self.MAX_GENERATED_COMMIT_COMMANDS,
        )
        execute_markup = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        self._t(update, "git.commit_execute_button"),
                        callback_data=f"commitexec:confirm:{command_token}",
                        **self._affirmative_inline_button_kwargs(),
                    ),
                    InlineKeyboardButton(
                        self._t(update, "git.cancel_button"),
                        callback_data=f"commitexec:cancel:{command_token}",
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
        if await self._warn_if_session_branch_discrepancy(update, context, session, project_path):
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
        parts = action.split(":")
        if len(parts) != 3 or parts[0] != "commitexec" or parts[1] not in {"confirm", "cancel"}:
            return
        _, choice, token = parts
        payload = self._generated_commit_commands().get(token)
        if payload is None or payload.get("chat_id") != str(update.effective_chat.id):
            await query.edit_message_text(self._t(update, "common.button_expired"))
            return
        if choice == "cancel":
            self._generated_commit_commands().pop(token, None)
            await query.edit_message_text(self._t(update, "git.commit_generate_cancelled"))
            return
        if await self._notify_if_current_project_busy(update, context):
            return
        active_session, active_project_path = await self._active_session_project_or_notify(
            update,
            context,
            require_git_repo=True,
        )
        if active_session is None or active_project_path is None:
            return
        chat_state = self.deps.store.get_chat_state(self.deps.bot_id, update.effective_chat.id)
        active_session_id = str(chat_state.get("active_session_id") or "").strip()
        active_project_folder = str(active_session.get("project_folder") or "")
        active_branch = str(active_session.get("branch_name") or self.git.current_branch(active_project_path) or "").strip()
        if (
            active_session_id != str(payload.get("session_id") or "")
            or active_project_folder != str(payload.get("project_folder") or "")
            or active_branch != str(payload.get("branch_name") or "")
        ):
            self._generated_commit_commands().pop(token, None)
            await query.edit_message_text(self._t(update, "git.commit_execute_context_changed"))
            return
        if await self._warn_if_session_branch_discrepancy(
            update,
            context,
            active_session,
            active_project_path,
        ):
            return
        command = str(payload.get("command") or "").strip()
        if not command:
            self._generated_commit_commands().pop(token, None)
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
            self._generated_commit_commands().pop(token, None)

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
        if await self._warn_if_session_branch_discrepancy(update, context, session, project_path):
            return

        branch_name = session.get("branch_name") or self.git.current_branch(project_path)
        if not branch_name:
            await send_text(update, context, self._t(update, "git.branch_unknown"))
            return
        token = self._register_git_confirmation(
            chat_id=update.effective_chat.id,
            session=session,
            action="push",
            branch_name=str(branch_name),
        )

        confirm_markup = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        self._t(update, "git.push_confirm_button"),
                        callback_data=f"push:confirm:{token}",
                        **self._affirmative_inline_button_kwargs(),
                    ),
                    InlineKeyboardButton(
                        self._t(update, "git.cancel_button"),
                        callback_data=f"push:cancel:{token}",
                        **self._negative_inline_button_kwargs(),
                    ),
                ]
            ]
        )
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=self._t(update, "git.push_confirm_prompt", branch_name=self._escape_markdown_code_value(branch_name)),
            parse_mode="Markdown",
            reply_markup=confirm_markup,
        )

    @require_allowed_chat()
    async def handle_log(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if await self._notify_if_current_project_busy(update, context):
            return
        if context.args:
            await send_text(update, context, self._t(update, "git.usage_log"))
            return

        session, project_path = await self._active_session_project_or_notify(
            update,
            context,
            require_git_repo=True,
        )
        if session is None or project_path is None:
            return
        if await self._warn_if_session_branch_discrepancy(update, context, session, project_path):
            return

        result = await asyncio.to_thread(self.git.run_git_command, project_path, ["log", "-5", "--oneline"])
        await send_html_text(
            update,
            context,
            self._bash_block(self._format_git_response([(["log", "-5", "--oneline"], result)], [])),
        )

    @require_allowed_chat()
    async def handle_reset(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if await self._notify_if_current_project_busy(update, context):
            return
        if context.args:
            await send_text(update, context, self._t(update, "git.usage_reset"))
            return

        session, project_path = await self._active_session_project_or_notify(
            update,
            context,
            require_git_repo=True,
        )
        if session is None or project_path is None:
            return
        if await self._warn_if_session_branch_discrepancy(update, context, session, project_path):
            return
        if not self.deps.store.is_project_trusted(session["project_folder"]):
            await send_text(update, context, self._t(update, "git.project_not_trusted_for_mutation"))
            return

        current_branch = str(session.get("branch_name") or self.git.current_branch(project_path) or "").strip()
        default_branch = str(self.git.default_branch(project_path) or current_branch).strip()
        if not current_branch or not default_branch:
            await send_text(update, context, self._t(update, "git.branch_unknown"))
            return

        chat_state = self.deps.store.get_chat_state(self.deps.bot_id, update.effective_chat.id)
        prompts = self._reset_prompts()
        token = self._new_unique_token(prompts)
        self._store_bounded_record(
            prompts,
            token,
            {
                "chat_id": str(update.effective_chat.id),
                "session_id": str(chat_state.get("active_session_id") or ""),
                "project_folder": str(session["project_folder"]),
                "current_branch": current_branch,
                "default_branch": default_branch,
            },
            limit=self.MAX_RESET_PROMPTS,
        )

        rows = [
            [InlineKeyboardButton(f"local/{default_branch}", callback_data=f"reset:select:{token}:local-default")],
            [InlineKeyboardButton(f"origin/{default_branch}", callback_data=f"reset:select:{token}:origin-default")],
            [InlineKeyboardButton(f"local/{current_branch}", callback_data=f"reset:select:{token}:local-current")],
            [InlineKeyboardButton(f"origin/{current_branch}", callback_data=f"reset:select:{token}:origin-current")],
        ]
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=self._t(update, "git.reset_select_prompt"),
            reply_markup=InlineKeyboardMarkup(rows),
        )

    @require_allowed_chat(answer_callback=True)
    async def handle_reset_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        query = update.callback_query
        if query is None:
            return

        await query.answer()

        action = (query.data or "").strip()
        if action.startswith("reset:select:"):
            if await self._notify_if_current_project_busy(update, context):
                return
            parts = action.split(":")
            if len(parts) != 4:
                return
            _, _, token, target_kind = parts
            prompt = self._reset_prompts().get(token)
            if prompt is None or prompt.get("chat_id") != str(update.effective_chat.id):
                await query.edit_message_text(self._t(update, "common.button_expired"))
                return
            session, project_path = await self._active_session_project_or_notify(
                update,
                context,
                require_git_repo=True,
            )
            if session is None or project_path is None:
                return
            chat_state = self.deps.store.get_chat_state(self.deps.bot_id, update.effective_chat.id)
            if (
                str(chat_state.get("active_session_id") or "") != prompt["session_id"]
                or str(session["project_folder"]) != prompt["project_folder"]
                or str(session.get("branch_name") or self.git.current_branch(project_path) or "").strip()
                != prompt["current_branch"]
            ):
                self._reset_prompts().pop(token, None)
                await query.edit_message_text(self._t(update, "common.button_expired"))
                return
            if await self._warn_if_session_branch_discrepancy(update, context, session, project_path):
                return
            if not self.deps.store.is_project_trusted(session["project_folder"]):
                await query.edit_message_text(self._t(update, "git.project_not_trusted_for_mutation"))
                return
            target = self._reset_target(prompt["current_branch"], prompt["default_branch"], target_kind)
            if target is None:
                await query.edit_message_text(self._t(update, "git.branch_unknown"))
                return
            target_ref, is_origin = target
            reset_branch = prompt["current_branch"]
            if not reset_branch:
                await query.edit_message_text(self._t(update, "git.branch_unknown"))
                return
            self._reset_prompts().pop(token, None)
            token = self._new_reset_selection_token()
            selections = self._reset_selections()
            self._store_bounded_record(
                selections,
                token,
                {
                    "chat_id": str(update.effective_chat.id),
                    "session_id": str(chat_state.get("active_session_id") or ""),
                    "project_folder": str(session["project_folder"]),
                    "reset_branch": reset_branch,
                    "target_ref": target_ref,
                    "target_branch": target_ref.removeprefix("origin/") if is_origin else target_ref,
                    "is_origin": str(is_origin),
                },
                limit=self.MAX_RESET_SELECTIONS,
            )
            markup = InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            self._t(update, "git.reset_confirm_button"),
                            callback_data=f"reset:confirm:{token}",
                            **self._affirmative_inline_button_kwargs(),
                        ),
                        InlineKeyboardButton(
                            self._t(update, "git.cancel_button"),
                            callback_data=f"reset:cancel:{token}",
                            **self._negative_inline_button_kwargs(),
                        ),
                    ]
                ]
            )
            await query.edit_message_text(
                self._t(update, "git.reset_confirm_prompt", target_ref=self._escape_markdown_code_value(target_ref)),
                parse_mode="Markdown",
                reply_markup=markup,
            )
            return

        if action.startswith("reset:cancel:"):
            token = action.removeprefix("reset:cancel:")
            selection = self._reset_selections().get(token)
            if selection is None or selection.get("chat_id") != str(update.effective_chat.id):
                await query.edit_message_text(self._t(update, "common.button_expired"))
                return
            self._reset_selections().pop(token, None)
            await query.edit_message_text(self._t(update, "git.reset_cancelled"))
            return
        if not action.startswith("reset:confirm:"):
            return

        token = action.removeprefix("reset:confirm:")
        selection = self._reset_selections().get(token)
        if selection is None or selection.get("chat_id") != str(update.effective_chat.id):
            await query.edit_message_text(self._t(update, "common.button_expired"))
            return
        if await self._notify_if_current_project_busy(update, context):
            return
        session, project_path = await self._active_session_project_or_notify(
            update,
            context,
            require_git_repo=True,
        )
        if session is None or project_path is None:
            return
        chat_state = self.deps.store.get_chat_state(self.deps.bot_id, update.effective_chat.id)
        if (
            str(chat_state.get("active_session_id") or "") != selection["session_id"]
            or str(session["project_folder"]) != selection["project_folder"]
            or str(session.get("branch_name") or self.git.current_branch(project_path) or "").strip()
            != selection["reset_branch"]
        ):
            self._reset_selections().pop(token, None)
            await query.edit_message_text(self._t(update, "common.button_expired"))
            return
        if await self._warn_if_session_branch_discrepancy(update, context, session, project_path):
            return
        if not self.deps.store.is_project_trusted(session["project_folder"]):
            await query.edit_message_text(self._t(update, "git.project_not_trusted_for_mutation"))
            return
        async with self._workspace_git_operation_lock(
            update,
            context,
            selection["project_folder"],
        ) as acquired:
            if not acquired:
                return
            selection = self._reset_selections().pop(token, None)
            if selection is None:
                await query.edit_message_text(self._t(update, "common.button_expired"))
                return
            await self._execute_confirmed_reset(update, context, query, selection, project_path)

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
        if await self._warn_if_session_branch_discrepancy(update, context, session, project_path):
            return

        branch_name = session.get("branch_name") or self.git.current_branch(project_path)
        if not branch_name:
            await send_text(update, context, self._t(update, "git.branch_unknown"))
            return

        default_branch = self.git.default_branch(project_path) or branch_name
        token = self._register_git_confirmation(
            chat_id=update.effective_chat.id,
            session=session,
            action="pull",
            branch_name=str(branch_name),
            default_branch=str(default_branch),
        )
        prompt_key = "git.pull_confirm_prompt_with_default" if default_branch and default_branch != branch_name else "git.pull_confirm_prompt"

        confirm_markup = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        self._t(update, "git.pull_confirm_button"),
                        callback_data=f"pull:confirm:{token}",
                        **self._affirmative_inline_button_kwargs(),
                    ),
                    InlineKeyboardButton(
                        self._t(update, "git.cancel_button"),
                        callback_data=f"pull:cancel:{token}",
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
                branch_name=self._escape_markdown_code_value(branch_name),
                default_branch=self._escape_markdown_code_value(default_branch),
            ),
            parse_mode="Markdown",
            reply_markup=confirm_markup,
        )

    @require_allowed_chat(answer_callback=True)
    async def handle_pull_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        query = update.callback_query
        if query is None:
            return

        await query.answer()

        action = (query.data or "").strip()
        parts = action.split(":")
        if len(parts) != 3 or parts[0] != "pull" or parts[1] not in {"confirm", "cancel"}:
            return
        _, choice, token = parts
        confirmation = self._get_git_confirmation(token, chat_id=update.effective_chat.id, action="pull")
        if confirmation is None:
            await query.edit_message_text(self._t(update, "common.button_expired"))
            return
        if choice == "cancel":
            self._git_confirmations().pop(token, None)
            await query.edit_message_text(self._t(update, "git.pull_cancelled"))
            return
        if await self._notify_if_current_project_busy(update, context):
            return

        session, project_path = await self._active_session_project_or_notify(
            update,
            context,
            require_git_repo=True,
        )
        if session is None or project_path is None:
            return
        chat_state = self.deps.store.get_chat_state(self.deps.bot_id, update.effective_chat.id)
        if (
            str(chat_state.get("active_session_id") or "") != confirmation["session_id"]
            or str(session["project_folder"]) != confirmation["project_folder"]
            or str(session.get("branch_name") or self.git.current_branch(project_path) or "").strip()
            != confirmation["branch_name"]
        ):
            self._git_confirmations().pop(token, None)
            await query.edit_message_text(self._t(update, "common.button_expired"))
            return
        if await self._warn_if_session_branch_discrepancy(update, context, session, project_path):
            return
        async with self._workspace_git_operation_lock(
            update,
            context,
            confirmation["project_folder"],
        ) as acquired:
            if not acquired:
                return
            confirmation = self._git_confirmations().pop(token, None)
            if confirmation is None:
                await query.edit_message_text(self._t(update, "common.button_expired"))
                return

            branch_name = confirmation["branch_name"]
            if not branch_name:
                await query.edit_message_text(self._t(update, "git.branch_unknown"))
                return

            default_branch = confirmation["default_branch"] or branch_name
            prompt_key = "git.pull_in_progress_with_default" if default_branch and default_branch != branch_name else "git.pull_in_progress"
            await query.edit_message_text(
                self._t(
                    update,
                    prompt_key,
                    branch_name=self._escape_markdown_code_value(branch_name),
                    default_branch=self._escape_markdown_code_value(default_branch),
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
                if message and not branch_warnings:
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
            if message and not branch_warnings:
                completed_messages.append(message)
            warnings.extend(branch_warnings)

            lines = list(completed_messages)
            if not lines and not warnings:
                lines.append(self._t(update, "git.pull_completed"))
            if warnings:
                if lines:
                    lines.append("")
                lines.append(self._t(update, "project.refresh_warnings"))
                lines.extend(f"- {warning}" for warning in warnings)
            await send_text(update, context, "\n".join(lines))

    @require_allowed_chat(answer_callback=True)
    async def handle_push_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        query = update.callback_query
        if query is None:
            return

        await query.answer()

        action = (query.data or "").strip()
        parts = action.split(":")
        if len(parts) != 3 or parts[0] != "push" or parts[1] not in {"confirm", "cancel"}:
            return
        _, choice, token = parts
        confirmation = self._get_git_confirmation(token, chat_id=update.effective_chat.id, action="push")
        if confirmation is None:
            await query.edit_message_text(self._t(update, "common.button_expired"))
            return
        if choice == "cancel":
            self._git_confirmations().pop(token, None)
            await query.edit_message_text(self._t(update, "git.push_cancelled"))
            return
        if await self._notify_if_current_project_busy(update, context):
            return

        session, project_path = await self._active_session_project_or_notify(
            update,
            context,
            require_git_repo=True,
        )
        if session is None or project_path is None:
            return
        chat_state = self.deps.store.get_chat_state(self.deps.bot_id, update.effective_chat.id)
        if (
            str(chat_state.get("active_session_id") or "") != confirmation["session_id"]
            or str(session["project_folder"]) != confirmation["project_folder"]
            or str(session.get("branch_name") or self.git.current_branch(project_path) or "").strip()
            != confirmation["branch_name"]
        ):
            self._git_confirmations().pop(token, None)
            await query.edit_message_text(self._t(update, "common.button_expired"))
            return
        if await self._warn_if_session_branch_discrepancy(update, context, session, project_path):
            return
        async with self._workspace_git_operation_lock(
            update,
            context,
            confirmation["project_folder"],
        ) as acquired:
            if not acquired:
                return
            confirmation = self._git_confirmations().pop(token, None)
            if confirmation is None:
                await query.edit_message_text(self._t(update, "common.button_expired"))
                return

            branch_name = confirmation["branch_name"]
            if not branch_name:
                await query.edit_message_text(self._t(update, "git.branch_unknown"))
                return

            current_branch = self.git.current_branch(project_path)
            if current_branch != branch_name:
                checkout = await asyncio.to_thread(self.git.checkout_branch, project_path, branch_name)
                if not checkout.success:
                    await query.edit_message_text(
                        self._t(
                            update,
                            "git.push_cancelled_checkout_failed",
                            branch_name=self._escape_markdown_code_value(branch_name),
                        ),
                        parse_mode="Markdown",
                    )
                    await send_html_text(update, context, self._bash_block(self._format_git_response([(["checkout", branch_name], checkout)], [])))
                    return

            await query.edit_message_text(
                self._t(update, "git.push_in_progress", branch_name=self._escape_markdown_code_value(branch_name)),
                parse_mode="Markdown",
            )
            result = await asyncio.to_thread(self.git.push_branch, project_path, branch_name)
            await send_html_text(
                update,
                context,
                self._bash_block(self._format_git_response([(["push", "origin", branch_name], result)], [])),
            )
