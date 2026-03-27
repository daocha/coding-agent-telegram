from pathlib import Path

import json

from coding_agent_telegram.session_store import SessionStore


def test_create_and_switch_session(tmp_path: Path):
    state = tmp_path / "state.json"
    backup = tmp_path / "state.json.bak"
    store = SessionStore(state, backup)

    store.set_current_project_folder("bot-a", 123, "backend")
    store.create_session("bot-a", 123, "sess_1", "backend-fix", "backend", "codex", branch_name="feature-1")

    sessions = store.list_sessions("bot-a", 123)
    assert "sess_1" in sessions
    assert sessions["sess_1"]["project_folder"] == "backend"
    assert sessions["sess_1"]["provider"] == "codex"
    assert sessions["sess_1"]["branch_name"] == "feature-1"

    assert store.switch_session("bot-a", 123, "sess_1")
    chat = store.get_chat_state("bot-a", 123)
    assert chat["active_session_id"] == "sess_1"
    assert chat["current_project_folder"] == "backend"
    assert chat["current_provider"] == "codex"
    assert chat["current_branch"] == "feature-1"


def test_set_current_provider_persists_in_chat_state(tmp_path: Path):
    state = tmp_path / "state.json"
    backup = tmp_path / "state.json.bak"
    store = SessionStore(state, backup)

    store.set_current_provider("bot-a", 123, "copilot")

    chat = store.get_chat_state("bot-a", 123)
    assert chat["current_provider"] == "copilot"


def test_set_pending_action_persists_and_clears(tmp_path: Path):
    state = tmp_path / "state.json"
    backup = tmp_path / "state.json.bak"
    store = SessionStore(state, backup)

    store.set_pending_action("bot-a", 123, {"kind": "message", "user_message": "hello"})
    assert store.get_chat_state("bot-a", 123)["pending_action"]["kind"] == "message"

    store.set_pending_action("bot-a", 123, None)
    assert "pending_action" not in store.get_chat_state("bot-a", 123)


def test_load_empty_state_file_returns_default_state(tmp_path: Path):
    state = tmp_path / "state.json"
    backup = tmp_path / "state.json.bak"
    state.touch()
    store = SessionStore(state, backup)

    assert store.load() == {"chats": {}, "trusted_projects": []}


def test_sessions_are_isolated_per_bot(tmp_path: Path):
    state = tmp_path / "state.json"
    backup = tmp_path / "state.json.bak"
    store = SessionStore(state, backup)

    store.create_session("bot-a", 123, "sess_a", "api", "backend", "codex")
    store.create_session("bot-b", 123, "sess_b", "web", "frontend", "codex")

    assert set(store.list_sessions("bot-a", 123)) == {"sess_a"}
    assert set(store.list_sessions("bot-b", 123)) == {"sess_b"}


def test_legacy_chat_state_is_migrated_to_first_bot_scope(tmp_path: Path):
    state = tmp_path / "state.json"
    backup = tmp_path / "state.json.bak"
    state.write_text(
        json.dumps(
            {
                "chats": {
                    "123": {
                        "active_session_id": "sess_1",
                        "current_project_folder": "backend",
                        "sessions": {
                            "sess_1": {
                                "name": "backend-fix",
                                "project_folder": "backend",
                                "provider": "codex",
                            }
                        },
                    }
                }
            }
        ),
        encoding="utf-8",
    )
    store = SessionStore(state, backup)

    chat_state = store.get_chat_state("bot-a", 123)

    assert chat_state["active_session_id"] == "sess_1"
    raw_state = store.load()
    assert "123" not in raw_state["chats"]
    assert "bot-a:123" in raw_state["chats"]


def test_trust_project_persists(tmp_path: Path):
    state = tmp_path / "state.json"
    backup = tmp_path / "state.json.bak"
    store = SessionStore(state, backup)

    store.trust_project("backend")

    assert store.is_project_trusted("backend") is True


def test_replace_session_does_not_duplicate_entries(tmp_path: Path):
    state = tmp_path / "state.json"
    backup = tmp_path / "state.json.bak"
    store = SessionStore(state, backup)

    store.create_session("bot-a", 123, "sess_old", "backend-fix", "backend", "codex")
    store.replace_session("bot-a", 123, "sess_old", "sess_new", "backend-fix", "backend", "codex")

    sessions = store.list_sessions("bot-a", 123)
    assert "sess_old" not in sessions
    assert "sess_new" in sessions
    assert len(sessions) == 1


def test_set_active_session_branch_updates_session_and_chat_state(tmp_path: Path):
    state = tmp_path / "state.json"
    backup = tmp_path / "state.json.bak"
    store = SessionStore(state, backup)

    store.create_session("bot-a", 123, "sess_1", "backend-fix", "backend", "codex", branch_name="main")
    store.set_active_session_branch("bot-a", 123, "feature-2")

    sessions = store.list_sessions("bot-a", 123)
    assert sessions["sess_1"]["branch_name"] == "feature-2"


def test_switch_session_returns_false_when_chat_state_is_missing(tmp_path: Path):
    state = tmp_path / "state.json"
    backup = tmp_path / "state.json.bak"
    store = SessionStore(state, backup)

    assert store.switch_session("bot-a", 123, "missing") is False


def test_rebind_session_returns_false_when_chat_state_is_missing(tmp_path: Path):
    state = tmp_path / "state.json"
    backup = tmp_path / "state.json.bak"
    store = SessionStore(state, backup)

    assert store.rebind_session("bot-a", 123, "old", "new") is False


# ---------------------------------------------------------------------------
# SessionStoreError — lock-timeout handling
# ---------------------------------------------------------------------------


def test_load_raises_session_store_error_on_lock_timeout(tmp_path, monkeypatch):
    """load() must raise SessionStoreError when portalocker cannot acquire the lock."""
    import portalocker

    from coding_agent_telegram.session_store import SessionStoreError

    state = tmp_path / "state.json"
    backup = tmp_path / "state.json.bak"
    store = SessionStore(state, backup)

    class _FailingLock:
        def __init__(self, *args, **kwargs):
            pass

        def __enter__(self):
            raise portalocker.LockException("simulated timeout")

        def __exit__(self, *args):
            pass

    monkeypatch.setattr(portalocker, "Lock", _FailingLock)

    import pytest

    with pytest.raises(SessionStoreError, match="temporarily locked"):
        store.load()


def test_save_raises_session_store_error_on_lock_timeout(tmp_path, monkeypatch):
    """save() must raise SessionStoreError when portalocker cannot acquire the lock."""
    import portalocker

    from coding_agent_telegram.session_store import SessionStoreError

    state = tmp_path / "state.json"
    backup = tmp_path / "state.json.bak"
    store = SessionStore(state, backup)

    class _FailingLock:
        def __init__(self, *args, **kwargs):
            pass

        def __enter__(self):
            raise portalocker.LockException("simulated timeout")

        def __exit__(self, *args):
            pass

    monkeypatch.setattr(portalocker, "Lock", _FailingLock)

    import pytest

    with pytest.raises(SessionStoreError, match="temporarily locked"):
        store.save({})
