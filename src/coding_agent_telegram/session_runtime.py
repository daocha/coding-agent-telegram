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
from coding_agent_telegram.i18n import locale_from_update, translate
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
IMAGE_INSPECTION_PROMPT = "Open and inspect that image before answering."
IMAGE_NO_CAPTION_MESSAGE = "The user sent an image without additional text."
COMPACT_SUMMARY_PROMPT = (
    "Create a compact handoff summary for this session so work can continue in a fresh session with less context. "
    "Do not make code changes. Do not ask follow-up questions. Keep it concise but complete. "
    "Include: current goal, important decisions, files changed, unresolved issues, and the most useful next steps."
)
COMPACT_BOOTSTRAP_TEMPLATE = (
    "Use this compact handoff summary from the previous session as your starting context.\n\n"
    "{summary}\n\n"
    "Acknowledge that you have loaded the handoff summary and are ready to continue."
)

# Matches absolute filesystem paths (Unix and Windows styles) in error messages.
_ABSOLUTE_PATH_RE = re.compile(r"(?:^|(?<=\s)|(?<=[\"'(]))((?:/[^\s\"',;)]+)+|[A-Za-z]:\\[^\s\"',;)]+)")


def _reply_to_message_id(update: Update) -> int | None:
    message = getattr(update, "message", None)
    return getattr(message, "message_id", None)


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


def _sanitize_agent_error(text: str, *, error_code: str | None = None) -> str:
    """Remove absolute filesystem paths from agent error messages before sending to users."""
    if error_code == "agent_aborted":
        return "Agent run aborted by /abort."
    return _ABSOLUTE_PATH_RE.sub("<path>", text)


class PhotoAttachmentError(ValueError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


class PhotoAttachmentStore:
    MAX_PHOTO_BYTES = DEFAULT_MAX_PHOTO_ATTACHMENT_BYTES  # Telegram photos are capped to keep local storage bounded.

    def __init__(self, app_internal_root: Path) -> None:
        self.app_internal_root = app_internal_root

    def attachments_root(self, project_folder: str) -> Path:
        safe_project_folder = Path(project_folder).name
        return self.app_internal_root / PHOTO_ATTACHMENTS_DIR / safe_project_folder

    async def store_photo(self, update: Update, project_folder: str) -> Path:
        if update.message is None or not update.message.photo:
            raise PhotoAttachmentError("missing_photo", "Photo message does not contain a photo.")

        telegram_photo = update.message.photo[-1]
        declared_size = getattr(telegram_photo, "file_size", None)
        if isinstance(declared_size, int) and declared_size > self.MAX_PHOTO_BYTES:
            raise PhotoAttachmentError("photo_too_large", translate(locale_from_update(update), "runtime.photo_too_large"))

        telegram_file = await telegram_photo.get_file()
        content = bytes(await telegram_file.download_as_bytearray())
        if len(content) > self.MAX_PHOTO_BYTES:
            raise PhotoAttachmentError("photo_too_large", translate(locale_from_update(update), "runtime.photo_too_large"))
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

    def _locale(self, update: Update | None) -> str:
        return self.cfg.locale

    def _t(self, update: Update | None, key: str, **kwargs) -> str:
        return translate(self._locale(update), key, **kwargs)

    def _take_reply_to_message_id(self, reply_state: dict[str, int | None]) -> int | None:
        reply_to_message_id = reply_state.get("reply_to_message_id")
        reply_state["reply_to_message_id"] = None
        return reply_to_message_id

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
            await send_text(update, context, self._t(update, "common.no_active_session"))
            return None, None, None

        session = chat_state.get("sessions", {}).get(active_id)
        if not session:
            await send_text(update, context, self._t(update, "common.no_active_session"))
            return None, None, None

        project_path = resolve_project_path(self.cfg.workspace_root, session["project_folder"])
        if not project_path.exists() or not project_path.is_dir():
            await send_text(
                update,
                context,
                self._t(update, "common.project_folder_missing", project_folder=session["project_folder"]),
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
        suppress_working_notice: bool = False,
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
        reply_to_message_id = _reply_to_message_id(update)
        if not suppress_working_notice:
            await send_text(
                update,
                context,
                self._t(update, "runtime.working_on_it"),
                reply_to_message_id=reply_to_message_id,
            )
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
            stall_message=self._t(update, "runtime.active_run_stall"),
            progress_label=self._t(update, "runtime.live_agent_output"),
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
            error_text = (
                _sanitize_agent_error(result.error_message, error_code=getattr(result, "error_code", None))
                if result.error_message
                else self._t(update, "runtime.agent_run_failed")
            )
            if getattr(result, "error_code", None) == "agent_aborted":
                error_text = self._t(update, "runtime.agent_run_aborted")
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
                self._t(
                    update,
                    "runtime.resume_id_changed",
                    session_id=result.session_id,
                    session_name=switched_session_name,
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
            branch_name=branch_name,
            active_id=active_id,
            result=result,
            before_snapshot=before_snapshot,
            before=before,
            reply_to_message_id=reply_to_message_id,
        )
        return result

    async def compact_active_session(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
    ) -> AgentRunResult | None:
        chat_id = update.effective_chat.id
        active_id, session, project_path = await self._active_session_or_notify(update, context)
        if active_id is None or session is None or project_path is None:
            return None

        project_folder = session["project_folder"]
        provider = session.get("provider", "codex")
        branch_name = session.get("branch_name", "")
        session_name = session["name"]
        logger.info(
            "Compacting session '%s' (%s) for chat %s in project '%s' with provider '%s'.",
            session_name,
            active_id,
            chat_id,
            project_folder,
            provider,
        )

        if branch_name and self.git.is_git_repo(project_path):
            checkout = await self._checkout_branch(update, context, project_path, branch_name)
            if not checkout:
                return None

        await send_text(update, context, self._t(update, "runtime.compacting_session"))
        summary_result = await self.run_with_typing(
            update,
            context,
            self.agent_runner.resume_session,
            provider,
            active_id,
            project_path,
            COMPACT_SUMMARY_PROMPT,
            workspace_lock_key=project_folder,
            skip_git_repo_check=self.should_skip_git_repo_check(project_folder),
            stall_message=self._t(update, "runtime.active_run_stall"),
            progress_label=self._t(update, "runtime.live_agent_output"),
        )
        if summary_result is None:
            logger.info(
                "Compaction summary run was not started for chat %s on project '%s' because the workspace is busy.",
                chat_id,
                project_folder,
            )
            return None
        if not summary_result.success:
            error_text = (
                _sanitize_agent_error(summary_result.error_message, error_code=getattr(summary_result, "error_code", None))
                if summary_result.error_message
                else self._t(update, "runtime.agent_run_failed")
            )
            if getattr(summary_result, "error_code", None) == "agent_aborted":
                error_text = self._t(update, "runtime.agent_run_aborted")
            await send_text(update, context, error_text)
            return summary_result

        compact_summary = (summary_result.assistant_text or "").strip()
        if not compact_summary:
            await send_text(update, context, self._t(update, "runtime.compact_summary_missing"))
            return AgentRunResult(
                session_id=active_id,
                success=False,
                assistant_text="",
                error_message=None,
                raw_events=[],
                error_code="compact_summary_missing",
            )

        create_result = await self.run_with_typing(
            update,
            context,
            self.agent_runner.create_session,
            provider,
            project_path,
            COMPACT_BOOTSTRAP_TEMPLATE.format(summary=compact_summary),
            workspace_lock_key=project_folder,
            skip_git_repo_check=self.should_skip_git_repo_check(project_folder),
            stall_message=self._t(update, "runtime.replacement_session_stall"),
            progress_label=self._t(update, "runtime.live_agent_output"),
        )
        if create_result is None:
            return None
        if not create_result.success or not create_result.session_id:
            error_text = (
                _sanitize_agent_error(create_result.error_message, error_code=getattr(create_result, "error_code", None))
                if create_result.error_message
                else self._t(update, "runtime.agent_run_failed")
            )
            if getattr(create_result, "error_code", None) == "agent_aborted":
                error_text = self._t(update, "runtime.agent_run_aborted")
            await send_text(update, context, error_text)
            return create_result

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
        await send_text(
            update,
            context,
            self._t(
                update,
                "runtime.session_compacted",
                session_name=switched_session_name,
                session_id=create_result.session_id,
            ),
        )
        return create_result

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
            stall_message=self._t(update, "runtime.replacement_session_stall"),
            progress_label=self._t(update, "runtime.live_agent_output"),
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
            self._t(
                update,
                "runtime.resume_created_new",
                session_id=create_result.session_id,
                session_name=switched_session_name,
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
        branch_name: str,
        active_id: str,
        result,
        before_snapshot: dict[str, str | None],
        before: set[str],
        reply_to_message_id: int | None,
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
        reply_state = {"reply_to_message_id": reply_to_message_id}

        await self._send_assistant_chunks(
            update,
            context,
            result.assistant_text,
            provider=provider,
            reply_state=reply_state,
        )
        logger.info(
            "Completed run for chat %s on session '%s' (%s); %d changed file(s).",
            update.effective_chat.id,
            session_name,
            result.session_id or active_id,
            len(files),
        )
        await send_text(
            update,
            context,
            build_summary(
                session_name,
                project_folder,
                files,
                branch_name=branch_name or None,
                locale=self._locale(update),
            ),
            reply_to_message_id=self._take_reply_to_message_id(reply_state),
        )
        await self._send_diffs(update, context, diffs, reply_state=reply_state)

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
        reply_state: dict[str, int | None],
    ) -> None:
        if self.cfg.enable_secret_scrub_filter:
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
                    reply_to_message_id=self._take_reply_to_message_id(reply_state),
                )
                continue

            provider_label = "Copilot" if provider == "copilot" else "Codex"
            title_prefix = (
                self._t(update, "runtime.provider_output_single", provider=provider_label)
                if total == 1
                else self._t(
                    update,
                    "runtime.provider_output_index",
                    provider=provider_label,
                    index=index,
                    total=total,
                )
            )
            for message in self._chunk_assistant_prose(title_prefix, segment.text):
                await send_html_text(
                    update,
                    context,
                    message,
                    reply_to_message_id=self._take_reply_to_message_id(reply_state),
                )

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

    async def _send_diffs(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        diffs,
        *,
        reply_state: dict[str, int | None],
    ) -> None:
        for file_diff in diffs:
            if self.cfg.enable_sensitive_diff_filter and is_sensitive_path(file_diff.path):
                await send_text(
                    update,
                    context,
                    self._t(update, "runtime.sensitive_diff_omitted", path=file_diff.path),
                    reply_to_message_id=self._take_reply_to_message_id(reply_state),
                )
                continue
            for chunk in chunk_fenced_diff(
                file_diff.path,
                file_diff.diff,
                self.cfg.max_telegram_message_length,
                locale=self._locale(update),
            ):
                await send_code_block(
                    update,
                    context,
                    chunk.header,
                    chunk.code,
                    language=chunk.language,
                    reply_to_message_id=self._take_reply_to_message_id(reply_state),
                )
