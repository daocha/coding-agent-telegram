from __future__ import annotations

import re
from collections import deque
from pathlib import Path
from types import SimpleNamespace

from telegram.ext import ContextTypes

from coding_agent_telegram.i18n import translate
from coding_agent_telegram.telegram_sender import send_text


QUEUED_QUESTIONS_DIR = "queued_questions"


class QueueProcessingMixin:
    def _queue_dir(self, chat_id: int) -> Path:
        queue_dir = self.deps.cfg.app_internal_root / QUEUED_QUESTIONS_DIR / str(chat_id)
        queue_dir.mkdir(parents=True, exist_ok=True)
        return queue_dir

    def _queue_lock_path(self, queue_file: Path) -> Path:
        return queue_file.with_suffix(queue_file.suffix + ".lock")

    def _sanitize_queue_session_id(self, session_id: str) -> str:
        cleaned = re.sub(r"[^A-Za-z0-9_.-]+", "-", session_id.strip())
        return cleaned or "session"

    def _next_queue_file_path(self, chat_id: int) -> Path:
        queue_dir = self._queue_dir(chat_id)
        if chat_id not in self._chat_message_queue_files and chat_id not in self._chat_processing_queue_files:
            next_index = 0
        else:
            next_index = self._chat_next_queue_file_index.get(chat_id, -1) + 1
        self._chat_next_queue_file_index[chat_id] = next_index
        chat_state = self.deps.store.get_chat_state(self.deps.bot_id, chat_id)
        session_id = self._sanitize_queue_session_id(str(chat_state.get("active_session_id") or "session"))
        return queue_dir / f"{session_id}-queue-{next_index}.txt"

    def _read_queue_questions(self, queue_file: Path) -> list[str]:
        if not queue_file.exists():
            return []
        raw = queue_file.read_text(encoding="utf-8")
        pattern = re.compile(r"^\[Question (\d+)\]\n(.*?)\n\[End Question \1\]\s*$", re.MULTILINE | re.DOTALL)
        return [match.group(2).strip() for match in pattern.finditer(raw) if match.group(2).strip()]

    def _append_question_to_queue_file(self, queue_file: Path, user_message: str) -> int:
        questions = self._read_queue_questions(queue_file)
        next_number = len(questions) + 1
        with queue_file.open("a", encoding="utf-8") as fh:
            if queue_file.stat().st_size > 0:
                fh.write("\n")
            fh.write(f"[Question {next_number}]\n{user_message.strip()}\n[End Question {next_number}]\n")
        return next_number

    def _write_queue_questions(self, queue_file: Path, questions: list[str]) -> None:
        with queue_file.open("w", encoding="utf-8") as fh:
            for index, question in enumerate(questions, start=1):
                if index > 1:
                    fh.write("\n")
                fh.write(f"[Question {index}]\n{question.strip()}\n[End Question {index}]\n")

    def _enqueue_chat_message(self, chat_id: int, user_message: str) -> tuple[Path, int]:
        queue = self._chat_message_queue_files.setdefault(chat_id, deque())
        queue_file = queue[-1] if queue else self._next_queue_file_path(chat_id)
        if not queue:
            queue.append(queue_file)
        question_number = self._append_question_to_queue_file(queue_file, user_message)
        return queue_file, question_number

    def _dequeue_chat_message_file(self, chat_id: int) -> tuple[Path | None, list[str]]:
        queue = self._chat_message_queue_files.get(chat_id)
        if not queue:
            return None, []
        queue_file = queue.popleft()
        questions = self._read_queue_questions(queue_file)
        if not questions:
            if not queue:
                self._chat_message_queue_files.pop(chat_id, None)
            return None, []
        if not queue:
            self._chat_message_queue_files.pop(chat_id, None)
        return queue_file, questions

    def _queued_batch_prompt(self, queued_messages: list[str]) -> str:
        lines = ["Answer the following queued user questions in order."]
        for index, message in enumerate(queued_messages, start=1):
            lines.extend(["", f"[Question {index}]", message.strip(), f"[End Question {index}]"])
        return "\n".join(lines)

    def _preview_queued_message(self, message: str, *, max_chars: int = 100) -> str:
        stripped = " ".join(message.split())
        if len(stripped) <= max_chars:
            return stripped
        if max_chars <= 3:
            return stripped[:max_chars]
        return f"{stripped[: max_chars - 3]}..."

    def _queued_batch_notice(self, chat_id: int, queued_messages: list[str]) -> str:
        lines = [translate(self._chat_locale(chat_id), "queue.working_on_queued")]
        for index, message in enumerate(queued_messages, start=1):
            lines.append(f"{index}. {self._preview_queued_message(message)}")
        return "\n".join(lines)

    def _has_pending_queue_decision(self, chat_id: int) -> bool:
        return chat_id in self._chat_pending_queue_decisions

    def _run_result_was_aborted(self, result: object) -> bool:
        error_message = getattr(result, "error_message", None)
        return isinstance(error_message, str) and error_message.strip().startswith("Agent run aborted by")

    def _has_pending_queue_files(self, chat_id: int) -> bool:
        queue = self._chat_message_queue_files.get(chat_id)
        return bool(queue)

    async def _prompt_continue_queued_questions(self, chat_id: int, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not hasattr(context.bot, "send_message"):
            return
        from telegram import InlineKeyboardButton, InlineKeyboardMarkup

        locale = self._chat_locale(chat_id)
        await context.bot.send_message(
            chat_id=chat_id,
            text=translate(locale, "queue.continue_prompt"),
            reply_markup=InlineKeyboardMarkup(
                [[
                    InlineKeyboardButton(translate(locale, "queue.button_yes"), callback_data="queuecontinue:yes"),
                    InlineKeyboardButton(translate(locale, "queue.button_no"), callback_data="queuecontinue:no"),
                ]]
            ),
        )

    async def _prompt_queue_batch_decision(
        self,
        chat_id: int,
        context: ContextTypes.DEFAULT_TYPE,
        queued_messages: list[str],
    ) -> None:
        if not hasattr(context.bot, "send_message"):
            return
        from telegram import InlineKeyboardButton, InlineKeyboardMarkup

        locale = self._chat_locale(chat_id)
        lines = [
            translate(locale, "queue.multiple_ready"),
            "",
            translate(locale, "queue.here_are_questions"),
        ]
        for index, message in enumerate(queued_messages, start=1):
            lines.append(f"Q{index}: {self._preview_queued_message(message)}")
        lines.extend(
            [
                "",
                translate(locale, "queue.choose_how"),
                translate(locale, "queue.group_guidance_1"),
                translate(locale, "queue.group_guidance_2"),
            ]
        )
        await context.bot.send_message(
            chat_id=chat_id,
            text="\n".join(lines),
            reply_markup=InlineKeyboardMarkup(
                [[
                    InlineKeyboardButton(translate(locale, "queue.button_group"), callback_data="queuebatch:group"),
                    InlineKeyboardButton(translate(locale, "queue.button_single"), callback_data="queuebatch:single"),
                ]]
            ),
        )

    def _clear_chat_message_queue(self, chat_id: int) -> None:
        queue = self._chat_message_queue_files.pop(chat_id, deque())
        for queue_file in queue:
            queue_file.unlink(missing_ok=True)
            self._queue_lock_path(queue_file).unlink(missing_ok=True)
        processing_file = self._chat_processing_queue_files.pop(chat_id, None)
        if processing_file is not None:
            processing_file.unlink(missing_ok=True)
            self._queue_lock_path(processing_file).unlink(missing_ok=True)
        pending = self._chat_pending_queue_decisions.pop(chat_id, None)
        if pending is not None:
            pending[0].unlink(missing_ok=True)
            self._queue_lock_path(pending[0]).unlink(missing_ok=True)
        self._chat_next_queue_file_index.pop(chat_id, None)

    async def _dispatch_queued_questions(
        self,
        chat_id: int,
        context: ContextTypes.DEFAULT_TYPE,
        *,
        queue_file: Path,
        queued_messages: list[str],
        grouped: bool,
    ) -> bool:
        self._chat_processing_queue_files[chat_id] = queue_file
        self._queue_lock_path(queue_file).write_text("", encoding="utf-8")
        current_batch = queued_messages if grouped or len(queued_messages) <= 1 else queued_messages[:1]
        queued_notice = self._queued_batch_notice(chat_id, current_batch)
        queued_update = SimpleNamespace(
            effective_chat=SimpleNamespace(id=chat_id, type="private"),
            message=SimpleNamespace(text=queued_notice, photo=None, caption=None),
        )
        await send_text(queued_update, context, queued_notice)
        if grouped:
            user_message = self._queued_batch_prompt(queued_messages)
        else:
            user_message = queued_messages[0]
        queued_update = SimpleNamespace(
            effective_chat=SimpleNamespace(id=chat_id, type="private"),
            message=SimpleNamespace(text=user_message, photo=None, caption=None),
        )
        self.deps.store.set_pending_action(
            self.deps.bot_id,
            chat_id,
            {
                "kind": "message",
                "user_message": user_message,
            },
        )
        continued = await self._continue_pending_action(queued_update, context)
        if not continued:
            self._queue_lock_path(queue_file).unlink(missing_ok=True)
            self._chat_processing_queue_files.pop(chat_id, None)
            queue = self._chat_message_queue_files.setdefault(chat_id, deque())
            queue.appendleft(queue_file)
            return False
        if not grouped and len(queued_messages) > 1:
            remaining_queue_file = self._next_queue_file_path(chat_id)
            self._write_queue_questions(remaining_queue_file, queued_messages[1:])
            queue = self._chat_message_queue_files.setdefault(chat_id, deque())
            queue.appendleft(remaining_queue_file)
        return True

    async def _drain_chat_message_queue(self, chat_id: int, context: ContextTypes.DEFAULT_TYPE) -> None:
        if chat_id in self._chat_message_queue_draining:
            return
        self._chat_message_queue_draining.add(chat_id)
        try:
            while True:
                if self._is_project_busy(chat_id):
                    return
                last_result = self._last_run_results.pop(chat_id, None)
                if self._run_result_was_aborted(last_result) and self._has_pending_queue_files(chat_id):
                    processing_file = self._chat_processing_queue_files.get(chat_id)
                    if processing_file is not None:
                        processing_file.unlink(missing_ok=True)
                        self._queue_lock_path(processing_file).unlink(missing_ok=True)
                        self._chat_processing_queue_files.pop(chat_id, None)
                    await self._prompt_continue_queued_questions(chat_id, context)
                    return
                processing_file = self._chat_processing_queue_files.get(chat_id)
                if processing_file is not None:
                    processing_file.unlink(missing_ok=True)
                    self._queue_lock_path(processing_file).unlink(missing_ok=True)
                    self._chat_processing_queue_files.pop(chat_id, None)
                queue_file, queued_messages = self._dequeue_chat_message_file(chat_id)
                if queue_file is None or not queued_messages:
                    if chat_id not in self._chat_processing_queue_files and chat_id not in self._chat_message_queue_files:
                        self._chat_next_queue_file_index.pop(chat_id, None)
                    return
                if len(queued_messages) == 1:
                    continued = await self._dispatch_queued_questions(
                        chat_id,
                        context,
                        queue_file=queue_file,
                        queued_messages=queued_messages,
                        grouped=False,
                    )
                    if not continued:
                        return
                    continue
                self._chat_pending_queue_decisions[chat_id] = (queue_file, queued_messages)
                await self._prompt_queue_batch_decision(chat_id, context, queued_messages)
                return
        finally:
            self._chat_message_queue_draining.discard(chat_id)
