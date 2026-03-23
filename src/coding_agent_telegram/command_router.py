from __future__ import annotations

from dataclasses import dataclass

from telegram import Update
from telegram.ext import ContextTypes

from coding_agent_telegram.agent_runner import MultiAgentRunner
from coding_agent_telegram.config import AppConfig
from coding_agent_telegram.diff_utils import build_summary, changed_files, chunk_fenced_diff, collect_diffs
from coding_agent_telegram.filters import is_sensitive_path, is_valid_project_folder, resolve_project_path
from coding_agent_telegram.session_store import SessionStore
from coding_agent_telegram.telegram_sender import send_text


@dataclass
class RouterDeps:
    cfg: AppConfig
    store: SessionStore
    agent_runner: MultiAgentRunner


class CommandRouter:
    def __init__(self, deps: RouterDeps) -> None:
        self.deps = deps

    def _chat_allowed(self, update: Update) -> tuple[bool, str | None]:
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

        path = resolve_project_path(self.deps.cfg.workspace_root, folder)
        if not path.exists() or not path.is_dir():
            await send_text(update, context, f"Project not found: {folder}")
            return

        self.deps.store.set_current_project_folder(update.effective_chat.id, folder)
        await send_text(update, context, f"Project set: {folder}")

    async def handle_new(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        allowed, reason = self._chat_allowed(update)
        if not allowed:
            await send_text(update, context, reason)
            return

        if len(context.args) < 1:
            await send_text(update, context, "Usage: /new <session_name> [provider]\nExample: /new backend-fix codex")
            return

        chat_id = update.effective_chat.id
        chat_state = self.deps.store.get_chat_state(chat_id)
        project_folder = chat_state.get("current_project_folder")
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

        project_path = resolve_project_path(self.deps.cfg.workspace_root, project_folder)
        result = self.deps.agent_runner.create_session(provider, project_path, f"Create session: {session_name}")

        if not result.success or not result.session_id:
            await send_text(update, context, result.error_message or "Failed to create a session.")
            return

        self.deps.store.create_session(chat_id, result.session_id, session_name, project_folder, provider)
        await send_text(
            update,
            context,
            f"Session created successfully: {session_name}\nProject: {project_folder}\nProvider: {provider}",
        )

    async def handle_switch(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        allowed, reason = self._chat_allowed(update)
        if not allowed:
            await send_text(update, context, reason)
            return

        chat_id = update.effective_chat.id
        sessions = self.deps.store.list_sessions(chat_id)
        active = self.deps.store.get_chat_state(chat_id).get("active_session_id")

        if not context.args:
            if not sessions:
                await send_text(update, context, "No sessions found.")
                return
            lines = ["Available sessions:", ""]
            for idx, (sid, data) in enumerate(sessions.items(), start=1):
                status = "active" if sid == active else "idle"
                lines.extend(
                    [
                        f"{idx}.",
                        f"session_id: {sid}",
                        f"name: {data['name']}",
                        f"project: {data['project_folder']}",
                        f"provider: {data.get('provider', 'codex')}",
                        f"status: {status}",
                        "",
                    ]
                )
            lines.extend(["Use:", "/switch <session_id>"])
            await send_text(update, context, "\n".join(lines).strip())
            return

        session_id = context.args[0]
        if not self.deps.store.switch_session(chat_id, session_id):
            await send_text(update, context, "Session not found.\nRun /switch to list available sessions.")
            return

        session = self.deps.store.list_sessions(chat_id)[session_id]
        await send_text(
            update,
            context,
            f"Switched to session: {session['name']}\nProject: {session['project_folder']}\nProvider: {session.get('provider', 'codex')}",
        )

    async def handle_current(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        allowed, reason = self._chat_allowed(update)
        if not allowed:
            await send_text(update, context, reason)
            return

        chat_id = update.effective_chat.id
        chat_state = self.deps.store.get_chat_state(chat_id)
        active_id = chat_state.get("active_session_id")
        if not active_id:
            await send_text(update, context, "No active session.\nPlease run /project and /new first.")
            return

        session = chat_state.get("sessions", {}).get(active_id)
        if not session:
            await send_text(update, context, "No active session.\nPlease run /project and /new first.")
            return

        await send_text(
            update,
            context,
            f"Current session: {session['name']}\nProject: {session['project_folder']}\nProvider: {session.get('provider', 'codex')}",
        )

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        allowed, reason = self._chat_allowed(update)
        if not allowed:
            await send_text(update, context, reason)
            return

        if update.message is None or not update.message.text:
            return

        chat_id = update.effective_chat.id
        chat_state = self.deps.store.get_chat_state(chat_id)
        active_id = chat_state.get("active_session_id")
        if not active_id:
            await send_text(update, context, "No active session.\nPlease run /project and /new first.")
            return

        session = chat_state.get("sessions", {}).get(active_id)
        if not session:
            await send_text(update, context, "No active session.\nPlease run /project and /new first.")
            return

        project_folder = session["project_folder"]
        provider = session.get("provider", "codex")
        project_path = resolve_project_path(self.deps.cfg.workspace_root, project_folder)

        before = set(changed_files(project_path))
        result = self.deps.agent_runner.resume_session(provider, active_id, project_path, update.message.text)

        if (not result.success) and result.error_message and "resume" in result.error_message.lower():
            create_result = self.deps.agent_runner.create_session(provider, project_path, update.message.text)
            if create_result.success and create_result.session_id:
                self.deps.store.create_session(chat_id, create_result.session_id, session["name"], project_folder, provider)
                await send_text(
                    update,
                    context,
                    "The previous session is no longer valid.\nA new session was created and the task continued.",
                )
                result = create_result

        if not result.success:
            await send_text(update, context, result.error_message or "Agent run failed.")
            return

        after = set(changed_files(project_path))
        files = sorted(after.union(before))
        diffs = collect_diffs(project_path, files)

        await send_text(update, context, build_summary(session["name"], project_folder, files))

        for file_diff in diffs:
            if self.deps.cfg.enable_sensitive_diff_filter and is_sensitive_path(file_diff.path):
                await send_text(update, context, f"{file_diff.path}\nThis file contains sensitive content and was omitted.")
                continue

            for chunk in chunk_fenced_diff(
                file_diff.path,
                file_diff.diff,
                self.deps.cfg.max_telegram_message_length,
            ):
                await send_text(update, context, chunk)
