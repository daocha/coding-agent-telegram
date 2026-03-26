from __future__ import annotations

import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Optional, TypeVar

import portalocker

T = TypeVar("T")


class SessionStore:
    """Persist per-chat session state with file locking and crash-safe writes."""

    def __init__(self, state_file: Path, backup_file: Path) -> None:
        self.state_file = state_file
        self.backup_file = backup_file
        self.temp_file = state_file.with_suffix(state_file.suffix + ".tmp")
        self.lock_file = state_file.with_suffix(state_file.suffix + ".lock")

    def _now(self) -> str:
        return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")

    def _default_state(self) -> dict[str, Any]:
        return {"chats": {}, "trusted_projects": []}

    def _ensure_paths(self) -> None:
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        self.lock_file.parent.mkdir(parents=True, exist_ok=True)

    def _chat_key(self, bot_id: str, chat_id: int) -> str:
        return f"{bot_id}:{chat_id}"

    def _get_chat_data(
        self,
        state: dict[str, Any],
        bot_id: str,
        chat_id: int,
        *,
        create: bool = False,
    ) -> tuple[Optional[dict[str, Any]], bool]:
        chats = state.setdefault("chats", {})
        scoped_key = self._chat_key(bot_id, chat_id)
        chat_data = chats.get(scoped_key)
        if chat_data is not None:
            return chat_data, False

        # Migrate legacy single-bot state to the first bot that touches it.
        legacy_key = str(chat_id)
        legacy_data = chats.get(legacy_key)
        if legacy_data is not None:
            chats[scoped_key] = legacy_data
            del chats[legacy_key]
            return legacy_data, True

        if create:
            chat_data = {"sessions": {}}
            chats[scoped_key] = chat_data
            return chat_data, True

        return None, False

    def _load_unlocked(self) -> dict[str, Any]:
        if not self.state_file.exists():
            return self._default_state()
        try:
            raw = self.state_file.read_text(encoding="utf-8").strip()
        except OSError:
            return self._default_state()
        if not raw:
            return self._default_state()
        try:
            loaded = json.loads(raw)
        except json.JSONDecodeError:
            return self._default_state()
        if not isinstance(loaded, dict):
            return self._default_state()
        return loaded

    def load(self) -> dict[str, Any]:
        self._ensure_paths()
        with portalocker.Lock(str(self.lock_file), timeout=5):
            return self._load_unlocked()

    def _save_unlocked(self, state: dict[str, Any]) -> None:
        serialized = json.dumps(state, indent=2, ensure_ascii=False)
        if self.state_file.exists():
            shutil.copy2(self.state_file, self.backup_file)
        self.temp_file.write_text(serialized + "\n", encoding="utf-8")
        self.temp_file.replace(self.state_file)

    def save(self, state: dict[str, Any]) -> None:
        self._ensure_paths()
        with portalocker.Lock(str(self.lock_file), timeout=5):
            self._save_unlocked(state)

    def _mutate_state(self, fn: Callable[[dict[str, Any]], T]) -> T:
        self._ensure_paths()
        with portalocker.Lock(str(self.lock_file), timeout=5):
            state = self._load_unlocked()
            result = fn(state)
            self._save_unlocked(state)
            return result

    def _mutate_chat_data(
        self,
        bot_id: str,
        chat_id: int,
        fn: Callable[[dict[str, Any]], T],
        *,
        create: bool = False,
    ) -> Optional[T]:
        """Mutate a single chat scope and return `None` when that scope does not exist."""

        def mutate(state: dict[str, Any]) -> Optional[T]:
            chat_data, _ = self._get_chat_data(state, bot_id, chat_id, create=create)
            if chat_data is None:
                return None
            return fn(chat_data)

        return self._mutate_state(mutate)

    def _write_session_record(
        self,
        sessions: dict[str, Any],
        session_id: str,
        *,
        session_name: str,
        project_folder: str,
        provider: str,
        branch_name: Optional[str],
    ) -> dict[str, str]:
        now = self._now()
        sessions[session_id] = {
            "name": session_name,
            "project_folder": project_folder,
            "provider": provider,
            "branch_name": branch_name or "",
            "created_at": now,
            "updated_at": now,
        }
        return sessions[session_id]

    def trust_project(self, project_folder: str) -> None:
        def mutate(state: dict[str, Any]) -> None:
            trusted_projects = state.setdefault("trusted_projects", [])
            if project_folder not in trusted_projects:
                trusted_projects.append(project_folder)
                trusted_projects.sort()

        self._mutate_state(mutate)

    def is_project_trusted(self, project_folder: str) -> bool:
        state = self.load()
        trusted_projects = state.setdefault("trusted_projects", [])
        return project_folder in trusted_projects

    def set_current_project_folder(self, bot_id: str, chat_id: int, project_folder: str) -> None:
        def mutate(chat_data: dict[str, Any]) -> None:
            chat_data["current_project_folder"] = project_folder

        self._mutate_chat_data(bot_id, chat_id, mutate, create=True)

    def set_current_branch(self, bot_id: str, chat_id: int, branch_name: Optional[str]) -> None:
        def mutate(chat_data: dict[str, Any]) -> None:
            if branch_name:
                chat_data["current_branch"] = branch_name
            else:
                chat_data.pop("current_branch", None)

        self._mutate_chat_data(bot_id, chat_id, mutate, create=True)

    def set_current_provider(self, bot_id: str, chat_id: int, provider: str) -> None:
        def mutate(chat_data: dict[str, Any]) -> None:
            chat_data["current_provider"] = provider

        self._mutate_chat_data(bot_id, chat_id, mutate, create=True)

    def set_pending_action(self, bot_id: str, chat_id: int, pending_action: Optional[dict[str, Any]]) -> None:
        def mutate(chat_data: dict[str, Any]) -> None:
            if pending_action:
                chat_data["pending_action"] = pending_action
            else:
                chat_data.pop("pending_action", None)

        self._mutate_chat_data(bot_id, chat_id, mutate, create=True)

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
        def mutate(chat_data: dict[str, Any]) -> None:
            sessions = chat_data.setdefault("sessions", {})
            self._write_session_record(
                sessions,
                session_id,
                session_name=session_name,
                project_folder=project_folder,
                provider=provider,
                branch_name=branch_name,
            )
            chat_data["active_session_id"] = session_id
            chat_data["current_project_folder"] = project_folder
            chat_data["current_provider"] = provider
            if branch_name:
                chat_data["current_branch"] = branch_name

        self._mutate_chat_data(bot_id, chat_id, mutate, create=True)

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
        def mutate(chat_data: dict[str, Any]) -> None:
            sessions = chat_data.setdefault("sessions", {})
            sessions.pop(old_session_id, None)
            self._write_session_record(
                sessions,
                new_session_id,
                session_name=session_name,
                project_folder=project_folder,
                provider=provider,
                branch_name=branch_name,
            )
            chat_data["active_session_id"] = new_session_id
            chat_data["current_project_folder"] = project_folder
            chat_data["current_provider"] = provider
            if branch_name:
                chat_data["current_branch"] = branch_name

        self._mutate_chat_data(bot_id, chat_id, mutate, create=True)

    def rebind_session(
        self,
        bot_id: str,
        chat_id: int,
        old_session_id: str,
        new_session_id: str,
    ) -> bool:
        def mutate(chat_data: dict[str, Any]) -> bool:
            sessions = chat_data.setdefault("sessions", {})
            session = sessions.get(old_session_id)
            if session is None:
                return False
            if old_session_id == new_session_id:
                session["updated_at"] = self._now()
                return True

            rebound = dict(session)
            rebound["updated_at"] = self._now()
            sessions.pop(old_session_id, None)
            sessions[new_session_id] = rebound
            if chat_data.get("active_session_id") == old_session_id:
                chat_data["active_session_id"] = new_session_id
            return True

        result = self._mutate_chat_data(bot_id, chat_id, mutate)
        return False if result is None else result

    def list_sessions(self, bot_id: str, chat_id: int) -> dict[str, dict[str, str]]:
        self._ensure_paths()
        with portalocker.Lock(str(self.lock_file), timeout=5):
            state = self._load_unlocked()
            chat_data, migrated = self._get_chat_data(state, bot_id, chat_id)
            if migrated:
                self._save_unlocked(state)
            return {} if chat_data is None else dict(chat_data.get("sessions", {}))

    def set_active_session_branch(self, bot_id: str, chat_id: int, branch_name: str) -> None:
        def mutate(chat_data: dict[str, Any]) -> None:
            active_session_id = chat_data.get("active_session_id")
            if not active_session_id:
                return
            session = chat_data.get("sessions", {}).get(active_session_id)
            if not session:
                return
            session["branch_name"] = branch_name
            session["updated_at"] = self._now()
            chat_data["current_branch"] = branch_name

        self._mutate_chat_data(bot_id, chat_id, mutate)

    def get_chat_state(self, bot_id: str, chat_id: int) -> dict[str, Any]:
        self._ensure_paths()
        with portalocker.Lock(str(self.lock_file), timeout=5):
            state = self._load_unlocked()
            chat_data, migrated = self._get_chat_data(state, bot_id, chat_id)
            if migrated:
                self._save_unlocked(state)
            return {} if chat_data is None else dict(chat_data)

    def get_session(self, bot_id: str, chat_id: int, session_id: str) -> Optional[dict[str, str]]:
        return self.list_sessions(bot_id, chat_id).get(session_id)

    def switch_session(self, bot_id: str, chat_id: int, session_id: str) -> bool:
        def mutate(chat_data: dict[str, Any]) -> bool:
            session = chat_data.get("sessions", {}).get(session_id)
            if not session:
                return False

            chat_data["active_session_id"] = session_id
            chat_data["current_project_folder"] = session["project_folder"]
            chat_data["current_provider"] = session.get("provider", "codex")
            if session.get("branch_name"):
                chat_data["current_branch"] = session["branch_name"]
            else:
                chat_data.pop("current_branch", None)
            session["updated_at"] = self._now()
            return True

        result = self._mutate_chat_data(bot_id, chat_id, mutate)
        return False if result is None else result
