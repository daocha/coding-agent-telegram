from __future__ import annotations

from datetime import datetime


class SessionCommonMixin:
    def _next_available_session_name(self, chat_id: int, base_name: str) -> str:
        existing_names = {
            data.get("name", "").strip().lower()
            for data in self.deps.store.list_sessions(self.deps.bot_id, chat_id).values()
            if data.get("name", "").strip()
        }
        if base_name.lower() not in existing_names:
            return base_name
        suffix = 1
        while True:
            candidate = f"{base_name}-{suffix}"
            if candidate.lower() not in existing_names:
                return candidate
            suffix += 1

    def _selected_provider(self, chat_state: dict[str, object]) -> str:
        provider = str(chat_state.get("current_provider") or "").strip().lower()
        return provider if provider in {"codex", "copilot"} else ""

    def _active_session_matches_current_context(self, chat_state: dict[str, object]) -> bool:
        active_session_id = chat_state.get("active_session_id")
        if not active_session_id:
            return False
        session = chat_state.get("sessions", {}).get(active_session_id)
        if not isinstance(session, dict):
            return False
        return (
            session.get("project_folder") == chat_state.get("current_project_folder")
            and session.get("provider", "codex") == self._selected_provider(chat_state)
        )

    def _pending_action(self, chat_id: int) -> dict[str, object] | None:
        chat_state = self.deps.store.get_chat_state(self.deps.bot_id, chat_id)
        pending_action = chat_state.get("pending_action")
        return pending_action if isinstance(pending_action, dict) else None

    def _store_pending_action(self, chat_id: int, pending_action: dict[str, object] | None) -> None:
        self.deps.store.set_pending_action(self.deps.bot_id, chat_id, pending_action)

    def _auto_session_name(self, project_folder: str, branch_name: str, provider: str, chat_id: int) -> str:
        branch_label = (branch_name or "current").replace("/", "-")
        base_name = f"{project_folder}-{branch_label}-{provider}"
        if self._next_available_session_name(chat_id, base_name) == base_name:
            return base_name
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        fallback_name = f"{base_name}-{timestamp}"
        return self._next_available_session_name(chat_id, fallback_name)
