from __future__ import annotations

import asyncio
import html
import logging
import os
import shlex
from dataclasses import dataclass
from pathlib import Path
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
    ALLOWED_COMMIT_SUBCOMMANDS = {"add", "commit", "restore", "rm", "status"}
    ENFORCED_COMMIT_ARGS = ["--no-verify", "--no-post-rewrite", "--no-gpg-sign"]
    SAFE_COMMIT_OPTION_RULES = {
        "add": {
            "flags": {"-A", "--all", "-u", "--update"},
            "value_options": set(),
        },
        "commit": {
            "flags": {"-a", "--all", "--amend", "--no-edit"},
            "value_options": {"-m", "--message"},
        },
        "restore": {
            "flags": {"--staged", "--worktree"},
            "value_options": {"--source"},
        },
        "rm": {
            "flags": {"-f", "--force", "-r", "--recursive", "--cached", "--ignore-unmatch"},
            "value_options": set(),
        },
        "status": {
            "flags": {"-s", "--short", "-b", "--branch", "--porcelain"},
            "value_options": set(),
        },
    }
    DISALLOWED_NESTED_GIT_SUBCOMMANDS = ALLOWED_COMMIT_SUBCOMMANDS | {
        "branch",
        "checkout",
        "cherry-pick",
        "diff",
        "clone",
        "fetch",
        "merge",
        "pull",
        "push",
        "rebase",
        "reset",
        "switch",
        "tag",
    }

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
        if chat.type != "private":
            return False, "Group chats are not supported."
        return True, None

    def _active_session_context(self, chat_id: int) -> tuple[Optional[str], Optional[dict[str, str]], Optional[Path]]:
        chat_state = self.deps.store.get_chat_state(self.deps.bot_id, chat_id)
        active_id = chat_state.get("active_session_id")
        if not active_id:
            return None, None, None
        session = chat_state.get("sessions", {}).get(active_id)
        if not session:
            return active_id, None, None
        project_path = resolve_project_path(self.deps.cfg.workspace_root, session["project_folder"])
        return active_id, session, project_path

    def _split_shell_commands(self, raw: str) -> list[str]:
        commands: list[str] = []
        current: list[str] = []
        quote: Optional[str] = None
        escape = False
        index = 0
        while index < len(raw):
            char = raw[index]
            if escape:
                current.append(char)
                escape = False
                index += 1
                continue
            if char == "\\":
                current.append(char)
                escape = True
                index += 1
                continue
            if quote:
                current.append(char)
                if char == quote:
                    quote = None
                index += 1
                continue
            if char in {"'", '"'}:
                quote = char
                current.append(char)
                index += 1
                continue
            if raw.startswith("&&", index) or raw.startswith("||", index):
                segment = "".join(current).strip()
                if segment:
                    commands.append(segment)
                current = []
                index += 2
                continue
            if char in {";", "\n", "|", "&", "<", ">"}:
                segment = "".join(current).strip()
                if segment:
                    commands.append(segment)
                current = []
                while index + 1 < len(raw) and raw[index + 1] == char:
                    index += 1
                index += 1
                continue
            current.append(char)
            index += 1

        segment = "".join(current).strip()
        if segment:
            commands.append(segment)
        return commands

    def _validated_commit_commands(self, raw: str) -> tuple[list[list[str]], list[str]]:
        valid: list[list[str]] = []
        ignored: list[str] = []
        for segment in self._split_shell_commands(raw):
            try:
                tokens = shlex.split(segment)
            except ValueError:
                ignored.append(segment)
                continue
            if len(tokens) < 2 or tokens[0] != "git":
                ignored.append(segment)
                continue
            if tokens[1].startswith("-") or tokens[1] not in self.ALLOWED_COMMIT_SUBCOMMANDS:
                ignored.append(segment)
                continue
            if self._has_nested_git_subcommand(tokens):
                ignored.append(segment)
                continue
            if not self._has_only_safe_commit_args(tokens[1], tokens[2:]):
                ignored.append(segment)
                continue
            valid.append(tokens[1:])
        return valid, ignored

    @classmethod
    def _extract_commit_path_args(cls, subcommand: str, args: list[str]) -> list[str]:
        paths: list[str] = []
        index = 0
        after_double_dash = False

        while index < len(args):
            token = args[index]
            if after_double_dash:
                paths.append(token)
                index += 1
                continue
            if token == "--":
                after_double_dash = True
                index += 1
                continue
            if subcommand == "commit":
                if token in {"-m", "--message"}:
                    index += 2
                    continue
                if token.startswith("--message=") or (token.startswith("-m") and token != "-m"):
                    index += 1
                    continue
            if subcommand == "restore":
                if token == "--source":
                    index += 2
                    continue
                if token.startswith("--source="):
                    index += 1
                    continue
            if token.startswith("-") and token != "-":
                index += 1
                continue
            paths.append(token)
            index += 1

        return paths

    @staticmethod
    def _path_within_project(project_path: Path, token: str) -> bool:
        if not token:
            return False
        if token.startswith(":(") or token.startswith(":/"):
            return False

        candidate = Path(token.replace("\\", "/"))
        if candidate.is_absolute():
            return False

        normalized = Path(os.path.normpath(candidate.as_posix()))
        if normalized == Path(".."):
            return False
        if any(part == ".." for part in normalized.parts):
            return False
        return True

    @classmethod
    def _commands_use_only_project_paths(cls, project_path: Path, commands: list[list[str]]) -> bool:
        for args in commands:
            if not args:
                return False
            for token in cls._extract_commit_path_args(args[0], args[1:]):
                if not cls._path_within_project(project_path, token):
                    return False
        return True

    @staticmethod
    def _append_ignored_segments(lines: list[str], ignored: list[str]) -> None:
        if ignored:
            lines.extend(["", "Ignored non-git commands:", *[f"- {segment}" for segment in ignored]])

    @staticmethod
    def _bash_block(text: str) -> str:
        return f'<pre><code class="language-bash">{html.escape(text)}</code></pre>'

    @staticmethod
    def _git_result_output(result) -> str:
        parts = [part for part in (getattr(result, "stdout", ""), getattr(result, "stderr", "")) if part]
        if parts:
            return "\n".join(parts)
        message = getattr(result, "message", "")
        return message if not getattr(result, "success", False) and message else "[Completed]"

    @classmethod
    def _effective_git_args(cls, args: list[str]) -> list[str]:
        if args and args[0] == "commit":
            insert_at = len(args)
            index = 1
            while index < len(args):
                token = args[index]
                if token == "--":
                    insert_at = index
                    break
                if token in {"-m", "--message"}:
                    index += 2
                    continue
                if token.startswith("--message="):
                    index += 1
                    continue
                if token.startswith("-m") and token != "-m":
                    index += 1
                    continue
                if token.startswith("-"):
                    index += 1
                    continue
                insert_at = index
                break
            return [*args[:insert_at], *cls.ENFORCED_COMMIT_ARGS, *args[insert_at:]]
        return args

    @classmethod
    def _format_git_response(cls, commands: list[tuple[list[str], object]], ignored: list[str]) -> str:
        lines: list[str] = []
        for args, result in commands:
            lines.append(f"${shlex.join(['git', *args])}")
            lines.append("---------------")
            lines.append(cls._git_result_output(result))
            lines.append("")
        if ignored:
            lines.extend(["Ignored non-git commands:", *[f"- {segment}" for segment in ignored]])
        return "\n".join(lines).rstrip()

    @classmethod
    def _has_nested_git_subcommand(cls, tokens: list[str]) -> bool:
        for index in range(2, len(tokens) - 1):
            if tokens[index] == "git" and tokens[index + 1] in cls.DISALLOWED_NESTED_GIT_SUBCOMMANDS:
                return True
        return False

    @classmethod
    def _has_only_safe_commit_args(cls, subcommand: str, args: list[str]) -> bool:
        rules = cls.SAFE_COMMIT_OPTION_RULES.get(subcommand)
        if rules is None:
            return False

        flags = rules["flags"]
        value_options = rules["value_options"]
        index = 0
        after_double_dash = False
        while index < len(args):
            token = args[index]
            if after_double_dash:
                index += 1
                continue
            if token == "--":
                after_double_dash = True
                index += 1
                continue
            if not token.startswith("-") or token == "-":
                index += 1
                continue
            if token in flags:
                index += 1
                continue
            if token in value_options:
                if index + 1 >= len(args):
                    return False
                index += 2
                continue
            if any(option.startswith("--") and token.startswith(f"{option}=") for option in value_options):
                index += 1
                continue
            short_value_option = next(
                (
                    option
                    for option in value_options
                    if len(option) == 2 and option.startswith("-") and token.startswith(option) and token != option
                ),
                None,
            )
            if short_value_option is not None:
                index += 1
                continue
            if token.startswith("-") and not token.startswith("--") and len(token) > 2:
                short_flags = {option for option in flags if len(option) == 2 and option.startswith("-")}
                if all(f"-{char}" in short_flags for char in token[1:]):
                    index += 1
                    continue
            return False
        return True

    async def _ensure_session_project_exists(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        session: dict[str, str],
        project_path: Path,
    ) -> bool:
        if project_path.exists() and project_path.is_dir():
            return True
        await send_text(
            update,
            context,
            f"⚠️ Project folder no longer exists for this session: {session['project_folder']}",
        )
        return False

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

    async def handle_commit(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        allowed, reason = self._chat_allowed(update)
        if not allowed:
            await send_text(update, context, reason)
            return

        if update.message is None or not update.message.text:
            await send_text(update, context, "Usage: /commit git add ... && git commit ...")
            return

        raw = update.message.text.partition(" ")[2].strip()
        if not raw:
            await send_text(update, context, "Usage: /commit git add ... && git commit ...")
            return

        chat_id = update.effective_chat.id
        _, session, project_path = self._active_session_context(chat_id)
        if session is None or project_path is None:
            await send_text(update, context, "No active session.\nPlease run /project and /new first.")
            return
        if not await self._ensure_session_project_exists(update, context, session, project_path):
            return
        if not self.git.is_git_repo(project_path):
            await send_text(update, context, "⚠️ Current project is not a git repository.")
            return

        commands, ignored = self._validated_commit_commands(raw)
        if not commands:
            await send_text(update, context, "No valid git commit commands were found.")
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

    async def handle_push(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        allowed, reason = self._chat_allowed(update)
        if not allowed:
            await send_text(update, context, reason)
            return

        if context.args:
            await send_text(update, context, "Usage: /push")
            return

        chat_id = update.effective_chat.id
        _, session, project_path = self._active_session_context(chat_id)
        if session is None or project_path is None:
            await send_text(update, context, "No active session.\nPlease run /project and /new first.")
            return
        if not await self._ensure_session_project_exists(update, context, session, project_path):
            return
        if not self.git.is_git_repo(project_path):
            await send_text(update, context, "⚠️ Current project is not a git repository.")
            return

        branch_name = session.get("branch_name") or self.git.current_branch(project_path)
        if not branch_name:
            await send_text(update, context, "⚠️ Could not determine the branch for the current session.")
            return

        current_branch = self.git.current_branch(project_path)
        if current_branch != branch_name:
            checkout = await asyncio.to_thread(self.git.checkout_branch, project_path, branch_name)
            if not checkout.success:
                await send_html_text(
                    update,
                    context,
                    self._bash_block(self._format_git_response([(["checkout", branch_name], checkout)], [])),
                )
                return

        result = await asyncio.to_thread(self.git.push_branch, project_path, branch_name)
        await send_html_text(
            update,
            context,
            self._bash_block(self._format_git_response([(["push", "origin", branch_name], result)], [])),
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
        try:
            attachment_path = await self.photo_attachments.store_photo(update, session["project_folder"])
        except ValueError as exc:
            await send_text(update, context, str(exc))
            return
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
