from __future__ import annotations

import asyncio
import html

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

from coding_agent_telegram.filters import is_valid_project_folder, resolve_project_path
from coding_agent_telegram.telegram_sender import send_html_text, send_text

from .base import logger, require_allowed_chat


class ProjectCommandMixin:
    def _branch_source_intro_lines(self, *, target_exists: bool, new_branch: str) -> list[str]:
        if target_exists:
            return [self._t(None, "project.branch_switch_requires_source", new_branch=new_branch), ""]
        return [self._t(None, "project.branch_create_from_source", new_branch=new_branch), ""]

    def _branch_source_keyboard(
        self,
        *,
        source_branch: str,
        new_branch: str,
        allow_local: bool,
        allow_origin: bool,
    ) -> InlineKeyboardMarkup:
        buttons: list[InlineKeyboardButton] = []
        if allow_local:
            buttons.append(
                InlineKeyboardButton(
                    f"local/{source_branch}",
                    callback_data=f"branchsource:local:{source_branch}:{new_branch}",
                )
            )
        if allow_origin:
            buttons.append(
                InlineKeyboardButton(
                    f"origin/{source_branch}",
                    callback_data=f"branchsource:origin:{source_branch}:{new_branch}",
                )
        )
        return InlineKeyboardMarkup([buttons])

    def _multi_branch_source_keyboard(
        self,
        *,
        new_branch: str,
        source_branches: list[str],
        project_path,
    ) -> InlineKeyboardMarkup | None:
        rows: list[list[InlineKeyboardButton]] = []
        seen: set[tuple[str, str]] = set()
        for source_branch in source_branches:
            if not source_branch:
                continue
            row: list[InlineKeyboardButton] = []
            if self.git.local_branch_exists(project_path, source_branch):
                key = ("local", source_branch)
                if key not in seen:
                    row.append(
                        InlineKeyboardButton(
                            f"local/{source_branch}",
                            callback_data=f"branchsource:local:{source_branch}:{new_branch}",
                        )
                    )
                    seen.add(key)
            if self.git.remote_branch_exists(project_path, source_branch):
                key = ("origin", source_branch)
                if key not in seen:
                    row.append(
                        InlineKeyboardButton(
                            f"origin/{source_branch}",
                            callback_data=f"branchsource:origin:{source_branch}:{new_branch}",
                        )
                    )
                    seen.add(key)
            if row:
                rows.append(row)
        if not rows:
            return None
        return InlineKeyboardMarkup(rows)

    async def _prompt_for_branch_source(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        *,
        project_folder: str,
        project_path,
        source_branch: str | None,
        new_branch: str,
        intro_lines: list[str] | None = None,
        source_branches: list[str] | None = None,
    ) -> bool:
        keyboard: InlineKeyboardMarkup | None
        if source_branches is not None:
            keyboard = self._multi_branch_source_keyboard(
                new_branch=new_branch,
                source_branches=source_branches,
                project_path=project_path,
            )
            if keyboard is None:
                joined_sources = ", ".join(branch for branch in source_branches if branch)
                await send_text(
                    update,
                    context,
                    self._t(
                        update,
                        "project.branch_source_missing",
                        project_folder=project_folder,
                        source_branch=joined_sources,
                    ),
                )
                return False
        else:
            source_branch = source_branch or ""
            allow_local = self.git.local_branch_exists(project_path, source_branch)
            allow_origin = self.git.remote_branch_exists(project_path, source_branch)
            if not allow_local and not allow_origin:
                await send_text(
                    update,
                    context,
                    self._t(
                        update,
                        "project.branch_source_missing",
                        project_folder=project_folder,
                        source_branch=source_branch,
                    ),
                )
                return False
            keyboard = self._branch_source_keyboard(
                source_branch=source_branch,
                new_branch=new_branch,
                allow_local=allow_local,
                allow_origin=allow_origin,
            )

        lines = list(intro_lines or [])
        lines.extend(
            [
                self._t(update, "project.project_label", project_folder=project_folder),
                self._t(update, "project.branch_target_label", new_branch=new_branch),
            ]
        )
        if source_branches is not None:
            current_branch = str(self.git.current_branch(project_path) or "").strip()
            default_branch = str(self.git.default_branch(project_path) or "").strip()
            if current_branch:
                lines.append(self._t(update, "project.current_branch_in_repo_label", branch_name=current_branch))
            if default_branch and default_branch != current_branch:
                lines.append(self._t(update, "project.default_branch_label", branch_name=default_branch))
        lines.extend(
            [
                "",
                self._t(update, "project.choose_branch_source"),
            ]
        )
        if update.effective_chat is not None:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="\n".join(lines),
                reply_markup=keyboard,
            )
        return True

    async def _send_branch_selection_prompt(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        *,
        project_folder: str,
        project_path,
        intro_lines: list[str] | None = None,
    ) -> None:
        refresh_result = await asyncio.to_thread(self.git.refresh_current_branch, project_path)
        if refresh_result is None:
            refresh_result = type("RefreshResult", (), {"success": True, "warnings": ()})()
        if not refresh_result.success:
            await send_text(update, context, refresh_result.message)
            return

        current_branch = self.git.current_branch(project_path) or "(unknown)"
        default_branch = self.git.default_branch(project_path) or "(unknown)"
        branches = self.git.list_local_branches(project_path)
        lines = list(intro_lines or [])
        lines.extend(
            [
                self._t(update, "project.project_label", project_folder=project_folder),
                self._t(update, "project.current_branch_in_repo_label", branch_name=current_branch),
                self._t(update, "project.default_branch_label", branch_name=default_branch),
                "",
            ]
        )
        if refresh_result.warnings:
            lines.append(self._t(update, "project.refresh_warnings"))
            for warning in refresh_result.warnings:
                lines.append(f"- {warning}")
            lines.append("")
        lines.append(self._t(update, "project.local_branches"))
        if branches:
            for branch in branches[:20]:
                marker = "*" if branch == current_branch else "-"
                annotations: list[str] = []
                if branch == default_branch:
                    annotations.append(self._t(update, "project.annotation_default"))
                if branch == current_branch:
                    annotations.append(self._t(update, "project.annotation_current_branch_in_repo"))
                suffix = f" ({', '.join(annotations)})" if annotations else ""
                lines.append(f"{marker} {branch}{suffix}")
        else:
            lines.append(f"- {self._t(update, 'project.none')}")
        lines.extend(
            [
                "",
                self._t(update, "project.select_branch_with"),
                "/branch <new_branch>",
                "/branch <origin_branch> <new_branch>",
            ]
        )
        await send_text(update, context, "\n".join(lines))

    @require_allowed_chat()
    async def handle_project(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if await self._notify_if_current_project_busy(update, context):
            return
        if len(context.args) != 1:
            await send_text(update, context, self._t(update, "project.usage_project"))
            return

        folder = context.args[0].strip()
        if not is_valid_project_folder(folder):
            await send_text(update, context, self._t(update, "project.invalid_project_folder"))
            return

        chat_id = update.effective_chat.id
        chat_state = self.deps.store.get_chat_state(self.deps.bot_id, chat_id)
        previous_project_folder = chat_state.get("current_project_folder")
        switched_project = previous_project_folder != folder
        active_session_id = chat_state.get("active_session_id")
        active_session = None
        if active_session_id:
            active_session = chat_state.get("sessions", {}).get(active_session_id)

        path = resolve_project_path(self.deps.cfg.workspace_root, folder)
        if path.exists() and not path.is_dir():
            await send_text(update, context, self._t(update, "project.path_not_directory", folder=folder))
            return
        project_created = False
        if not path.exists():
            path.mkdir(parents=True, exist_ok=True)
            self.deps.store.trust_project(folder)
            project_created = True
            logger.info("Created project folder '%s' for chat %s.", folder, update.effective_chat.id)

        self.deps.store.set_current_project_folder(self.deps.bot_id, chat_id, folder)
        is_git_repo = self.git.is_git_repo(path)
        branch_name = self.git.current_branch(path) if is_git_repo else None
        default_branch = self.git.default_branch(path) if is_git_repo else None
        if is_git_repo and switched_project:
            self.deps.store.set_current_branch(self.deps.bot_id, chat_id, None)
        else:
            self.deps.store.set_current_branch(self.deps.bot_id, chat_id, branch_name)
        logger.info("Set current project to '%s' for chat %s.", folder, chat_id)
        should_prompt_trust = not project_created and not self.deps.store.is_project_trusted(folder)
        warning_lines: list[str] = []
        if active_session and active_session.get("project_folder") != folder:
            warning_lines = [
                "",
                "",
                f"⚠️ <b>{html.escape(self._t(update, 'project.active_session_mismatch_title'))}</b>",
                self._t(update, "project.current_session_html", session_name=f"<b>{html.escape(active_session['name'])}</b>"),
                self._t(
                    update,
                    "project.session_project_html",
                    project_folder=f"<code>{html.escape(active_session['project_folder'])}</code>",
                ),
                self._t(update, "project.start_new_session_for_project_html"),
                *warning_lines,
            ]
        if is_git_repo and switched_project:
            intro_lines = [
                self._t(update, "project.project_changed_to", folder=folder),
                self._t(update, "project.branch_selection_required"),
            ]
            if active_session and active_session.get("project_folder") != folder:
                intro_lines.extend(
                    [
                        "",
                        self._t(update, "project.active_session_label", session_name=active_session["name"]),
                        self._t(update, "project.session_project_label", project_folder=active_session["project_folder"]),
                    ]
                )
            await self._send_branch_selection_prompt(
                update,
                context,
                project_folder=folder,
                project_path=path,
                intro_lines=intro_lines + [""],
            )
        elif branch_name:
            await send_html_text(
                update,
                context,
                (
                    f"✅ <b>{html.escape(self._t(update, 'project.project_set_title'))}</b>\n"
                    f"{self._t(update, 'project.project_html', project_folder=f'<code>{html.escape(folder)}</code>')}\n"
                    f"{self._t(update, 'project.current_branch_html', branch_name=f'<code>{html.escape(branch_name)}</code>')}\n\n"
                    f"{self._t(update, 'project.branch_usage_html')}\n"
                    f"{self._t(update, 'project.default_branch_behavior_html', branch_name=f'<code>{html.escape(default_branch or branch_name)}</code>')}\n"
                    f"{self._t(update, 'project.current_branch_behavior_html', branch_name=f'<code>{html.escape(branch_name)}</code>')}"
                    f"{chr(10).join(warning_lines)}"
                ),
            )
        else:
            suffix = f"\n{chr(10).join(warning_lines)}" if warning_lines else ""
            await send_html_text(
                update,
                context,
                (
                    f"✅ <b>{html.escape(self._t(update, 'project.project_set_title'))}</b>\n"
                    f"{self._t(update, 'project.project_html', project_folder=f'<code>{html.escape(folder)}</code>')}{suffix}"
                ),
            )
        if should_prompt_trust and update.effective_chat is not None:
            keyboard = InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(self._t(update, "queue.button_yes"), callback_data=f"trustproject:yes:{folder}"),
                        InlineKeyboardButton(self._t(update, "queue.button_no"), callback_data=f"trustproject:no:{folder}"),
                    ]
                ]
            )
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=self._t(update, "project.trust_prompt_html", project_folder=f"<code>{html.escape(folder)}</code>"),
                parse_mode="HTML",
                reply_markup=keyboard,
            )
        if (not is_git_repo or not switched_project) and hasattr(self, "_continue_pending_action"):
            await self._continue_pending_action(update, context)

    @require_allowed_chat(answer_callback=True)
    async def handle_trust_project_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        query = update.callback_query
        if query is None:
            return

        await query.answer()
        payload = (query.data or "").split(":", 2)
        if len(payload) != 3:
            await query.edit_message_text(self._t(update, "project.invalid_trust_decision"))
            return
        _, decision, folder = payload
        if decision not in {"yes", "no"} or not is_valid_project_folder(folder):
            await query.edit_message_text(self._t(update, "project.invalid_trust_decision"))
            return

        chat_id = update.effective_chat.id
        path = resolve_project_path(self.deps.cfg.workspace_root, folder)
        if not path.exists() or not path.is_dir():
            await query.edit_message_text(self._t(update, "project.project_folder_missing_only", project_folder=folder))
            return

        if decision == "no":
            await query.edit_message_text(self._t(update, "project.left_untrusted", folder=folder))
            return

        if self.deps.store.is_project_trusted(folder):
            await query.edit_message_text(self._t(update, "project.already_trusted", folder=folder))
            return
        self.deps.store.trust_project(folder)
        logger.info("Trusted existing project folder '%s' for chat %s via inline confirmation.", folder, chat_id)
        await query.edit_message_text(self._t(update, "project.trusted", folder=folder))

    @require_allowed_chat()
    async def handle_branch(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if await self._notify_if_current_project_busy(update, context):
            return
        chat_id = update.effective_chat.id
        chat_state = self.deps.store.get_chat_state(self.deps.bot_id, chat_id)
        project_folder = chat_state.get("current_project_folder")
        if not project_folder:
            await send_text(update, context, self._t(update, "common.no_project_selected"))
            return

        project_path = resolve_project_path(self.deps.cfg.workspace_root, project_folder)
        if not self.git.is_git_repo(project_path):
            await send_text(update, context, self._t(update, "common.current_project_not_git"))
            return

        if not context.args:
            await self._send_branch_selection_prompt(
                update,
                context,
                project_folder=project_folder,
                project_path=project_path,
            )
            return

        if len(context.args) not in {1, 2}:
            await send_text(
                update,
                context,
                self._t(update, "project.usage_branch"),
            )
            return

        if len(context.args) == 2:
            source_branch = context.args[0].strip()
            new_branch = context.args[1].strip()
            source_branches = None
        else:
            new_branch = context.args[0].strip()
            if self.git.local_branch_exists(project_path, new_branch) or self.git.remote_branch_exists(project_path, new_branch):
                source_branch = new_branch
                source_branches = None
            else:
                current_branch = str(self.git.current_branch(project_path) or "").strip()
                default_branch = str(self.git.default_branch(project_path) or "").strip()
                source_branches = [branch for branch in [current_branch, default_branch] if branch]
                source_branch = None
                if not source_branches:
                    await send_text(update, context, self._t(update, "project.default_branch_unknown"))
                    return

        target_exists = self.git.local_branch_exists(project_path, new_branch) or self.git.remote_branch_exists(project_path, new_branch)

        await self._prompt_for_branch_source(
            update,
            context,
            project_folder=project_folder,
            project_path=project_path,
            source_branch=source_branch,
            new_branch=new_branch,
            intro_lines=self._branch_source_intro_lines(target_exists=target_exists, new_branch=new_branch),
            source_branches=source_branches,
        )

    @require_allowed_chat(answer_callback=True)
    async def handle_branch_source_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        query = update.callback_query
        if query is None or query.data is None:
            return

        await query.answer()
        parts = query.data.split(":", 3)
        if len(parts) != 4:
            return
        _, source_kind, source_branch, new_branch = parts
        if source_kind not in {"local", "origin"}:
            return

        chat_id = update.effective_chat.id
        chat_state = self.deps.store.get_chat_state(self.deps.bot_id, chat_id)
        project_folder = chat_state.get("current_project_folder")
        if not project_folder:
            await query.edit_message_text(self._t(update, "common.no_project_selected"))
            return

        project_path = resolve_project_path(self.deps.cfg.workspace_root, project_folder)
        if not project_path.exists() or not project_path.is_dir():
            await query.edit_message_text(
                self._t(update, "project.project_folder_missing_retry", project_folder=project_folder)
            )
            return

        result = await asyncio.to_thread(
            self.git.prepare_branch_from_source,
            project_path,
            source_kind=source_kind,
            source_branch=source_branch,
            new_branch=new_branch,
        )
        if not result.success:
            if hasattr(self, "_offer_branch_source_fallback"):
                handled = await self._offer_branch_source_fallback(
                    query,
                    project_folder=project_folder,
                    project_path=project_path,
                    source_kind=source_kind,
                    source_branch=source_branch,
                    new_branch=new_branch,
                    error_message=result.message,
                )
                if handled:
                    return
            await query.edit_message_text(result.message)
            return

        self.deps.store.set_current_branch(self.deps.bot_id, chat_id, result.current_branch)
        self.deps.store.set_active_session_branch(self.deps.bot_id, chat_id, result.current_branch or "")
        if hasattr(self, "_pending_action") and hasattr(self, "_store_pending_action"):
            pending_action = self._pending_action(chat_id)
            if isinstance(pending_action, dict) and pending_action.get("branch_resolution"):
                pending_action = dict(pending_action)
                pending_action.pop("branch_resolution", None)
                self._store_pending_action(chat_id, pending_action)
        logger.info(
            "Prepared branch '%s' for chat %s in project '%s' from %s/%s.",
            result.current_branch,
            chat_id,
            project_folder,
            source_kind,
            source_branch,
        )
        await query.edit_message_text(
            "\n".join(
                [
                    result.message,
                    self._t(update, "project.current_branch_html", branch_name=result.current_branch),
                ]
            )
        )
        if hasattr(self, "_continue_pending_action"):
            await self._continue_pending_action(update, context)
