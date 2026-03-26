from __future__ import annotations

import json
import logging
import os
import subprocess
import tempfile
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Optional, Sequence, Tuple, Union


logger = logging.getLogger(__name__)

AssistantEvent = Union[dict[str, Any], list[Any], str]


@dataclass
class AgentRunResult:
    session_id: Optional[str]
    success: bool
    assistant_text: str
    error_message: Optional[str]
    raw_events: list[dict]


@dataclass(frozen=True)
class AgentStallInfo:
    command: tuple[str, ...]
    elapsed_seconds: float
    idle_seconds: float
    seen_output: bool
    last_stderr: str


@dataclass(frozen=True)
class AgentProgressInfo:
    command: tuple[str, ...]
    elapsed_seconds: float
    text: str
    source: str


class MultiAgentRunner:
    """Runs supported local agent CLIs while preserving session behavior."""

    STALL_WARNING_AFTER_SECONDS = 60.0
    STALL_POLL_INTERVAL_SECONDS = 0.5
    PROGRESS_UPDATE_INTERVAL_SECONDS = 3.0
    PROMPT_PREFIX = (
        "Treat the current on-disk workspace as the source of truth. "
        "Re-read relevant files from disk before making claims or edits. "
    )

    def __init__(
        self,
        codex_bin: str,
        copilot_bin: str,
        approval_policy: str,
        sandbox_mode: str,
        codex_model: str = "",
        copilot_model: str = "",
        copilot_autopilot: bool = True,
        copilot_no_ask_user: bool = True,
        copilot_allow_all: bool = True,
        copilot_allow_all_tools: bool = False,
        copilot_allow_tools: tuple[str, ...] = (),
        copilot_deny_tools: tuple[str, ...] = (),
        copilot_available_tools: tuple[str, ...] = (),
    ) -> None:
        self.codex_bin = codex_bin
        self.copilot_bin = copilot_bin
        self.approval_policy = approval_policy
        self.sandbox_mode = sandbox_mode
        self.codex_model = codex_model.strip()
        self.copilot_model = copilot_model.strip()
        self.copilot_autopilot = copilot_autopilot
        self.copilot_no_ask_user = copilot_no_ask_user
        self.copilot_allow_all = copilot_allow_all
        self.copilot_allow_all_tools = copilot_allow_all_tools
        self.copilot_allow_tools = tuple(tool.strip() for tool in copilot_allow_tools if tool.strip())
        self.copilot_deny_tools = tuple(tool.strip() for tool in copilot_deny_tools if tool.strip())
        self.copilot_available_tools = tuple(tool.strip() for tool in copilot_available_tools if tool.strip())

    def _extract_assistant_text(self, event: AssistantEvent) -> str:
        if isinstance(event, str):
            return event
        if isinstance(event, list):
            return "\n".join(filter(None, [self._extract_assistant_text(item) for item in event]))
        if not isinstance(event, dict):
            return ""

        chunks: list[str] = []
        if isinstance(event.get("assistant_text"), str):
            chunks.append(event["assistant_text"])
        if isinstance(event.get("deltaContent"), str):
            chunks.append(event["deltaContent"])

        role = event.get("role")
        event_type = event.get("type")
        if role == "assistant" or event_type in {
            "message",
            "assistant_message",
            "assistant.message_delta",
            "message_delta",
            "output_text",
            "text",
        }:
            for key in ("text", "message", "content", "deltaContent"):
                value = event.get(key)
                extracted = self._extract_assistant_text(value)
                if extracted:
                    chunks.append(extracted)

        for item in event.values():
            if isinstance(item, (dict, list)):
                extracted = self._extract_assistant_text(item)
                if extracted:
                    chunks.append(extracted)

        unique_chunks: list[str] = []
        for chunk in chunks:
            cleaned = chunk.strip()
            if cleaned and cleaned not in unique_chunks:
                unique_chunks.append(cleaned)
        return "\n".join(unique_chunks)

    def _parse_jsonl(self, stdout: str) -> Tuple[Optional[str], bool, str, Optional[str], list[dict]]:
        events: list[dict] = []
        for line in stdout.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                events.append(json.loads(line))
            except json.JSONDecodeError:
                continue

        session_id = None
        success = True
        assistant_text = ""
        error_message = None

        for ev in events:
            for key in ("session_id", "thread_id", "sessionId", "threadId"):
                if isinstance(ev.get(key), str):
                    session_id = ev[key]
            extracted_text = self._extract_assistant_text(ev)
            if extracted_text:
                assistant_text = extracted_text
            if isinstance(ev.get("error"), str):
                error_message = ev["error"]
            if isinstance(ev.get("message"), str) and ev.get("type") == "error":
                error_message = ev["message"]
            if isinstance(ev.get("success"), bool):
                success = ev["success"]

        return session_id, success, assistant_text, error_message, events

    def _extract_progress_text(self, chunk: str, *, is_stderr: bool) -> str:
        stripped = chunk.strip()
        if not stripped:
            return ""
        if is_stderr:
            return stripped
        try:
            event = json.loads(stripped)
        except json.JSONDecodeError:
            return stripped

        extracted = self._extract_assistant_text(event)
        if extracted:
            return extracted
        for key in ("message", "error", "status", "text"):
            value = event.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
        return stripped

    def _run(
        self,
        args: list[str],
        *,
        cwd: Optional[Path] = None,
        env: Optional[dict[str, str]] = None,
        on_stall: Optional[Callable[[AgentStallInfo], None]] = None,
        on_progress: Optional[Callable[[AgentProgressInfo], None]] = None,
    ) -> AgentRunResult:
        proc = subprocess.Popen(
            args,
            cwd=cwd,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

        stdout_chunks: list[str] = []
        stderr_chunks: list[str] = []
        state_lock = threading.Lock()
        start_time = time.monotonic()
        last_activity = start_time
        last_progress_at = start_time
        seen_output = False
        last_stderr = ""
        last_progress_text = ""

        def record_activity(chunk: str, *, is_stderr: bool) -> None:
            nonlocal last_activity, seen_output, last_stderr, last_progress_at, last_progress_text
            if not chunk:
                return
            now = time.monotonic()
            with state_lock:
                last_activity = now
                seen_output = True
                if is_stderr and chunk.strip():
                    last_stderr = chunk.strip()
                progress_text = self._extract_progress_text(chunk, is_stderr=is_stderr)
                should_report_progress = bool(
                    on_progress
                    and progress_text
                    and progress_text != last_progress_text
                    and now - last_progress_at >= self.PROGRESS_UPDATE_INTERVAL_SECONDS
                )
                if should_report_progress:
                    last_progress_at = now
                    last_progress_text = progress_text
            if should_report_progress:
                info = AgentProgressInfo(
                    command=tuple(args),
                    elapsed_seconds=now - start_time,
                    text=progress_text,
                    source="stderr" if is_stderr else "stdout",
                )
                try:
                    on_progress(info)
                except Exception:
                    logger.exception("Agent progress callback failed.")

        def read_stream(stream, chunks: list[str], *, is_stderr: bool) -> None:
            try:
                for line in iter(stream.readline, ""):
                    chunks.append(line)
                    record_activity(line, is_stderr=is_stderr)
            finally:
                stream.close()

        stdout_thread = threading.Thread(
            target=read_stream,
            args=(proc.stdout, stdout_chunks),
            kwargs={"is_stderr": False},
            daemon=True,
        )
        stderr_thread = threading.Thread(
            target=read_stream,
            args=(proc.stderr, stderr_chunks),
            kwargs={"is_stderr": True},
            daemon=True,
        )
        stdout_thread.start()
        stderr_thread.start()

        stall_reported = False
        while proc.poll() is None:
            if on_stall and not stall_reported:
                now = time.monotonic()
                with state_lock:
                    idle_seconds = now - last_activity
                    seen_output_snapshot = seen_output
                    last_stderr_snapshot = last_stderr
                if idle_seconds >= self.STALL_WARNING_AFTER_SECONDS:
                    stall_reported = True
                    info = AgentStallInfo(
                        command=tuple(args),
                        elapsed_seconds=now - start_time,
                        idle_seconds=idle_seconds,
                        seen_output=seen_output_snapshot,
                        last_stderr=last_stderr_snapshot,
                    )
                    logger.warning(
                        "Agent command appears stalled after %.1fs without output: %s",
                        info.idle_seconds,
                        " ".join(args[:3]),
                    )
                    try:
                        on_stall(info)
                    except Exception:
                        logger.exception("Agent stall callback failed.")
            time.sleep(self.STALL_POLL_INTERVAL_SECONDS)

        stdout_thread.join()
        stderr_thread.join()
        stdout = "".join(stdout_chunks)
        stderr = "".join(stderr_chunks)
        session_id, parsed_success, assistant_text, error_message, events = self._parse_jsonl(stdout)

        success = proc.returncode == 0 and parsed_success
        if not success and not error_message:
            error_message = stderr.strip() or "Agent command failed."

        return AgentRunResult(
            session_id=session_id,
            success=success,
            assistant_text=assistant_text,
            error_message=error_message,
            raw_events=events,
        )

    def _run_with_output_file(
        self,
        args: list[str],
        *,
        cwd: Path,
        tail_args: int,
        env: Optional[dict[str, str]] = None,
        on_stall: Optional[Callable[[AgentStallInfo], None]] = None,
        on_progress: Optional[Callable[[AgentProgressInfo], None]] = None,
    ) -> AgentRunResult:
        with tempfile.NamedTemporaryFile(prefix="coding-agent-telegram-", suffix=".txt", delete=False) as handle:
            output_path = Path(handle.name)

        try:
            split_at = len(args) - tail_args
            result = self._run(
                [*args[:split_at], "--output-last-message", str(output_path), *args[split_at:]],
                cwd=cwd,
                env=env,
                on_stall=on_stall,
                on_progress=on_progress,
            )
            if output_path.exists():
                output_text = output_path.read_text(encoding="utf-8").strip()
                if output_text:
                    result.assistant_text = output_text
            return result
        finally:
            try:
                os.unlink(output_path)
            except FileNotFoundError:
                pass

    def _codex_base(
        self,
        project_path: Path,
        user_message: str,
        skip_git_repo_check: bool,
        image_paths: Sequence[Path] = (),
    ) -> list[str]:
        args = []
        if self.codex_model:
            args.extend(["-m", self.codex_model])
        for image_path in image_paths:
            args.extend(["--image", str(image_path)])
        args.extend(
            [
            "-c",
            f"approval_policy={self.approval_policy}",
            "-c",
            f"sandbox_mode={self.sandbox_mode}",
            "--json",
            "--cd",
            str(project_path),
            f"{self.PROMPT_PREFIX}{user_message}",
            ]
        )
        if skip_git_repo_check:
            return ["--skip-git-repo-check", *args]
        return args

    def _codex_resume_base(
        self,
        user_message: str,
        skip_git_repo_check: bool,
        image_paths: Sequence[Path] = (),
    ) -> list[str]:
        args = []
        if self.codex_model:
            args.extend(["-m", self.codex_model])
        for image_path in image_paths:
            args.extend(["--image", str(image_path)])
        args.extend(
            [
                "-c",
                f"approval_policy={self.approval_policy}",
                "-c",
                f"sandbox_mode={self.sandbox_mode}",
                "--json",
                f"{self.PROMPT_PREFIX}{user_message}",
            ]
        )
        if skip_git_repo_check:
            return ["--skip-git-repo-check", *args]
        return args

    def _codex_resume_args(
        self,
        session_id: str,
        user_message: str,
        skip_git_repo_check: bool,
        image_paths: Sequence[Path] = (),
    ) -> list[str]:
        return [
            *self._codex_resume_base(user_message, skip_git_repo_check, image_paths)[:-1],
            session_id,
            f"{self.PROMPT_PREFIX}{user_message}",
        ]

    def _copilot_env(self, project_path: Path, skip_git_repo_check: bool) -> dict[str, str]:
        env = os.environ.copy()
        if skip_git_repo_check and not env.get("COPILOT_HOME"):
            env["COPILOT_HOME"] = str(project_path / ".copilot")
        return env

    def _copilot_base(self, user_message: str, skip_git_repo_check: bool) -> list[str]:
        args = []
        if self.copilot_model:
            args.extend(["--model", self.copilot_model])
        if self.copilot_autopilot:
            args.append("--autopilot")
        if self.copilot_no_ask_user:
            args.append("--no-ask-user")
        if self.copilot_allow_all:
            args.append("--allow-all")
        elif self.copilot_allow_all_tools or skip_git_repo_check:
            args.append("--allow-all-tools")
        for tool in self.copilot_allow_tools:
            args.extend(["--allow-tool", tool])
        for tool in self.copilot_deny_tools:
            args.extend(["--deny-tool", tool])
        if self.copilot_available_tools:
            args.extend(["--available-tools", ",".join(self.copilot_available_tools)])
        args.extend(
            [
            "--output-format=json",
            "--prompt",
            f"{self.PROMPT_PREFIX}{user_message}",
            ]
        )
        return args

    def create_session(
        self,
        provider: str,
        project_path: Path,
        user_message: str,
        *,
        skip_git_repo_check: bool = False,
        image_paths: Sequence[Path] = (),
        on_stall: Optional[Callable[[AgentStallInfo], None]] = None,
        on_progress: Optional[Callable[[AgentProgressInfo], None]] = None,
    ) -> AgentRunResult:
        if provider == "codex":
            args = [
                self.codex_bin,
                "exec",
                *self._codex_base(project_path, user_message, skip_git_repo_check, image_paths),
            ]
            return self._run_with_output_file(
                args,
                cwd=project_path,
                tail_args=1,
                on_stall=on_stall,
                on_progress=on_progress,
            )
        elif provider == "copilot":
            if image_paths:
                return AgentRunResult(None, False, "", "Image attachments are not supported for Copilot sessions.", [])
            args = [self.copilot_bin, *self._copilot_base(user_message, skip_git_repo_check)]
            return self._run(
                args,
                cwd=project_path,
                env=self._copilot_env(project_path, skip_git_repo_check),
                on_stall=on_stall,
                on_progress=on_progress,
            )
        else:
            return AgentRunResult(None, False, "", f"Unsupported provider: {provider}", [])

    def resume_session(
        self,
        provider: str,
        session_id: str,
        project_path: Path,
        user_message: str,
        *,
        skip_git_repo_check: bool = False,
        image_paths: Sequence[Path] = (),
        on_stall: Optional[Callable[[AgentStallInfo], None]] = None,
        on_progress: Optional[Callable[[AgentProgressInfo], None]] = None,
    ) -> AgentRunResult:
        if provider == "codex":
            args = [
                self.codex_bin,
                "exec",
                "resume",
                *self._codex_resume_args(session_id, user_message, skip_git_repo_check, image_paths),
            ]
            return self._run_with_output_file(
                args,
                cwd=project_path,
                tail_args=2,
                on_stall=on_stall,
                on_progress=on_progress,
            )
        elif provider == "copilot":
            if image_paths:
                return AgentRunResult(None, False, "", "Image attachments are not supported for Copilot sessions.", [])
            args = [self.copilot_bin, f"--resume={session_id}", *self._copilot_base(user_message, skip_git_repo_check)]
            return self._run(
                args,
                cwd=project_path,
                env=self._copilot_env(project_path, skip_git_repo_check),
                on_stall=on_stall,
                on_progress=on_progress,
            )
        else:
            return AgentRunResult(None, False, "", f"Unsupported provider: {provider}", [])
