from __future__ import annotations

import asyncio
import html
import logging
from dataclasses import dataclass
from typing import Optional, Tuple

from telegram import Update
from telegram.constants import ChatAction
from telegram.ext import ContextTypes

from coding_agent_telegram.agent_runner import MultiAgentRunner
from coding_agent_telegram.config import AppConfig
from coding_agent_telegram.filters import is_valid_project_folder, resolve_project_path
from coding_agent_telegram.git_utils import GitWorkspaceManager
from coding_agent_telegram.session_store import SessionStore
from coding_agent_telegram.session_runtime import PhotoAttachmentStore, SessionRuntime
from coding_agent_telegram.telegram_sender import send_html_text, send_text


logger = logging.getLogger(__name__)


@dataclass
class RouterDeps:
    cfg: AppConfig
    store: SessionStore
    agent_runner: MultiAgentRunner
    bot_id: str


class CommandRouter:
    SWITCH_PAGE_SIZE = 10

    def __init__(self, deps: RouterDeps) -> None:
        self.deps = deps
        self.git = GitWorkspaceManager()
        self.photo_attachments = PhotoAttachmentStore(deps.cfg.workspace_root)
        self.runtime = SessionRuntime(
            cfg=deps.cfg,
            store=deps.store,
            agent_runner=deps.agent_runner,
            bot_id=deps.bot_id,
            git=self.git,
            run_with_typing=self._run_with_typing,
        )

    def _sorted_sessions(self, sessions: dict[str, dict[str, str]]) -> list[tuple[str, dict[str, str]]]:
        return sorted(
            sessions.items(),
            key=lambda item: (item[1].get("updated_at") or item[1].get("created_at") or "", item[0]),
            reverse=True,
        )

    def _build_switch_page(
        self,
        sessions: dict[str, dict[str, str]],
        active_session_id: Optional[str],
        page: int,
    ) -> str:
        sorted_sessions = self._sorted_sessions(sessions)
        total_sessions = len(sorted_sessions)
        total_pages = max(1, (total_sessions + self.SWITCH_PAGE_SIZE - 1) // self.SWITCH_PAGE_SIZE)
        page = min(max(page, 1), total_pages)

        start = (page - 1) * self.SWITCH_PAGE_SIZE
        page_items = sorted_sessions[start : start + self.SWITCH_PAGE_SIZE]

        lines = [f"Available sessions (page {page}/{total_pages}):", ""]
        for idx, (sid, data) in enumerate(page_items, start=start + 1):
            status = "active" if sid == active_session_id else "idle"
            branch_name = data.get("branch_name") or "(current branch)"
            lines.append(
                f"{idx}. {html.escape(data['name'])} | <code>{html.escape(data['project_folder'])}</code> &lt;{html.escape(branch_name)}&gt; | {html.escape(data.get('provider', 'codex'))} | {status}"
            )
            lines.append(f"session_id: {sid}")
            lines.append("")

        lines.extend(
            [
                "Use:",
                "/switch &lt;session_id&gt;",
                f"/switch page {page}",
            ]
        )
        if total_pages > 1:
            lines.append(f"Pages: /switch page 1 ... /switch page {total_pages}")

        return "\n".join(lines).strip()

    async def _run_with_typing(self, update: Update, context: ContextTypes.DEFAULT_TYPE, fn, *args, **kwargs):
        chat = update.effective_chat
        if chat is None:
            return await asyncio.to_thread(fn, *args, **kwargs)

        stop_event = asyncio.Event()
        await context.bot.send_chat_action(chat_id=chat.id, action=ChatAction.TYPING)

        async def typing_loop() -> None:
            while not stop_event.is_set():
                await context.bot.send_chat_action(chat_id=chat.id, action=ChatAction.TYPING)
                try:
                    await asyncio.wait_for(stop_event.wait(), timeout=4)
                except asyncio.TimeoutError:
                    continue

        typing_task = asyncio.create_task(typing_loop())
        try:
            return await asyncio.to_thread(fn, *args, **kwargs)
        finally:
            stop_event.set()
            await typing_task


    def _chat_allowed(self, update: Update) -> Tuple[bool, Optional[str]]:
        chat = update.effective_chat
        if chat is None:
            return False, "Chat is not available."
        if chat.id not in self.deps.cfg.allowed_chat_ids:
            return False, "This chat is not allowed."
        if not self.deps.cfg.enable_group_chats and chat.type != "private":
            return False, "Group chats are not supported."
        return True, None

    async def handle_project(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        allowed, reason = self._chat_allowed(update)
        if not allowed:
            await send_text(update, context, reason)
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
        active_session_id = chat_state.get("active_session_id")
        active_session = None
        if active_session_id:
            active_session = chat_state.get("sessions", {}).get(active_session_id)

        path = resolve_project_path(self.deps.cfg.workspace_root, folder)
        if path.exists() and not path.is_dir():
            await send_text(update, context, f"Project path exists but is not a directory: {folder}")
            return
        if not path.exists():
            path.mkdir(parents=True, exist_ok=True)
            self.deps.store.trust_project(folder)
            logger.info("Created project folder '%s' for chat %s.", folder, update.effective_chat.id)

        self.deps.store.set_current_project_folder(self.deps.bot_id, chat_id, folder)
        branch_name = self.git.current_branch(path) if self.git.is_git_repo(path) else None
        self.deps.store.set_current_branch(self.deps.bot_id, chat_id, branch_name)
        logger.info("Set current project to '%s' for chat %s.", folder, chat_id)
        warning_lines: list[str] = []
        if active_session and active_session.get("project_folder") != folder:
            warning_lines = [
                "",
                "",
                "⚠️ <b>Active Session Mismatch</b>",
                f"Current session: <b>{html.escape(active_session['name'])}</b>",
                f"Session project: <code>{html.escape(active_session['project_folder'])}</code>",
                "Start a new session with <code>/new</code> if you want to work in this newly selected project.",
            ]
        if branch_name:
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

    async def handle_branch(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        allowed, reason = self._chat_allowed(update)
        if not allowed:
            await send_text(update, context, reason)
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
            refresh_result = await asyncio.to_thread(self.git.refresh_current_branch, project_path)
            if not refresh_result.success:
                await send_text(update, context, refresh_result.message)
                return
            current_branch = self.git.current_branch(project_path) or "(unknown)"
            default_branch = self.git.default_branch(project_path) or "(unknown)"
            branches = self.git.list_local_branches(project_path)
            lines = [
                f"Project: {project_folder}",
                f"Current branch: {current_branch}",
                f"Default branch: {default_branch}",
                "",
            ]
            if refresh_result.warnings:
                lines.append("Refresh warnings:")
                for warning in refresh_result.warnings:
                    lines.append(f"- {warning}")
                lines.append("")
            lines.extend(
                [
                "Local branches:",
                ]
            )
            if branches:
                for branch in branches[:20]:
                    marker = "*" if branch == current_branch else "-"
                    lines.append(f"{marker} {branch}")
            else:
                lines.append("- (none)")
            lines.extend(
                [
                    "",
                    "Use:",
                    "/branch <new_branch>",
                    "/branch <origin_branch> <new_branch>",
                ]
            )
            await send_text(update, context, "\n".join(lines))
            return

        if len(context.args) not in {1, 2}:
            await send_text(
                update,
                context,
                "Usage: /branch <new_branch>\nOr: /branch <origin_branch> <new_branch>",
            )
            return

        origin_branch = None
        new_branch = context.args[0].strip()
        if len(context.args) == 2:
            origin_branch = context.args[0].strip()
            new_branch = context.args[1].strip()

        result = await asyncio.to_thread(
            self.git.prepare_branch,
            project_path,
            origin_branch=origin_branch,
            new_branch=new_branch,
        )
        if not result.success:
            await send_text(update, context, result.message)
            return

        self.deps.store.set_current_branch(self.deps.bot_id, chat_id, result.current_branch)
        self.deps.store.set_active_session_branch(self.deps.bot_id, chat_id, result.current_branch or "")
        logger.info(
            "Prepared branch '%s' for chat %s in project '%s' from base '%s'.",
            result.current_branch,
            chat_id,
            project_folder,
            origin_branch or result.default_branch or "unknown",
        )
        await send_text(
            update,
            context,
            f"{result.message}\nCurrent branch: {result.current_branch}",
        )

    async def handle_new(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        allowed, reason = self._chat_allowed(update)
        if not allowed:
            await send_text(update, context, reason)
            return

        if len(context.args) < 1:
            await send_text(update, context, "Usage: /new <session_name> [provider]\nExample: /new backend-fix codex")
            return

        chat_id = update.effective_chat.id
        chat_state = self.deps.store.get_chat_state(self.deps.bot_id, chat_id)
        project_folder = chat_state.get("current_project_folder")
        branch_name = chat_state.get("current_branch", "")
        if not project_folder:
            await send_text(
                update,
                context,
                "No project selected.\nPlease run /project <project_folder> first.\nExample: /project backend",
            )
            return

        provider = self.deps.cfg.default_agent_provider
        name_parts = context.args
        if context.args[-1].lower() in {"codex", "copilot"}:
            provider = context.args[-1].lower()
            name_parts = context.args[:-1]

        session_name = " ".join(name_parts).strip()
        if not session_name:
            await send_text(update, context, "Session name cannot be empty.")
            return
        existing_sessions = self.deps.store.list_sessions(self.deps.bot_id, chat_id)
        if any(data.get("name", "").strip().lower() == session_name.lower() for data in existing_sessions.values()):
            await send_text(
                update,
                context,
                f"Session name already exists: {session_name}\nPlease use a different session name.",
            )
            return

        project_path = resolve_project_path(self.deps.cfg.workspace_root, project_folder)
        logger.info(
            "Creating session '%s' for chat %s in project '%s' with provider '%s'.",
            session_name,
            chat_id,
            project_folder,
            provider,
        )
        await send_text(update, context, "Creating session...")
        result = await self._run_with_typing(
            update,
            context,
            self.deps.agent_runner.create_session,
            provider,
            project_path,
            f"Create session: {session_name}",
            skip_git_repo_check=self.runtime.should_skip_git_repo_check(project_folder),
        )

        if not result.success or not result.session_id:
            await send_text(update, context, result.error_message or "Failed to create a session.")
            return

        self.deps.store.create_session(
            self.deps.bot_id,
            chat_id,
            result.session_id,
            session_name,
            project_folder,
            provider,
            branch_name=branch_name,
        )
        logger.info(
            "Created session '%s' (%s) for chat %s in project '%s'.",
            session_name,
            result.session_id,
            chat_id,
            project_folder,
        )
        await send_text(
            update,
            context,
            (
                f"Session created successfully: {session_name}\n"
                f"Session ID: {result.session_id}\n"
                f"Project: {project_folder}\n"
                f"Provider: {provider}\n"
                f"Branch: {branch_name or '(current branch)'}"
            ),
        )

    async def handle_switch(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        allowed, reason = self._chat_allowed(update)
        if not allowed:
            await send_text(update, context, reason)
            return

        chat_id = update.effective_chat.id
        sessions = self.deps.store.list_sessions(self.deps.bot_id, chat_id)
        active = self.deps.store.get_chat_state(self.deps.bot_id, chat_id).get("active_session_id")

        if not context.args:
            if not sessions:
                await send_text(update, context, "No sessions found.")
                return
            logger.info("Listed sessions page 1 for chat %s (%d sessions total).", chat_id, len(sessions))
            await send_html_text(update, context, self._build_switch_page(sessions, active, 1))
            return

        if len(context.args) == 2 and context.args[0].lower() == "page":
            if not sessions:
                await send_text(update, context, "No sessions found.")
                return
            try:
                page = int(context.args[1])
            except ValueError:
                await send_text(update, context, "Invalid page number.\nUse: /switch page <number>")
                return
            if page < 1:
                await send_text(update, context, "Invalid page number.\nUse: /switch page <number>")
                return
            logger.info("Listed sessions page %d for chat %s (%d sessions total).", page, chat_id, len(sessions))
            await send_html_text(update, context, self._build_switch_page(sessions, active, page))
            return

        session_id = " ".join(context.args).strip()
        session = self.deps.store.get_session(self.deps.bot_id, chat_id, session_id)
        if session is None:
            await send_text(update, context, "⚠️ Session not found.\nRun /switch to list available sessions.")
            return

        branch_name = session.get("branch_name", "")
        project_path = resolve_project_path(self.deps.cfg.workspace_root, session["project_folder"])
        if not project_path.exists() or not project_path.is_dir():
            await send_text(
                update,
                context,
                f"⚠️ Project folder no longer exists for this session: {session['project_folder']}",
            )
            return
        if branch_name and self.git.is_git_repo(project_path):
            checkout = await asyncio.to_thread(self.git.checkout_branch, project_path, branch_name)
            if not checkout.success:
                await send_text(update, context, checkout.message)
                return
        if not self.deps.store.switch_session(self.deps.bot_id, chat_id, session_id):
            await send_text(update, context, "⚠️ Session not found.\nRun /switch to list available sessions.")
            return
        logger.info(
            "Switched chat %s to session '%s' (%s) in project '%s'.",
            chat_id,
            session["name"],
            session_id,
            session["project_folder"],
        )
        await send_html_text(
            update,
            context,
            f"Switched to session: {html.escape(session['name'])}\nProject: <code>{html.escape(session['project_folder'])}</code>\nProvider: {html.escape(session.get('provider', 'codex'))}\nBranch: {html.escape(branch_name or '(current branch)')}",
        )

    async def handle_current(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        allowed, reason = self._chat_allowed(update)
        if not allowed:
            await send_text(update, context, reason)
            return

        chat_id = update.effective_chat.id
        chat_state = self.deps.store.get_chat_state(self.deps.bot_id, chat_id)
        active_id = chat_state.get("active_session_id")
        if not active_id:
            await send_text(update, context, "No active session.\nPlease run /project and /new first.")
            return

        session = chat_state.get("sessions", {}).get(active_id)
        if not session:
            await send_text(update, context, "No active session.\nPlease run /project and /new first.")
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
                f"Project: {session['project_folder']}\n"
                f"Provider: {session.get('provider', 'codex')}\n"
                f"Branch: {session.get('branch_name') or '(current branch)'}"
            ),
        )

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        allowed, reason = self._chat_allowed(update)
        if not allowed:
            await send_text(update, context, reason)
            return

        if update.message is None or not update.message.text:
            return
        await self.runtime.run_active_session(update, context, user_message=update.message.text)

    async def handle_photo(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        allowed, reason = self._chat_allowed(update)
        if not allowed:
            await send_text(update, context, reason)
            return

        if update.message is None or not update.message.photo:
            return

        chat_id = update.effective_chat.id
        chat_state = self.deps.store.get_chat_state(self.deps.bot_id, chat_id)
        active_id = chat_state.get("active_session_id")
        if not active_id:
            await send_text(update, context, "No active session.\nPlease run /project and /new first.")
            return

        session = chat_state.get("sessions", {}).get(active_id)
        if not session:
            await send_text(update, context, "No active session.\nPlease run /project and /new first.")
            return

        if session.get("provider", "codex") != "codex":
            await send_text(update, context, "Photo attachments are currently supported only for codex sessions.")
            return

        project_path = resolve_project_path(self.deps.cfg.workspace_root, session["project_folder"])
        attachment_path = await self.photo_attachments.store_photo(update, session["project_folder"])
        prompt = self.photo_attachments.build_prompt(attachment_path, project_path, update.message.caption or "")
        await self.runtime.run_active_session(update, context, user_message=prompt, image_paths=(attachment_path,))

    async def handle_unsupported_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        allowed, reason = self._chat_allowed(update)
        if not allowed:
            await send_text(update, context, reason)
            return

        await send_text(
            update,
            context,
            "Unsupported message type.\nThis bot currently accepts only text messages and photos.",
        )
