from pathlib import Path

from coding_agent_telegram.session_store import SessionStore


def test_create_and_switch_session(tmp_path: Path):
    state = tmp_path / "state.json"
    backup = tmp_path / "state.json.bak"
    store = SessionStore(state, backup)

    store.set_current_project_folder(123, "backend")
    store.create_session(123, "sess_1", "backend-fix", "backend", "codex")

    sessions = store.list_sessions(123)
    assert "sess_1" in sessions
    assert sessions["sess_1"]["project_folder"] == "backend"
    assert sessions["sess_1"]["provider"] == "codex"

    assert store.switch_session(123, "sess_1")
    chat = store.get_chat_state(123)
    assert chat["active_session_id"] == "sess_1"
    assert chat["current_project_folder"] == "backend"
