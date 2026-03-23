from __future__ import annotations

import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import portalocker


class SessionStore:
    def __init__(self, state_file: Path, backup_file: Path) -> None:
        self.state_file = state_file
        self.backup_file = backup_file
        self.temp_file = state_file.with_suffix(state_file.suffix + ".tmp")
        self.lock_file = state_file.with_suffix(state_file.suffix + ".lock")

    def _now(self) -> str:
        return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")

    def _default_state(self) -> dict[str, Any]:
        return {"chats": {}}

    def load(self) -> dict[str, Any]:
        if not self.state_file.exists():
            return self._default_state()
        return json.loads(self.state_file.read_text(encoding="utf-8"))

    def save(self, state: dict[str, Any]) -> None:
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        self.lock_file.parent.mkdir(parents=True, exist_ok=True)
        serialized = json.dumps(state, indent=2, ensure_ascii=False)

        with portalocker.Lock(str(self.lock_file), timeout=5):
            if self.state_file.exists():
                shutil.copy2(self.state_file, self.backup_file)
            self.temp_file.write_text(serialized + "\n", encoding="utf-8")
            self.temp_file.replace(self.state_file)

    def set_current_project_folder(self, chat_id: int, project_folder: str) -> None:
        state = self.load()
        chat_data = state["chats"].setdefault(str(chat_id), {"sessions": {}})
        chat_data["current_project_folder"] = project_folder
        self.save(state)

    def create_session(self, chat_id: int, session_id: str, session_name: str, project_folder: str, provider: str) -> None:
        state = self.load()
        chat_data = state["chats"].setdefault(str(chat_id), {"sessions": {}})
        now = self._now()
        chat_data.setdefault("sessions", {})[session_id] = {
            "name": session_name,
            "project_folder": project_folder,
            "provider": provider,
            "created_at": now,
            "updated_at": now,
        }
        chat_data["active_session_id"] = session_id
        chat_data["current_project_folder"] = project_folder
        self.save(state)

    def list_sessions(self, chat_id: int) -> dict[str, dict[str, str]]:
        return self.load().get("chats", {}).get(str(chat_id), {}).get("sessions", {})

    def get_chat_state(self, chat_id: int) -> dict[str, Any]:
        return self.load().get("chats", {}).get(str(chat_id), {})

    def switch_session(self, chat_id: int, session_id: str) -> bool:
        state = self.load()
        chat_data = state.get("chats", {}).get(str(chat_id))
        if not chat_data:
            return False
        session = chat_data.get("sessions", {}).get(session_id)
        if not session:
            return False

        chat_data["active_session_id"] = session_id
        chat_data["current_project_folder"] = session["project_folder"]
        session["updated_at"] = self._now()
        self.save(state)
        return True
