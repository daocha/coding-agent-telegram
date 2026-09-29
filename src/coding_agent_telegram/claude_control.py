from __future__ import annotations

import json
import logging
import threading
from concurrent.futures import Future
from typing import Callable

logger = logging.getLogger(__name__)

# Claude's bidirectional stream-json protocol, also used by the Agent SDK.
# Keep this adapter separate from the provider-neutral subprocess runner.
QuestionHandler = Callable[[dict], Future]


class ClaudeControl:
    def __init__(self, stdin, prompt: str, on_question: QuestionHandler):
        self.stdin = stdin
        self.prompt = prompt
        self.on_question = on_question
        self.lock = threading.RLock()
        self.pending: dict[str, Future] = {}
        self.initialized = False
        self.closed = False
        self.result_received = False
        self.session_state = None
        self.background_agents: set[str] = set()
        self.error: str | None = None

    @property
    def waiting(self) -> bool:
        with self.lock:
            return bool(self.pending)

    def write(self, event: dict) -> None:
        with self.lock:
            if not self.closed:
                self.stdin.write(json.dumps(event, ensure_ascii=False) + "\n")
                self.stdin.flush()

    def start(self) -> None:
        self.write({"type": "control_request", "request_id": "telegram-init",
                    "request": {"subtype": "initialize"}})

    def reply(self, request_id: str, response: dict) -> None:
        self.write({"type": "control_response", "response": {
            "subtype": "success", "request_id": request_id, "response": response}})

    def handle(self, event: dict) -> None:
        kind = event.get("type")
        if kind == "control_response":
            response = event.get("response", {})
            if response.get("request_id") == "telegram-init" and not self.initialized:
                if response.get("subtype") != "success":
                    self.error = "Claude could not initialize structured question support."
                    self.close()
                    return
                self.initialized = True
                self.write({"type": "user", "session_id": "", "parent_tool_use_id": None,
                            "message": {"role": "user", "content": self.prompt}})
        elif kind == "control_request":
            request_id = event.get("request_id")
            request = event.get("request", {})
            if not isinstance(request_id, str) or not isinstance(request, dict):
                return
            if request.get("subtype") != "can_use_tool" or request.get("tool_name") != "AskUserQuestion":
                # Never elevate tool permissions merely to support questions.
                self.reply(request_id, {"behavior": "deny", "message":
                           "This Telegram integration only handles AskUserQuestion requests. "
                           "Other tools must follow the configured permission rules."})
                return
            try:
                future = self.on_question(request.get("input", {}))
                with self.lock:
                    if self.closed:
                        future.cancel()
                        return
                    self.pending[request_id] = future
                future.add_done_callback(lambda result: self._answered(request_id, result))
            except Exception:
                logger.exception("Could not present Claude question.")
                self.reply(request_id, {"behavior": "deny", "message":
                           "The question could not be displayed. Explain this to the user in plain text."})
        elif kind == "control_cancel_request":
            with self.lock:
                future = self.pending.pop(event.get("request_id"), None)
            if future is not None:
                future.cancel()
        elif kind == "system":
            subtype = event.get("subtype")
            task_id = event.get("task_id")
            if subtype == "task_started" and event.get("task_type") in {"local_agent", "local_workflow"}:
                self.background_agents.add(task_id)
            elif subtype == "task_notification":
                self.background_agents.discard(task_id)
            elif subtype == "task_updated" and (event.get("patch") or {}).get("status") in {"completed", "failed", "stopped"}:
                self.background_agents.discard(task_id)
            elif subtype == "session_state_changed":
                self.session_state = event.get("state")
                if self.session_state == "idle" and self.result_received and not self.background_agents:
                    self.close()
        elif kind in {"assistant", "stream_event"} and not event.get("parent_tool_use_id"):
            self.result_received = False
        elif kind == "result":
            # A result can end one turn while background agents still owe a
            # follow-up. Keep their question channel open until the run is idle.
            self.result_received = True
            if self.session_state in (None, "idle") and not self.background_agents:
                self.close()

    def _answered(self, request_id: str, future: Future) -> None:
        with self.lock:
            if self.pending.pop(request_id, None) is None or self.closed:
                return
        if future.cancelled():
            return
        try:
            response = future.result()
        except Exception:
            logger.exception("Claude question UI failed.")
            response = {"behavior": "deny", "message":
                        "Telegram could not collect the answer. Explain this to the user in plain text."}
        try:
            self.reply(request_id, response)
        except (OSError, ValueError):
            logger.warning("Claude exited before the question answer could be returned.")

    def close(self) -> None:
        with self.lock:
            if self.closed:
                return
            self.closed = True
            pending = list(self.pending.values())
            self.pending.clear()
            try:
                self.stdin.close()
            except OSError:
                pass
        for future in pending:
            future.cancel()
