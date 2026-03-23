from __future__ import annotations

import json
import os
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Tuple


@dataclass
class AgentRunResult:
    session_id: Optional[str]
    success: bool
    assistant_text: str
    error_message: Optional[str]
    raw_events: list[dict]


class MultiAgentRunner:
    """Runs supported local agent CLIs while preserving session behavior."""

    PROMPT_PREFIX = (
        "Refresh the workspace state from disk before making changes. "
        "Verify whether files currently exist in the project before claiming they do. "
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

    def _extract_assistant_text(self, event: object) -> str:
        if isinstance(event, str):
            return event
        if isinstance(event, list):
            return "\n".join(filter(None, [self._extract_assistant_text(item) for item in event]))
        if not isinstance(event, dict):
            return ""

        chunks: list[str] = []
        if isinstance(event.get("assistant_text"), str):
            chunks.append(event["assistant_text"])

        role = event.get("role")
        event_type = event.get("type")
        if role == "assistant" or event_type in {"message", "assistant_message", "output_text", "text"}:
            for key in ("text", "message", "content"):
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

    def _run(self, args: list[str], *, cwd: Optional[Path] = None, env: Optional[dict[str, str]] = None) -> AgentRunResult:
        proc = subprocess.run(args, capture_output=True, text=True, check=False, cwd=cwd, env=env)
        session_id, parsed_success, assistant_text, error_message, events = self._parse_jsonl(proc.stdout)

        success = proc.returncode == 0 and parsed_success
        if not success and not error_message:
            error_message = proc.stderr.strip() or "Agent command failed."

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
    ) -> AgentRunResult:
        with tempfile.NamedTemporaryFile(prefix="coding-agent-telegram-", suffix=".txt", delete=False) as handle:
            output_path = Path(handle.name)

        try:
            split_at = len(args) - tail_args
            result = self._run(
                [*args[:split_at], "--output-last-message", str(output_path), *args[split_at:]],
                cwd=cwd,
                env=env,
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

    def _codex_base(self, project_path: Path, user_message: str, skip_git_repo_check: bool) -> list[str]:
        args = []
        if self.codex_model:
            args.extend(["-m", self.codex_model])
        args.extend(
            [
            "--json",
            "--cd",
            str(project_path),
            "-c",
            f"approval_policy={self.approval_policy}",
            "-c",
            f"sandbox_mode={self.sandbox_mode}",
            f"{self.PROMPT_PREFIX}{user_message}",
            ]
        )
        if skip_git_repo_check:
            return ["--skip-git-repo-check", *args]
        return args

    def _codex_resume_base(self, user_message: str, skip_git_repo_check: bool) -> list[str]:
        args = []
        if self.codex_model:
            args.extend(["-m", self.codex_model])
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

    def _copilot_env(self, project_path: Path, skip_git_repo_check: bool) -> dict[str, str]:
        env = os.environ.copy()
        if skip_git_repo_check:
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
    ) -> AgentRunResult:
        if provider == "codex":
            args = [self.codex_bin, "exec", *self._codex_base(project_path, user_message, skip_git_repo_check)]
            return self._run_with_output_file(args, cwd=project_path, tail_args=1)
        elif provider == "copilot":
            args = [self.copilot_bin, *self._copilot_base(user_message, skip_git_repo_check)]
            return self._run(args, cwd=project_path, env=self._copilot_env(project_path, skip_git_repo_check))
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
    ) -> AgentRunResult:
        if provider == "codex":
            args = [self.codex_bin, "exec", "resume"]
            args.extend([*self._codex_resume_base(user_message, skip_git_repo_check)[:-1], session_id, user_message])
            return self._run_with_output_file(args, cwd=project_path, tail_args=2)
        elif provider == "copilot":
            args = [self.copilot_bin, f"--resume={session_id}", *self._copilot_base(user_message, skip_git_repo_check)]
            return self._run(args, cwd=project_path, env=self._copilot_env(project_path, skip_git_repo_check))
        else:
            return AgentRunResult(None, False, "", f"Unsupported provider: {provider}", [])
