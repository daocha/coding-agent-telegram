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
            return [f"Switching branch to {new_branch} requires choosing a source first.", ""]
        return [f"Creating a new branch from the following branch source: {new_branch}", ""]

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

    async def _prompt_for_branch_source(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        *,
        project_folder: str,
        project_path,
        source_branch: str,
        new_branch: str,
        intro_lines: list[str] | None = None,
    ) -> bool:
        allow_local = self.git.local_branch_exists(project_path, source_branch)
        allow_origin = self.git.remote_branch_exists(project_path, source_branch)
        if not allow_local and not allow_origin:
            await send_text(
                update,
                context,
                (
                    f"Branch source not found for project '{project_folder}'.\n"
                    f"Missing local/{source_branch} and origin/{source_branch}."
                ),
            )
            return False

        lines = list(intro_lines or [])
        lines.extend(
            [
                f"Project: {project_folder}",
                f"Branch target: {new_branch}",
                "",
                "Choose the branch source:",
            ]
        )
        if update.effective_chat is not None:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="\n".join(lines),
                reply_markup=self._branch_source_keyboard(
                    source_branch=source_branch,
                    new_branch=new_branch,
                    allow_local=allow_local,
                    allow_origin=allow_origin,
                ),
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
                f"Project: {project_folder}",
                f"Current branch in repo: {current_branch}",
                f"Default branch: {default_branch}",
                "",
            ]
        )
        if refresh_result.warnings:
            lines.append("Refresh warnings:")
            for warning in refresh_result.warnings:
                lines.append(f"- {warning}")
            lines.append("")
        lines.append("Local branches:")
        if branches:
            for branch in branches[:20]:
                marker = "*" if branch == current_branch else "-"
                annotations: list[str] = []
                if branch == default_branch:
                    annotations.append("default")
                if branch == current_branch:
                    annotations.append("current branch in repo")
                suffix = f" ({', '.join(annotations)})" if annotations else ""
                lines.append(f"{marker} {branch}{suffix}")
        else:
            lines.append("- (none)")
        lines.extend(
            [
                "",
                "Select a branch with:",
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
            await send_text(update, context, "Usage: /project <project_folder>\nExample: /project backend")
            return

        folder = context.args[0].strip()
        if not is_valid_project_folder(folder):
            await send_text(update, context, "Invalid project folder. Folder name only is allowed.")
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
            await send_text(update, context, f"Project path exists but is not a directory: {folder}")
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
                "⚠️ <b>Active Session Mismatch</b>",
                f"Current session: <b>{html.escape(active_session['name'])}</b>",
                f"Session project: <code>{html.escape(active_session['project_folder'])}</code>",
                "Start a new session with <code>/new</code> if you want to work in this newly selected project.",
                *warning_lines,
            ]
        if is_git_repo and switched_project:
            intro_lines = [
                f"Project changed to: {folder}",
                "Branch selection is required before creating or continuing a session in this project.",
            ]
            if active_session and active_session.get("project_folder") != folder:
                intro_lines.extend(
                    [
                        "",
                        f"Active session: {active_session['name']}",
                        f"Session project: {active_session['project_folder']}",
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
                    f"✅ <b>Project Set</b>\n"
                    f"Project: <code>{html.escape(folder)}</code>\n"
                    f"Current branch: <code>{html.escape(branch_name)}</code>\n\n"
                    f"Use <code>/branch &lt;new_branch&gt;</code> or "
                    f"<code>/branch &lt;origin_branch&gt; &lt;new_branch&gt;</code> "
                    f"if you want a dedicated work branch.\n"
                    f"If <code>&lt;origin_branch&gt;</code> is not specified, the bot uses the default branch: "
                    f"<code>{html.escape(default_branch or branch_name)}</code>.\n"
                    f"If you do not set one, the bot will work on the current branch: "
                    f"<code>{html.escape(branch_name)}</code>"
                    f"{chr(10).join(warning_lines)}"
                ),
            )
        else:
            suffix = f"\n{chr(10).join(warning_lines)}" if warning_lines else ""
            await send_html_text(
                update,
                context,
                f"✅ <b>Project Set</b>\nProject: <code>{html.escape(folder)}</code>{suffix}",
            )
        if should_prompt_trust and update.effective_chat is not None:
            keyboard = InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton("Yes", callback_data=f"trustproject:yes:{folder}"),
                        InlineKeyboardButton("No", callback_data=f"trustproject:no:{folder}"),
                    ]
                ]
            )
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=f"Do you trust this project?\nProject: <code>{html.escape(folder)}</code>",
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
            await query.edit_message_text("Invalid trust decision.")
            return
        _, decision, folder = payload
        if decision not in {"yes", "no"} or not is_valid_project_folder(folder):
            await query.edit_message_text("Invalid trust decision.")
            return

        chat_id = update.effective_chat.id
        path = resolve_project_path(self.deps.cfg.workspace_root, folder)
        if not path.exists() or not path.is_dir():
            await query.edit_message_text(f"Project folder does not exist: {folder}")
            return

        if decision == "no":
            await query.edit_message_text(f"Project left untrusted: {folder}")
            return

        if self.deps.store.is_project_trusted(folder):
            await query.edit_message_text(f"Project is already trusted: {folder}")
            return
        self.deps.store.trust_project(folder)
        logger.info("Trusted existing project folder '%s' for chat %s via inline confirmation.", folder, chat_id)
        await query.edit_message_text(f"Project trusted: {folder}")

    @require_allowed_chat()
    async def handle_branch(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if await self._notify_if_current_project_busy(update, context):
            return
        chat_id = update.effective_chat.id
        chat_state = self.deps.store.get_chat_state(self.deps.bot_id, chat_id)
        project_folder = chat_state.get("current_project_folder")
        if not project_folder:
            await send_text(update, context, "⚠️ No project selected.\nPlease run /project <project_folder> first.")
            return

        project_path = resolve_project_path(self.deps.cfg.workspace_root, project_folder)
        if not self.git.is_git_repo(project_path):
            await send_text(update, context, "⚠️ Current project is not a git repository.")
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
                "Usage: /branch <new_branch>\nOr: /branch <origin_branch> <new_branch>",
            )
            return

        if len(context.args) == 2:
            source_branch = context.args[0].strip()
            new_branch = context.args[1].strip()
        else:
            new_branch = context.args[0].strip()
            if self.git.local_branch_exists(project_path, new_branch) or self.git.remote_branch_exists(project_path, new_branch):
                source_branch = new_branch
            else:
                source_branch = self.git.default_branch(project_path) or ""
                if not source_branch:
                    await send_text(update, context, "Could not determine the default branch for this repository.")
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
            await query.edit_message_text("No project selected.\nPlease run /project <project_folder> first.")
            return

        project_path = resolve_project_path(self.deps.cfg.workspace_root, project_folder)
        if not project_path.exists() or not project_path.is_dir():
            await query.edit_message_text(f"Project folder does not exist: {project_folder}\nRun /project {project_folder} again.")
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
        await query.edit_message_text(f"{result.message}\nCurrent branch: {result.current_branch}")
        if hasattr(self, "_continue_pending_action"):
            await self._continue_pending_action(update, context)
