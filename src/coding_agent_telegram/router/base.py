from __future__ import annotations

import asyncio
import html
import logging
import os
import shlex
from concurrent.futures import CancelledError, Future
from dataclasses import dataclass
from functools import wraps
from pathlib import Path
from typing import Awaitable, Callable, Optional, Tuple

from telegram import Update
from telegram.constants import ChatAction
from telegram.error import BadRequest
from telegram.ext import ContextTypes

from coding_agent_telegram.agent_runner import AgentProgressInfo, MultiAgentRunner
from coding_agent_telegram.config import AppConfig
from coding_agent_telegram.filters import resolve_project_path
from coding_agent_telegram.git_utils import GitWorkspaceManager, _sanitize_git_output
from coding_agent_telegram.session_runtime import PhotoAttachmentStore, SessionRuntime
from coding_agent_telegram.session_store import SessionStore
from coding_agent_telegram.telegram_sender import send_text


logger = logging.getLogger(__name__)
TYPING_REFRESH_TIMEOUT_SECONDS = 4
ACTIVE_SESSION_REQUIRED_MESSAGE = "No active session.\nPlease run /project and /new first."
PROGRESS_PREVIEW_MAX_CHARS = 600


def require_allowed_chat(*, answer_callback: bool = False):
    """Skip handler execution when the incoming chat is not authorized for this bot."""

    def decorator(handler: Callable[..., Awaitable[None]]) -> Callable[..., Awaitable[None]]:
        @wraps(handler)
        async def wrapper(self: "CommandRouterBase", update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
            allowed, reason = self._chat_allowed(update)
            if not allowed:
                if answer_callback and update.callback_query is not None:
                    await update.callback_query.answer()
                elif reason:
                    await send_text(update, context, reason)
                return
            await handler(self, update, context)

        return wrapper

    return decorator


@dataclass
class RouterDeps:
    cfg: AppConfig
    store: SessionStore
    agent_runner: MultiAgentRunner
    bot_id: str


class CommandRouterBase:
    SWITCH_PAGE_SIZE = 10
    ALLOWED_COMMIT_SUBCOMMANDS = {"add", "commit", "restore", "rm", "status"}
    TRUST_REQUIRED_COMMIT_SUBCOMMANDS = {"add", "restore", "rm"}
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

        stall_message = kwargs.pop("stall_message", None)
        progress_label = kwargs.pop("progress_label", None)
        progress_state = {"message_id": None, "last_text": "", "closed": False, "futures": set()}
        if stall_message:
            kwargs["on_stall"] = self._make_stall_notifier(update, context, stall_message)
        if progress_label:
            kwargs["on_progress"] = self._make_progress_notifier(update, context, progress_label, progress_state)

        stop_event = asyncio.Event()
        await self._safe_send_chat_action(context, chat.id, ChatAction.TYPING)

        async def typing_loop() -> None:
            while not stop_event.is_set():
                await self._safe_send_chat_action(context, chat.id, ChatAction.TYPING)
                try:
                    await asyncio.wait_for(stop_event.wait(), timeout=TYPING_REFRESH_TIMEOUT_SECONDS)
                except asyncio.TimeoutError:
                    continue

        typing_task = asyncio.create_task(typing_loop())
        try:
            result = await asyncio.to_thread(fn, *args, **kwargs)
            # Give thread-safe Telegram notifications one event-loop turn to run
            # before we close the progress channel and finalize the response.
            await asyncio.sleep(0)
            pending_progress = tuple(progress_state["futures"])
            if pending_progress:
                try:
                    await asyncio.wait_for(
                        asyncio.gather(*(asyncio.wrap_future(future) for future in pending_progress), return_exceptions=True),
                        timeout=0.1,
                    )
                except asyncio.TimeoutError:
                    pass
            progress_state["closed"] = True
            for future in tuple(progress_state["futures"]):
                future.cancel()
            if progress_state["message_id"] is not None and hasattr(context.bot, "delete_message"):
                try:
                    await context.bot.delete_message(chat_id=chat.id, message_id=progress_state["message_id"])
                except BadRequest:
                    pass
            return result
        finally:
            stop_event.set()
            await typing_task

    def _make_stall_notifier(self, update: Update, context: ContextTypes.DEFAULT_TYPE, message: str):
        loop = asyncio.get_running_loop()

        def notify(_info) -> None:
            self._submit_threadsafe_notification(asyncio.run_coroutine_threadsafe(send_text(update, context, message), loop))

        return notify

    def _make_progress_notifier(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        label: str,
        progress_state: dict[str, object],
    ):
        loop = asyncio.get_running_loop()

        async def publish(info: AgentProgressInfo) -> None:
            chat = update.effective_chat
            if chat is None or progress_state.get("closed"):
                return
            body = info.text.strip()
            if len(body) > PROGRESS_PREVIEW_MAX_CHARS:
                body = body[: PROGRESS_PREVIEW_MAX_CHARS - 1].rstrip() + "..."
            message_text = f"{label} ({int(info.elapsed_seconds)}s)\n{body}"
            if message_text == progress_state["last_text"]:
                return
            progress_state["last_text"] = message_text
            if progress_state.get("closed"):
                return
            if progress_state["message_id"] is None:
                message = await context.bot.send_message(chat_id=chat.id, text=message_text)
                message_id = getattr(message, "message_id", None)
                if progress_state.get("closed") and message_id is not None and hasattr(context.bot, "delete_message"):
                    try:
                        await context.bot.delete_message(chat_id=chat.id, message_id=message_id)
                    except BadRequest:
                        pass
                    return
                progress_state["message_id"] = message_id
                return
            try:
                await context.bot.edit_message_text(
                    chat_id=chat.id,
                    message_id=progress_state["message_id"],
                    text=message_text,
                )
            except BadRequest:
                message = await context.bot.send_message(chat_id=chat.id, text=message_text)
                progress_state["message_id"] = getattr(message, "message_id", None)

        def notify(info: AgentProgressInfo) -> None:
            future = asyncio.run_coroutine_threadsafe(publish(info), loop)
            progress_state["futures"].add(future)
            self._submit_threadsafe_notification(future, progress_state=progress_state)

        return notify

    def _submit_threadsafe_notification(self, future: Future, *, progress_state: Optional[dict[str, object]] = None) -> None:
        def on_done(done_future: Future) -> None:
            if progress_state is not None:
                progress_state["futures"].discard(done_future)
            try:
                done_future.result()
            except CancelledError:
                pass
            except Exception:
                logger.exception("Telegram notification callback failed.")

        future.add_done_callback(on_done)

    async def _safe_send_chat_action(self, context: ContextTypes.DEFAULT_TYPE, chat_id: int, action: ChatAction) -> None:
        try:
            await context.bot.send_chat_action(chat_id=chat_id, action=action)
        except Exception:
            logger.warning("Failed to send Telegram chat action '%s' to chat %s.", action, chat_id, exc_info=True)

    def _chat_allowed(self, update: Update) -> Tuple[bool, Optional[str]]:
        chat = update.effective_chat
        if chat is None:
            return False, "Chat is not available."
        if chat.id not in self.deps.cfg.allowed_chat_ids:
            logger.info("Ignoring unauthorized chat %s of type '%s'.", chat.id, chat.type)
            return False, None
        if chat.type != "private":
            logger.info("Ignoring non-private chat %s of type '%s'.", chat.id, chat.type)
            return False, None
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

    async def _active_session_or_notify(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
    ) -> tuple[Optional[str], Optional[dict[str, str]]]:
        """Load the active session for the current chat or send the standard setup prompt."""
        chat_id = update.effective_chat.id
        active_id, session, _ = self._active_session_context(chat_id)
        if session is None:
            await send_text(update, context, ACTIVE_SESSION_REQUIRED_MESSAGE)
            return None, None
        return active_id, session

    async def _active_session_project_or_notify(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        *,
        require_git_repo: bool = False,
    ) -> tuple[Optional[dict[str, str]], Optional[Path]]:
        """Resolve the active session project and perform the common existence checks."""
        chat_id = update.effective_chat.id
        _, session, project_path = self._active_session_context(chat_id)
        if session is None or project_path is None:
            await send_text(update, context, ACTIVE_SESSION_REQUIRED_MESSAGE)
            return None, None
        if not await self._ensure_session_project_exists(update, context, session, project_path):
            return None, None
        if require_git_repo and not self.git.is_git_repo(project_path):
            await send_text(update, context, "⚠️ Current project is not a git repository.")
            return None, None
        return session, project_path

    def _split_shell_commands(self, raw: str) -> list[str]:
        """Split shell-like input into independent command segments without executing it."""
        raw = self._normalize_shell_line_continuations(raw)
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

    def _normalize_shell_line_continuations(self, raw: str) -> str:
        normalized: list[str] = []
        quote: Optional[str] = None
        escape = False
        index = 0

        while index < len(raw):
            char = raw[index]
            if escape:
                if char == "\n" and quote is None:
                    escape = False
                    index += 1
                    while index < len(raw) and raw[index] in {" ", "\t"}:
                        index += 1
                    continue
                normalized.append("\\")
                normalized.append(char)
                escape = False
                index += 1
                continue
            if char == "\\":
                escape = True
                index += 1
                continue
            if quote:
                normalized.append(char)
                if char == quote:
                    quote = None
                index += 1
                continue
            if char in {"'", '"'}:
                quote = char
                normalized.append(char)
                index += 1
                continue
            normalized.append(char)
            index += 1

        if escape:
            normalized.append("\\")
        return "".join(normalized)

    def _validated_commit_commands(self, raw: str) -> tuple[list[list[str]], list[str]]:
        """Return validated `git` commit subcommands plus ignored raw segments."""
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
        """Extract path operands from a validated git subcommand argument list."""
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
        """Validate that a commit-path token stays within the current project boundary."""
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
        """Ensure every path argument in validated commands is relative to the project root."""
        for args in commands:
            if not args:
                return False
            for token in cls._extract_commit_path_args(args[0], args[1:]):
                if not cls._path_within_project(project_path, token):
                    return False
        return True

    @classmethod
    def _requires_trusted_project(cls, commands: list[list[str]]) -> bool:
        """Report whether any validated command mutates tracked content."""
        return any(args and args[0] in cls.TRUST_REQUIRED_COMMIT_SUBCOMMANDS for args in commands)

    @staticmethod
    def _append_ignored_segments(lines: list[str], ignored: list[str]) -> None:
        if ignored:
            lines.extend(["", "Ignored non-git commands:", *[f"- {segment}" for segment in ignored]])

    @staticmethod
    def _bash_block(text: str) -> str:
        return f'<pre><code class="language-bash">{html.escape(text)}</code></pre>'

    @staticmethod
    def _git_result_output(result) -> str:
        stdout = getattr(result, "stdout", "")
        stderr = getattr(result, "stderr", "")
        parts = [_sanitize_git_output(part) for part in (stdout, stderr) if part]
        if parts:
            return "\n".join(parts)
        message = getattr(result, "message", "")
        sanitized_message = _sanitize_git_output(message) if message else ""
        return sanitized_message if not getattr(result, "success", False) and sanitized_message else "[Completed]"

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
        """Allow only explicitly whitelisted flags and value-taking options for `/commit`."""
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
