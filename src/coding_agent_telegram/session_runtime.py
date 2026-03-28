from __future__ import annotations

import asyncio
import hashlib
import html
import importlib.resources
import logging
import re
from pathlib import Path
import os
from typing import Awaitable, Callable, Optional, Sequence

from telegram import Update
from telegram.ext import ContextTypes

from coding_agent_telegram.agent_runner import AgentRunResult, MultiAgentRunner
from coding_agent_telegram.config import AppConfig, DEFAULT_MAX_PHOTO_ATTACHMENT_BYTES
from coding_agent_telegram.diff_utils import (
    TEXTUAL_DIFF_UNAVAILABLE,
    build_summary,
    changed_files,
    changed_files_from_snapshots,
    chunk_fenced_diff,
    chunk_plain_text,
    collect_diffs,
    collect_snapshot_diffs,
    snapshot_project_files,
)
from coding_agent_telegram.filters import is_sensitive_path, resolve_project_path
from coding_agent_telegram.git_utils import GitWorkspaceManager
from coding_agent_telegram.session_store import SessionStore
from coding_agent_telegram.telegram_sender import (
    markdownish_to_html,
    send_code_block,
    send_html_text,
    send_text,
    split_assistant_output,
)


logger = logging.getLogger(__name__)
PHOTO_ATTACHMENTS_DIR = "telegram_attachments"
ACTIVE_SESSION_REQUIRED_MESSAGE = "No active session.\nPlease run /project and /new first."
MISSING_PROJECT_MESSAGE = "⚠️ Project folder no longer exists for this session: {project_folder}"
WORKING_MESSAGE = "Working on it..."
PHOTO_TOO_LARGE_MESSAGE = "Photo is too large. The maximum supported size is 5 MB."
IMAGE_INSPECTION_PROMPT = "Open and inspect that image before answering."
IMAGE_NO_CAPTION_MESSAGE = "The user sent an image without additional text."
ACTIVE_RUN_STALL_MESSAGE = (
    "The current agent run appears stuck.\n"
    "The local agent process is still running but has not produced output.\n"
    "On macOS this often means a hidden permission dialog is waiting for input on the machine running the bot."
)
REPLACEMENT_SESSION_STALL_MESSAGE = (
    "Replacement session creation appears stuck.\n"
    "The local agent process is still running but has not produced output.\n"
    "On macOS this often means a hidden permission dialog is waiting for input on the machine running the bot."
)

# Matches absolute filesystem paths (Unix and Windows styles) in error messages.
_ABSOLUTE_PATH_RE = re.compile(r"(?:^|(?<=\s)|(?<=[\"'(]))((?:/[^\s\"',;)]+)+|[A-Za-z]:\\[^\s\"',;)]+)")


def _load_secret_scrub_patterns() -> tuple[tuple[re.Pattern[str], str], ...]:
    resource = importlib.resources.files("coding_agent_telegram").joinpath("resources/secret_scrub_patterns.properties")
    compiled: list[tuple[re.Pattern[str], str]] = []
    try:
        raw_text = resource.read_text(encoding="utf-8")
    except OSError:
        logger.exception("Failed to load secret scrub patterns from %s.", resource)
        return ()
    for raw_line in raw_text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        name, pattern_text = line.split("=", 1)
        name = name.strip()
        pattern_text = pattern_text.strip()
        if not name or not pattern_text:
            continue
        try:
            compiled.append((re.compile(pattern_text), f"<{name}>"))
        except re.error:
            logger.exception("Invalid secret scrub regex for pattern '%s'.", name)
    return tuple(compiled)


# Patterns for secrets that the agent might echo back from files it has read.
# Matches are replaced with a placeholder before sending to Telegram.
_SECRET_SCRUB_PATTERNS: tuple[tuple[re.Pattern[str], str], ...] = _load_secret_scrub_patterns()


def _scrub_secrets(text: str) -> str:
    """Replace known secret patterns in *text* with redaction placeholders."""
    for pattern, replacement in _SECRET_SCRUB_PATTERNS:
        text = pattern.sub(replacement, text)
    return text


def _sanitize_agent_error(text: str) -> str:
    """Remove absolute filesystem paths from agent error messages before sending to users."""
    normalized = " ".join((text or "").split())
    if re.match(r"^Agent run aborted by .+", normalized):
        return "Agent run aborted by /abort."
    return _ABSOLUTE_PATH_RE.sub("<path>", text)


class PhotoAttachmentStore:
    MAX_PHOTO_BYTES = DEFAULT_MAX_PHOTO_ATTACHMENT_BYTES  # Telegram photos are capped to keep local storage bounded.

    def __init__(self, app_internal_root: Path) -> None:
        self.app_internal_root = app_internal_root

    def attachments_root(self, project_folder: str) -> Path:
        safe_project_folder = Path(project_folder).name
        return self.app_internal_root / PHOTO_ATTACHMENTS_DIR / safe_project_folder

    async def store_photo(self, update: Update, project_folder: str) -> Path:
        if update.message is None or not update.message.photo:
            raise ValueError("Photo message does not contain a photo.")

        telegram_photo = update.message.photo[-1]
        declared_size = getattr(telegram_photo, "file_size", None)
        if isinstance(declared_size, int) and declared_size > self.MAX_PHOTO_BYTES:
            raise ValueError(PHOTO_TOO_LARGE_MESSAGE)

        telegram_file = await telegram_photo.get_file()
        content = bytes(await telegram_file.download_as_bytearray())
        if len(content) > self.MAX_PHOTO_BYTES:
            raise ValueError(PHOTO_TOO_LARGE_MESSAGE)
        suffix = Path(telegram_file.file_path or "image.jpg").suffix.lower() or ".jpg"
        if suffix not in {".jpg", ".jpeg", ".png", ".webp", ".gif"}:
            suffix = ".jpg"
        digest = hashlib.sha256(content).hexdigest()

        attachments_root = self.attachments_root(project_folder)
        attachments_root.mkdir(parents=True, exist_ok=True)
        target = attachments_root / f"{digest}{suffix}"
        if not target.exists():
            target.write_bytes(content)
        return target

    def build_prompt(self, attachment_path: Path, project_path: Path, caption: str) -> str:
        rel_path = os.path.relpath(attachment_path, start=project_path).replace(os.sep, "/")
        lines = [
            f"An image is attached at {rel_path}.",
            IMAGE_INSPECTION_PROMPT,
        ]
        caption = caption.strip()
        if caption:
            lines.extend(["", "User caption:", caption])
        else:
            lines.extend(["", IMAGE_NO_CAPTION_MESSAGE])
        return "\n".join(lines)


RunWithTyping = Callable[..., Awaitable[object]]


class SessionRuntime:
    def __init__(
        self,
        *,
        cfg: AppConfig,
        store: SessionStore,
        agent_runner: MultiAgentRunner,
        bot_id: str,
        git: GitWorkspaceManager,
        run_with_typing: RunWithTyping,
    ) -> None:
        self.cfg = cfg
        self.store = store
        self.agent_runner = agent_runner
        self.bot_id = bot_id
        self.git = git
        self.run_with_typing = run_with_typing

    def _next_rotated_session_name(self, chat_id: int, base_name: str) -> str:
        existing = {
            data.get("name", "").strip().lower()
            for data in self.store.list_sessions(self.bot_id, chat_id).values()
            if data.get("name", "").strip()
        }
        suffix = 1
        while True:
            candidate = f"{base_name}-{suffix}"
            if candidate.lower() not in existing:
                return candidate
            suffix += 1

    def should_skip_git_repo_check(self, project_folder: str) -> bool:
        return self.cfg.codex_skip_git_repo_check or self.store.is_project_trusted(project_folder)

    async def _active_session_or_notify(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
    ) -> tuple[Optional[str], Optional[dict[str, str]], Optional[Path]]:
        """Load the active session and ensure its project folder still exists."""
        chat_id = update.effective_chat.id
        chat_state = self.store.get_chat_state(self.bot_id, chat_id)
        active_id = chat_state.get("active_session_id")
        if not active_id:
            await send_text(update, context, ACTIVE_SESSION_REQUIRED_MESSAGE)
            return None, None, None

        session = chat_state.get("sessions", {}).get(active_id)
        if not session:
            await send_text(update, context, ACTIVE_SESSION_REQUIRED_MESSAGE)
            return None, None, None

        project_path = resolve_project_path(self.cfg.workspace_root, session["project_folder"])
        if not project_path.exists() or not project_path.is_dir():
            await send_text(
                update,
                context,
                MISSING_PROJECT_MESSAGE.format(project_folder=session["project_folder"]),
            )
            return None, None, None
        return active_id, session, project_path

    async def run_active_session(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        *,
        user_message: str,
        image_paths: Sequence[Path] = (),
    ) -> AgentRunResult | None:
        chat_id = update.effective_chat.id
        active_id, session, project_path = await self._active_session_or_notify(update, context)
        if active_id is None or session is None or project_path is None:
            return None

        project_folder = session["project_folder"]
        provider = session.get("provider", "codex")
        branch_name = session.get("branch_name", "")
        logger.info(
            "Running message for chat %s on session '%s' (%s) in project '%s' with provider '%s'. "
            "Prompt (first 200 chars): %.200r",
            chat_id,
            session["name"],
            active_id,
            project_folder,
            provider,
            user_message,
        )

        if branch_name and self.git.is_git_repo(project_path):
            checkout = await self._checkout_branch(update, context, project_path, branch_name)
            if not checkout:
                return None

        before_snapshot = snapshot_project_files(
            project_path,
            max_text_file_bytes=self.cfg.snapshot_text_file_max_bytes,
        )
        before = set(changed_files(project_path))
        await send_text(update, context, WORKING_MESSAGE)
        result = await self.run_with_typing(
            update,
            context,
            self.agent_runner.resume_session,
            provider,
            active_id,
            project_path,
            user_message,
            workspace_lock_key=project_folder,
            skip_git_repo_check=self.should_skip_git_repo_check(project_folder),
            image_paths=image_paths,
            stall_message=ACTIVE_RUN_STALL_MESSAGE,
            progress_label="Live agent output",
        )
        if result is None:
            logger.info(
                "Agent run was not started for chat %s on project '%s' because the workspace is busy.",
                chat_id,
                project_folder,
            )
            return None
        session_name = session["name"]
        result, active_id, session_name = await self._replace_invalid_session_if_needed(
            update,
            context,
            result=result,
            active_id=active_id,
            session_name=session_name,
            session=session,
            chat_id=chat_id,
            project_folder=project_folder,
            provider=provider,
            project_path=project_path,
            branch_name=branch_name,
            user_message=user_message,
            image_paths=image_paths,
        )
        if result is None:
            return None
        if not result.success:
            logger.warning(
                "Agent run failed for chat %s on session '%s' (%s): %s",
                chat_id,
                session_name,
                active_id,
                result.error_message or "unknown error",
            )
            error_text = _sanitize_agent_error(result.error_message) if result.error_message else "Agent run failed."
            await send_text(update, context, error_text)
            return result

        if result.session_id and result.session_id != active_id:
            switched_session_name = self._next_rotated_session_name(chat_id, session_name)
            self.store.create_session(
                self.bot_id,
                chat_id,
                result.session_id,
                switched_session_name,
                project_folder,
                provider,
                branch_name=branch_name,
            )
            logger.info(
                "Resume returned a different session id for chat %s; switched from '%s' (%s) to '%s' (%s).",
                chat_id,
                session_name,
                active_id,
                switched_session_name,
                result.session_id,
            )
            await send_text(
                update,
                context,
                (
                    "Resume succeeded, but the session ID changed.\n"
                    f"New session ID: {result.session_id}\n"
                    f"New session name: {switched_session_name}"
                ),
            )
            session_name = switched_session_name
            active_id = result.session_id

        await self._send_run_results(
            update,
            context,
            provider=provider,
            session_name=session_name,
            project_folder=project_folder,
            project_path=project_path,
            active_id=active_id,
            result=result,
            before_snapshot=before_snapshot,
            before=before,
        )
        return result

    async def _checkout_branch(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        project_path: Path,
        branch_name: str,
    ) -> bool:
        checkout = await asyncio.to_thread(self.git.checkout_branch, project_path, branch_name)
        if not checkout.success:
            await send_text(update, context, checkout.message)
            return False
        return True

    async def _replace_invalid_session_if_needed(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        *,
        result,
        active_id: str,
        session_name: str,
        session: dict[str, str],
        chat_id: int,
        project_folder: str,
        provider: str,
        project_path: Path,
        branch_name: str,
        user_message: str,
        image_paths: Sequence[Path],
    ):
        if result.success or not result.error_message or "resume" not in result.error_message.lower():
            return result, active_id, session_name

        logger.info(
            "Session '%s' (%s) for chat %s could not be resumed; creating a replacement session.",
            session["name"],
            active_id,
            chat_id,
        )
        create_result = await self.run_with_typing(
            update,
            context,
            self.agent_runner.create_session,
            provider,
            project_path,
            user_message,
            workspace_lock_key=project_folder,
            skip_git_repo_check=self.should_skip_git_repo_check(project_folder),
            image_paths=image_paths,
            stall_message=REPLACEMENT_SESSION_STALL_MESSAGE,
            progress_label="Live agent output",
        )
        if create_result is None:
            return None, active_id, session_name
        if not create_result.success or not create_result.session_id:
            return create_result, active_id, session_name

        switched_session_name = self._next_rotated_session_name(chat_id, session_name)
        self.store.create_session(
            self.bot_id,
            chat_id,
            create_result.session_id,
            switched_session_name,
            project_folder,
            provider,
            branch_name=branch_name,
        )
        logger.info(
            "Created a replacement session for chat %s after resume failure: old='%s' (%s) new='%s' (%s).",
            chat_id,
            session_name,
            active_id,
            switched_session_name,
            create_result.session_id,
        )
        await send_text(
            update,
            context,
            (
                "Resume failed, so a new session was created.\n"
                f"New session ID: {create_result.session_id}\n"
                f"New session name: {switched_session_name}"
            ),
        )
        return create_result, create_result.session_id, switched_session_name

    async def _send_run_results(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        *,
        provider: str,
        session_name: str,
        project_folder: str,
        project_path: Path,
        active_id: str,
        result,
        before_snapshot: dict[str, str | None],
        before: set[str],
    ) -> None:
        after_snapshot = snapshot_project_files(
            project_path,
            max_text_file_bytes=self.cfg.snapshot_text_file_max_bytes,
        )
        after = set(changed_files(project_path))
        snapshot_files = changed_files_from_snapshots(before_snapshot, after_snapshot)
        files = sorted((after - before).union(snapshot_files))
        diffs = collect_diffs(project_path, files)
        snapshot_diffs_by_path = {
            file_diff.path: file_diff
            for file_diff in collect_snapshot_diffs(before_snapshot, after_snapshot, files)
        }
        diffs = self._merge_snapshot_diffs(diffs, snapshot_diffs_by_path)

        await self._send_assistant_chunks(update, context, result.assistant_text, provider=provider)
        logger.info(
            "Completed run for chat %s on session '%s' (%s); %d changed file(s).",
            update.effective_chat.id,
            session_name,
            result.session_id or active_id,
            len(files),
        )
        await send_text(update, context, build_summary(session_name, project_folder, files))
        await self._send_diffs(update, context, diffs)

    def _merge_snapshot_diffs(self, diffs, snapshot_diffs_by_path):
        if not snapshot_diffs_by_path:
            return diffs
        merged_diffs = []
        for file_diff in diffs:
            snapshot_diff = snapshot_diffs_by_path.get(file_diff.path)
            if snapshot_diff is not None and snapshot_diff.diff != TEXTUAL_DIFF_UNAVAILABLE:
                merged_diffs.append(snapshot_diff)
                continue
            if file_diff.diff:
                merged_diffs.append(file_diff)
                continue
            if snapshot_diff is not None:
                merged_diffs.append(snapshot_diff)
            else:
                merged_diffs.append(file_diff)
        return merged_diffs

    async def _send_assistant_chunks(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        assistant_text: str,
        *,
        provider: str,
    ) -> None:
        assistant_text = _scrub_secrets(assistant_text)
        segments = split_assistant_output(assistant_text)
        if not segments:
            return

        total = len(segments)
        for index, segment in enumerate(segments, start=1):
            if segment.kind == "code":
                await send_code_block(
                    update,
                    context,
                    f"{segment.header} ({index}/{total})",
                    segment.text,
                    language=segment.language,
                )
                continue

            provider_label = "Copilot" if provider == "copilot" else "Codex"
            title_prefix = f"{provider_label} output" if total == 1 else f"{provider_label} output {index}/{total}"
            for message in self._chunk_assistant_prose(title_prefix, segment.text):
                await send_html_text(update, context, message)

    def _chunk_assistant_prose(self, title_prefix: str, text: str) -> list[str]:
        normalized = text.strip()
        if not normalized:
            return []

        bodies = [normalized]
        while True:
            total = len(bodies)
            for idx, body in enumerate(bodies):
                title = title_prefix if total == 1 else f"{title_prefix} ({idx + 1}/{total})"
                rendered = f"<b>{html.escape(title)}</b>\n{markdownish_to_html(body)}"
                if len(rendered) <= self.cfg.max_telegram_message_length:
                    continue
                left, right = self._split_assistant_body(body)
                bodies = [*bodies[:idx], left, right, *bodies[idx + 1 :]]
                break
            else:
                return [
                    (
                        f"<b>{html.escape(title_prefix if total == 1 else f'{title_prefix} ({idx + 1}/{total})')}</b>\n"
                        f"{markdownish_to_html(body)}"
                    )
                    for idx, body in enumerate(bodies)
                ]

    def _split_assistant_body(self, body: str) -> tuple[str, str]:
        lines = body.splitlines()
        if len(lines) > 1:
            midpoint = len(lines) // 2
            left = "\n".join(lines[:midpoint]).strip()
            right = "\n".join(lines[midpoint:]).strip()
            if left and right:
                return left, right

        midpoint = max(1, len(body) // 2)
        left = body[:midpoint].rstrip()
        right = body[midpoint:].lstrip()
        if not right:
            right = body[-1:]
            left = body[:-1].rstrip() or body[:1]
        return left, right

    async def _send_diffs(self, update: Update, context: ContextTypes.DEFAULT_TYPE, diffs) -> None:
        for file_diff in diffs:
            if self.cfg.enable_sensitive_diff_filter and is_sensitive_path(file_diff.path):
                await send_text(update, context, f"{file_diff.path}\nThis file contains sensitive content and was omitted.")
                continue
            for chunk in chunk_fenced_diff(
                file_diff.path,
                file_diff.diff,
                self.cfg.max_telegram_message_length,
            ):
                await send_code_block(update, context, chunk.header, chunk.code, language=chunk.language)
