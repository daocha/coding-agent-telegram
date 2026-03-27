from pathlib import Path

import json
import pytest

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


# ---------------------------------------------------------------------------
# _load_unlocked: error handling branches
# ---------------------------------------------------------------------------


def test_load_unlocked_oserror_returns_default(tmp_path: Path, monkeypatch):
    """When the state file raises OSError on read, _load_unlocked should return default."""
    from coding_agent_telegram.session_store import SessionStore

    store = SessionStore(tmp_path / "state.json", tmp_path / "state.json.bak")
    store._ensure_paths()
    store.state_file.write_text("{}", encoding="utf-8")

    # Patch Path.read_text to raise OSError only for the state file
    original_read_text = store.state_file.__class__.read_text

    def fail_read(self, *args, **kwargs):
        if self == store.state_file:
            raise OSError("Permission denied")
        return original_read_text(self, *args, **kwargs)

    monkeypatch.setattr(store.state_file.__class__, "read_text", fail_read)

    result = store._load_unlocked()
    assert isinstance(result, dict)


def test_load_unlocked_invalid_json_returns_default(tmp_path: Path):
    """When state file contains invalid JSON, _load_unlocked should return default."""
    from coding_agent_telegram.session_store import SessionStore

    store = SessionStore(tmp_path / "state.json", tmp_path / "state.json.bak")
    store._ensure_paths()
    store.state_file.write_text("NOT JSON!!!", encoding="utf-8")

    result = store._load_unlocked()
    assert isinstance(result, dict)


def test_load_unlocked_non_dict_json_returns_default(tmp_path: Path):
    """When state file contains valid JSON but not a dict, return default."""
    import json
    from coding_agent_telegram.session_store import SessionStore

    store = SessionStore(tmp_path / "state.json", tmp_path / "state.json.bak")
    store._ensure_paths()
    store.state_file.write_text(json.dumps([1, 2, 3]), encoding="utf-8")

    result = store._load_unlocked()
    assert isinstance(result, dict)


# ---------------------------------------------------------------------------
# list_sessions and get_chat_state: lock errors raise SessionStoreError
# ---------------------------------------------------------------------------


def test_list_sessions_raises_session_store_error_on_lock_timeout(tmp_path, monkeypatch):
    """list_sessions must raise SessionStoreError when the lock cannot be acquired."""
    import portalocker
    from coding_agent_telegram.session_store import SessionStore, SessionStoreError

    store = SessionStore(tmp_path / "state.json", tmp_path / "state.json.bak")

    class FailLock:
        def __enter__(self):
            raise portalocker.LockException("locked")
        def __exit__(self, *args):
            pass

    monkeypatch.setattr(portalocker, "Lock", lambda *a, **kw: FailLock())

    with pytest.raises(SessionStoreError):
        store.list_sessions("bot1", 1)


def test_get_chat_state_raises_session_store_error_on_lock_timeout(tmp_path, monkeypatch):
    """get_chat_state must raise SessionStoreError when the lock cannot be acquired."""
    import portalocker
    from coding_agent_telegram.session_store import SessionStore, SessionStoreError

    store = SessionStore(tmp_path / "state.json", tmp_path / "state.json.bak")

    class FailLock:
        def __enter__(self):
            raise portalocker.LockException("locked")
        def __exit__(self, *args):
            pass

    monkeypatch.setattr(portalocker, "Lock", lambda *a, **kw: FailLock())

    with pytest.raises(SessionStoreError):
        store.get_chat_state("bot1", 1)


# ---------------------------------------------------------------------------
# save(): happy path (line 105)
# ---------------------------------------------------------------------------


def test_save_persists_state(tmp_path: Path):
    """save() must persist a state dict to disk."""
    import json

    store = SessionStore(tmp_path / "state.json", tmp_path / "state.json.bak")
    store._ensure_paths()

    state = {"chats": {}, "trusted_projects": [], "custom": True}
    store.save(state)

    loaded = json.loads(store.state_file.read_text(encoding="utf-8"))
    assert loaded.get("custom") is True


# ---------------------------------------------------------------------------
# _mutate_state: lock exception raises SessionStoreError (lines 117-118)
# ---------------------------------------------------------------------------


def test_mutate_state_raises_session_store_error_on_lock_timeout(tmp_path, monkeypatch):
    """_mutate_state must raise SessionStoreError when lock cannot be acquired."""
    import portalocker
    from coding_agent_telegram.session_store import SessionStore, SessionStoreError

    store = SessionStore(tmp_path / "state.json", tmp_path / "state.json.bak")

    class FailLock:
        def __enter__(self):
            raise portalocker.LockException("locked")
        def __exit__(self, *args):
            pass

    monkeypatch.setattr(portalocker, "Lock", lambda *a, **kw: FailLock())

    with pytest.raises(SessionStoreError):
        store._mutate_state(lambda state: None)


# ---------------------------------------------------------------------------
# create_session: with branch_name sets current_branch (line 257)
# ---------------------------------------------------------------------------


def test_create_session_with_branch_name_sets_current_branch(tmp_path: Path):
    """create_session with branch_name must store current_branch in chat state."""
    store = SessionStore(tmp_path / "state.json", tmp_path / "state.json.bak")
    store.create_session("bot1", 1, "ses1", "Session 1", "myproject", "codex", branch_name="feature-x")

    state = store.get_chat_state("bot1", 1)
    assert state.get("current_branch") == "feature-x"


# ---------------------------------------------------------------------------
# rebind_session: all branches (lines 269-283)
# ---------------------------------------------------------------------------


def test_rebind_session_returns_false_when_session_not_found(tmp_path: Path):
    """rebind_session must return False when old_session_id doesn't exist."""
    store = SessionStore(tmp_path / "state.json", tmp_path / "state.json.bak")
    store.create_session("bot1", 1, "ses1", "Session 1", "proj", "codex")

    result = store.rebind_session("bot1", 1, "nonexistent", "new-id")
    assert result is False


def test_rebind_session_same_id_updates_timestamp(tmp_path: Path):
    """rebind_session with old==new must update timestamp and return True."""
    store = SessionStore(tmp_path / "state.json", tmp_path / "state.json.bak")
    store.create_session("bot1", 1, "ses1", "Session 1", "proj", "codex")

    result = store.rebind_session("bot1", 1, "ses1", "ses1")
    assert result is True


def test_rebind_session_renames_active_session(tmp_path: Path):
    """rebind_session with a new ID must rename the session and update active_session_id."""
    store = SessionStore(tmp_path / "state.json", tmp_path / "state.json.bak")
    store.create_session("bot1", 1, "ses1", "Session 1", "proj", "codex")

    result = store.rebind_session("bot1", 1, "ses1", "ses2")
    assert result is True

    sessions = store.list_sessions("bot1", 1)
    assert "ses2" in sessions
    assert "ses1" not in sessions

    state = store.get_chat_state("bot1", 1)
    assert state.get("active_session_id") == "ses2"


# ---------------------------------------------------------------------------
# replace_session: with branch_name sets current_branch (line 257)
# ---------------------------------------------------------------------------


def test_replace_session_with_branch_name_sets_current_branch(tmp_path: Path):
    """replace_session with branch_name must store current_branch in chat state."""
    store = SessionStore(tmp_path / "state.json", tmp_path / "state.json.bak")
    store.create_session("bot1", 1, "ses1", "Session 1", "proj", "codex")
    store.replace_session("bot1", 1, "ses1", "ses2", "Session 2", "proj", "codex", branch_name="fix-x")

    state = store.get_chat_state("bot1", 1)
    assert state.get("current_branch") == "fix-x"


# ---------------------------------------------------------------------------
# switch_session: returns False when session not found (line 333)
# ---------------------------------------------------------------------------


def test_switch_session_returns_false_when_session_id_missing(tmp_path: Path):
    """switch_session must return False when the requested session_id doesn't exist."""
    store = SessionStore(tmp_path / "state.json", tmp_path / "state.json.bak")
    store.create_session("bot1", 1, "ses1", "Session 1", "proj", "codex")

    result = store.switch_session("bot1", 1, "nonexistent-id")
    assert result is False


# ---------------------------------------------------------------------------
# switch_session: sets current_branch when session has one (line 339)
# ---------------------------------------------------------------------------


def test_switch_session_sets_current_branch_from_session(tmp_path: Path):
    """switch_session must copy branch_name into chat_state.current_branch."""
    store = SessionStore(tmp_path / "state.json", tmp_path / "state.json.bak")
    store.create_session("bot1", 1, "ses1", "Session 1", "proj", "codex", branch_name="my-branch")

    store.switch_session("bot1", 1, "ses1")
    state = store.get_chat_state("bot1", 1)
    assert state.get("current_branch") == "my-branch"
