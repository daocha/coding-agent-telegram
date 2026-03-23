from __future__ import annotations

import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

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
        return {"chats": {}, "trusted_projects": []}

    def _chat_key(self, bot_id: str, chat_id: int) -> str:
        return f"{bot_id}:{chat_id}"

    def _get_chat_data(
        self,
        state: dict[str, Any],
        bot_id: str,
        chat_id: int,
        *,
        create: bool = False,
    ) -> Optional[dict[str, Any]]:
        chats = state.setdefault("chats", {})
        scoped_key = self._chat_key(bot_id, chat_id)
        chat_data = chats.get(scoped_key)
        if chat_data is not None:
            return chat_data

        # Migrate legacy single-bot state to the first bot that touches it.
        legacy_key = str(chat_id)
        legacy_data = chats.get(legacy_key)
        if legacy_data is not None:
            chats[scoped_key] = legacy_data
            del chats[legacy_key]
            self.save(state)
            return legacy_data

        if create:
            chat_data = {"sessions": {}}
            chats[scoped_key] = chat_data
            return chat_data

        return None

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

    def trust_project(self, project_folder: str) -> None:
        state = self.load()
        trusted_projects = state.setdefault("trusted_projects", [])
        if project_folder not in trusted_projects:
            trusted_projects.append(project_folder)
            trusted_projects.sort()
            self.save(state)

    def is_project_trusted(self, project_folder: str) -> bool:
        state = self.load()
        trusted_projects = state.setdefault("trusted_projects", [])
        return project_folder in trusted_projects

    def set_current_project_folder(self, bot_id: str, chat_id: int, project_folder: str) -> None:
        state = self.load()
        chat_data = self._get_chat_data(state, bot_id, chat_id, create=True)
        chat_data["current_project_folder"] = project_folder
        self.save(state)

    def set_current_branch(self, bot_id: str, chat_id: int, branch_name: Optional[str]) -> None:
        state = self.load()
        chat_data = self._get_chat_data(state, bot_id, chat_id, create=True)
        if branch_name:
            chat_data["current_branch"] = branch_name
        else:
            chat_data.pop("current_branch", None)
        self.save(state)

    def create_session(
        self,
        bot_id: str,
        chat_id: int,
        session_id: str,
        session_name: str,
        project_folder: str,
        provider: str,
        branch_name: Optional[str] = None,
    ) -> None:
        state = self.load()
        chat_data = self._get_chat_data(state, bot_id, chat_id, create=True)
        now = self._now()
        chat_data.setdefault("sessions", {})[session_id] = {
            "name": session_name,
            "project_folder": project_folder,
            "provider": provider,
            "branch_name": branch_name or "",
            "created_at": now,
            "updated_at": now,
        }
        chat_data["active_session_id"] = session_id
        chat_data["current_project_folder"] = project_folder
        if branch_name:
            chat_data["current_branch"] = branch_name
        self.save(state)

    def replace_session(
        self,
        bot_id: str,
        chat_id: int,
        old_session_id: str,
        new_session_id: str,
        session_name: str,
        project_folder: str,
        provider: str,
        branch_name: Optional[str] = None,
    ) -> None:
        state = self.load()
        chat_data = self._get_chat_data(state, bot_id, chat_id, create=True)
        sessions = chat_data.setdefault("sessions", {})
        sessions.pop(old_session_id, None)
        now = self._now()
        sessions[new_session_id] = {
            "name": session_name,
            "project_folder": project_folder,
            "provider": provider,
            "branch_name": branch_name or "",
            "created_at": now,
            "updated_at": now,
        }
        chat_data["active_session_id"] = new_session_id
        chat_data["current_project_folder"] = project_folder
        if branch_name:
            chat_data["current_branch"] = branch_name
        self.save(state)

    def list_sessions(self, bot_id: str, chat_id: int) -> dict[str, dict[str, str]]:
        state = self.load()
        chat_data = self._get_chat_data(state, bot_id, chat_id)
        return {} if chat_data is None else chat_data.get("sessions", {})

    def set_active_session_branch(self, bot_id: str, chat_id: int, branch_name: str) -> None:
        state = self.load()
        chat_data = self._get_chat_data(state, bot_id, chat_id)
        if not chat_data:
            return
        active_session_id = chat_data.get("active_session_id")
        if not active_session_id:
            return
        session = chat_data.get("sessions", {}).get(active_session_id)
        if not session:
            return
        session["branch_name"] = branch_name
        session["updated_at"] = self._now()
        chat_data["current_branch"] = branch_name
        self.save(state)

    def get_chat_state(self, bot_id: str, chat_id: int) -> dict[str, Any]:
        state = self.load()
        chat_data = self._get_chat_data(state, bot_id, chat_id)
        return {} if chat_data is None else chat_data

    def switch_session(self, bot_id: str, chat_id: int, session_id: str) -> bool:
        state = self.load()
        chat_data = self._get_chat_data(state, bot_id, chat_id)
        if not chat_data:
            return False
        session = chat_data.get("sessions", {}).get(session_id)
        if not session:
            return False

        chat_data["active_session_id"] = session_id
        chat_data["current_project_folder"] = session["project_folder"]
        if session.get("branch_name"):
            chat_data["current_branch"] = session["branch_name"]
        session["updated_at"] = self._now()
        self.save(state)
        return True
