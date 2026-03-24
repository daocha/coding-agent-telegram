from __future__ import annotations

import asyncio
import hashlib
import html
import logging
from pathlib import Path
from typing import Awaitable, Callable, Sequence

from telegram import Update
from telegram.ext import ContextTypes

from coding_agent_telegram.agent_runner import MultiAgentRunner
from coding_agent_telegram.config import AppConfig
from coding_agent_telegram.diff_utils import (
    INTERNAL_APP_DIR,
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


class PhotoAttachmentStore:
    ATTACHMENTS_DIR = "telegram_attachments"

    def attachments_root(self, project_path: Path) -> Path:
        return project_path / INTERNAL_APP_DIR / self.ATTACHMENTS_DIR

    async def store_photo(self, update: Update, project_path: Path) -> Path:
        if update.message is None or not update.message.photo:
            raise ValueError("Photo message does not contain a photo.")

        telegram_photo = update.message.photo[-1]
        telegram_file = await telegram_photo.get_file()
        content = bytes(await telegram_file.download_as_bytearray())
        suffix = Path(telegram_file.file_path or "image.jpg").suffix.lower() or ".jpg"
        if suffix not in {".jpg", ".jpeg", ".png", ".webp", ".gif"}:
            suffix = ".jpg"
        digest = hashlib.sha256(content).hexdigest()

        attachments_root = self.attachments_root(project_path)
        attachments_root.mkdir(parents=True, exist_ok=True)
        target = attachments_root / f"{digest}{suffix}"
        if not target.exists():
            target.write_bytes(content)
        return target

    def build_prompt(self, attachment_path: Path, project_path: Path, caption: str) -> str:
        rel_path = attachment_path.relative_to(project_path).as_posix()
        lines = [
            f"An image is attached at {rel_path}.",
            "Open and inspect that image before answering.",
        ]
        caption = caption.strip()
        if caption:
            lines.extend(["", "User caption:", caption])
        else:
            lines.extend(["", "The user sent an image without additional text."])
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

    async def run_active_session(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        *,
        user_message: str,
        image_paths: Sequence[Path] = (),
    ) -> None:
        chat_id = update.effective_chat.id
        chat_state = self.store.get_chat_state(self.bot_id, chat_id)
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
        project_path = resolve_project_path(self.cfg.workspace_root, project_folder)
        branch_name = session.get("branch_name", "")
        logger.info(
            "Running message for chat %s on session '%s' (%s) in project '%s' with provider '%s'.",
            chat_id,
            session["name"],
            active_id,
            project_folder,
            provider,
        )

        if branch_name and self.git.is_git_repo(project_path):
            checkout = await self._checkout_branch(update, context, project_path, branch_name)
            if not checkout:
                return

        before_snapshot = snapshot_project_files(project_path)
        before = set(changed_files(project_path))
        await send_text(update, context, "Working on it...")
        result = await self.run_with_typing(
            update,
            context,
            self.agent_runner.resume_session,
            provider,
            active_id,
            project_path,
            user_message,
            skip_git_repo_check=self.should_skip_git_repo_check(project_folder),
            image_paths=image_paths,
        )
        result = await self._replace_invalid_session_if_needed(
            update,
            context,
            result=result,
            active_id=active_id,
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
            return
        if not result.success:
            logger.warning(
                "Agent run failed for chat %s on session '%s' (%s): %s",
                chat_id,
                session["name"],
                active_id,
                result.error_message or "unknown error",
            )
            await send_text(update, context, result.error_message or "Agent run failed.")
            return

        if result.session_id and result.session_id != active_id:
            switched_session_name = self._next_rotated_session_name(chat_id, session["name"])
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
                session["name"],
                active_id,
                switched_session_name,
                result.session_id,
            )
            await send_text(
                update,
                context,
                (
                    "Codex continued in a different session.\n"
                    f"Switched to: {switched_session_name}\n"
                    f"Session ID: {result.session_id}"
                ),
            )
            session_name = switched_session_name
            active_id = result.session_id
        else:
            session_name = session["name"]

        await self._send_run_results(
            update,
            context,
            session_name=session_name,
            project_folder=project_folder,
            project_path=project_path,
            active_id=active_id,
            result=result,
            before_snapshot=before_snapshot,
            before=before,
        )

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
            return result

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
            skip_git_repo_check=self.should_skip_git_repo_check(project_folder),
            image_paths=image_paths,
        )
        if not create_result.success or not create_result.session_id:
            return create_result

        self.store.replace_session(
            self.bot_id,
            chat_id,
            active_id,
            create_result.session_id,
            session["name"],
            project_folder,
            provider,
            branch_name=branch_name,
        )
        logger.info(
            "Replaced session '%s' for chat %s: old=%s new=%s.",
            session["name"],
            chat_id,
            active_id,
            create_result.session_id,
        )
        await send_text(
            update,
            context,
            f"The previous session is no longer valid.\nA new session was created and the task continued.\nSession ID: {create_result.session_id}",
        )
        return create_result

    async def _send_run_results(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        *,
        session_name: str,
        project_folder: str,
        project_path: Path,
        active_id: str,
        result,
        before_snapshot: dict[str, str | None],
        before: set[str],
    ) -> None:
        after_snapshot = snapshot_project_files(project_path)
        after = set(changed_files(project_path))
        snapshot_files = changed_files_from_snapshots(before_snapshot, after_snapshot)
        files = sorted((after - before).union(snapshot_files))
        diffs = collect_diffs(project_path, files)
        snapshot_diffs_by_path = {
            file_diff.path: file_diff
            for file_diff in collect_snapshot_diffs(before_snapshot, after_snapshot, files)
        }
        diffs = self._merge_snapshot_diffs(diffs, snapshot_diffs_by_path)

        await self._send_assistant_chunks(update, context, result.assistant_text)
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
            if file_diff.diff:
                merged_diffs.append(file_diff)
                continue
            snapshot_diff = snapshot_diffs_by_path.get(file_diff.path)
            if snapshot_diff is not None:
                merged_diffs.append(snapshot_diff)
            else:
                merged_diffs.append(file_diff)
        return merged_diffs

    async def _send_assistant_chunks(self, update: Update, context: ContextTypes.DEFAULT_TYPE, assistant_text: str) -> None:
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

            title = "Codex output" if total == 1 else f"Codex output {index}/{total}"
            for chunk in chunk_plain_text(title, segment.text, self.cfg.max_telegram_message_length):
                title, body = (chunk.split("\n", 1) + [""])[:2]
                await send_html_text(update, context, f"<b>{html.escape(title)}</b>\n{markdownish_to_html(body)}")

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
