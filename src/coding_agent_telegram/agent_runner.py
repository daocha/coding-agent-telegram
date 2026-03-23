from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass
class AgentRunResult:
    session_id: str | None
    success: bool
    assistant_text: str
    error_message: str | None
    raw_events: list[dict]


class MultiAgentRunner:
    """Runs supported local agent CLIs while preserving session behavior."""

    def __init__(self, codex_bin: str, copilot_bin: str, approval_policy: str, sandbox_mode: str) -> None:
        self.codex_bin = codex_bin
        self.copilot_bin = copilot_bin
        self.approval_policy = approval_policy
        self.sandbox_mode = sandbox_mode

    def _parse_jsonl(self, stdout: str) -> tuple[str | None, bool, str, str | None, list[dict]]:
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
            for key in ("session_id", "thread_id"):
                if isinstance(ev.get(key), str):
                    session_id = ev[key]
            if isinstance(ev.get("assistant_text"), str):
                assistant_text = ev["assistant_text"]
            if isinstance(ev.get("error"), str):
                error_message = ev["error"]
            if isinstance(ev.get("success"), bool):
                success = ev["success"]

        return session_id, success, assistant_text, error_message, events

    def _run(self, args: list[str]) -> AgentRunResult:
        proc = subprocess.run(args, capture_output=True, text=True, check=False)
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

    def _codex_base(self, project_path: Path, user_message: str) -> list[str]:
        return [
            "--json",
            "--cd",
            str(project_path),
            "-c",
            f"approval_policy={self.approval_policy}",
            "-c",
            f"sandbox_mode={self.sandbox_mode}",
            user_message,
        ]

    def _copilot_base(self, project_path: Path, user_message: str) -> list[str]:
        # Capability reservation for Copilot CLI. Mirrors secure constraints as a best-effort contract.
        return [
            "--json",
            "--cd",
            str(project_path),
            user_message,
        ]

    def create_session(self, provider: str, project_path: Path, user_message: str) -> AgentRunResult:
        if provider == "codex":
            args = [self.codex_bin, "exec", *self._codex_base(project_path, user_message)]
        elif provider == "copilot":
            args = [self.copilot_bin, "exec", *self._copilot_base(project_path, user_message)]
        else:
            return AgentRunResult(None, False, "", f"Unsupported provider: {provider}", [])
        return self._run(args)

    def resume_session(self, provider: str, session_id: str, project_path: Path, user_message: str) -> AgentRunResult:
        if provider == "codex":
            args = [self.codex_bin, "exec", "resume", session_id, *self._codex_base(project_path, user_message)]
        elif provider == "copilot":
            args = [self.copilot_bin, "exec", "resume", session_id, *self._copilot_base(project_path, user_message)]
        else:
            return AgentRunResult(None, False, "", f"Unsupported provider: {provider}", [])
        return self._run(args)
