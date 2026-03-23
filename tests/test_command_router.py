import asyncio
from pathlib import Path
from types import SimpleNamespace

from coding_agent_telegram.agent_runner import AgentRunResult
from coding_agent_telegram.command_router import CommandRouter, RouterDeps
from coding_agent_telegram.config import AppConfig
from coding_agent_telegram.session_store import SessionStore


class DummyRunner:
    def __init__(self):
        self.create_calls = []
        self.resume_calls = []

    def create_session(self, provider, project_path, user_message, *, skip_git_repo_check=False):
        self.create_calls.append(
            {
                "provider": provider,
                "project_path": project_path,
                "user_message": user_message,
                "skip_git_repo_check": skip_git_repo_check,
            }
        )
        return AgentRunResult(
            session_id="sess_abc123",
            success=True,
            assistant_text="",
            error_message=None,
            raw_events=[],
        )

    def resume_session(self, provider, session_id, project_path, user_message, *, skip_git_repo_check=False):
        self.resume_calls.append(
            {
                "provider": provider,
                "session_id": session_id,
                "project_path": project_path,
                "user_message": user_message,
                "skip_git_repo_check": skip_git_repo_check,
            }
        )
        return AgentRunResult(
            session_id=session_id,
            success=True,
            assistant_text="",
            error_message=None,
            raw_events=[],
        )


class FakeBot:
    def __init__(self):
        self.messages = []
        self.actions = []

    async def send_message(self, chat_id, text):
        self.messages.append((chat_id, text))

    async def send_chat_action(self, chat_id, action):
        self.actions.append((chat_id, action))


class FakeGitManager:
    def __init__(
        self,
        *,
        is_git_repo=False,
        current_branch=None,
        default_branch=None,
        local_branches=None,
        prepare_result=None,
        checkout_result=None,
    ):
        self._is_git_repo = is_git_repo
        self._current_branch = current_branch
        self._default_branch = default_branch
        self._local_branches = local_branches or []
        self.prepare_result = prepare_result
        self.checkout_result = checkout_result
        self.refresh_result = None

    def is_git_repo(self, project_path):
        return self._is_git_repo

    def current_branch(self, project_path):
        return self._current_branch

    def default_branch(self, project_path):
        return self._default_branch

    def list_local_branches(self, project_path):
        return self._local_branches

    def refresh_current_branch(self, project_path):
        return self.refresh_result

    def prepare_branch(self, project_path, *, origin_branch, new_branch):
        return self.prepare_result

    def checkout_branch(self, project_path, branch_name):
        return self.checkout_result


def make_update(chat_id=123, chat_type="private", text="hello"):
    return SimpleNamespace(
        effective_chat=SimpleNamespace(id=chat_id, type=chat_type),
        message=SimpleNamespace(text=text),
    )


def make_config(tmp_path: Path) -> AppConfig:
    return AppConfig(
        workspace_root=tmp_path,
        state_file=tmp_path / "state.json",
        state_backup_file=tmp_path / "state.json.bak",
        log_level="INFO",
        log_dir=tmp_path / "logs",
        telegram_bot_tokens=("x",),
        allowed_chat_ids={123},
        codex_bin="codex",
        copilot_bin="copilot",
        codex_model="",
        copilot_model="",
        copilot_autopilot=True,
        copilot_no_ask_user=True,
        copilot_allow_all=True,
        copilot_allow_all_tools=False,
        copilot_allow_tools=(),
        copilot_deny_tools=(),
        copilot_available_tools=(),
        codex_approval_policy="never",
        codex_sandbox_mode="workspace-write",
        codex_skip_git_repo_check=False,
        max_telegram_message_length=3000,
        enable_group_chats=False,
        enable_sensitive_diff_filter=True,
        default_agent_provider="codex",
    )


def test_project_command_rejects_path(tmp_path: Path):
    runner = DummyRunner()
    cfg = make_config(tmp_path)
    store = SessionStore(cfg.state_file, cfg.state_backup_file)
    router = CommandRouter(RouterDeps(cfg=cfg, store=store, agent_runner=runner, bot_id="bot-a"))

    update = make_update()
    bot = FakeBot()
    context = SimpleNamespace(args=["backend/api"], bot=bot)

    asyncio.run(router.handle_project(update, context))
    assert "Invalid project folder" in bot.messages[-1][1]


def test_project_command_creates_missing_folder(tmp_path: Path):
    runner = DummyRunner()
    cfg = make_config(tmp_path)
    store = SessionStore(cfg.state_file, cfg.state_backup_file)
    router = CommandRouter(RouterDeps(cfg=cfg, store=store, agent_runner=runner, bot_id="bot-a"))

    update = make_update()
    bot = FakeBot()
    context = SimpleNamespace(args=["backend"], bot=bot)

    asyncio.run(router.handle_project(update, context))

    assert (tmp_path / "backend").is_dir()
    assert store.get_chat_state("bot-a", 123)["current_project_folder"] == "backend"
    assert store.is_project_trusted("backend") is True
    assert "Project set: backend" in bot.messages[-1][1]


def test_project_command_reports_current_branch_for_git_repo(tmp_path: Path):
    backend = tmp_path / "backend"
    backend.mkdir()
    runner = DummyRunner()
    cfg = make_config(tmp_path)
    store = SessionStore(cfg.state_file, cfg.state_backup_file)
    router = CommandRouter(RouterDeps(cfg=cfg, store=store, agent_runner=runner, bot_id="bot-a"))
    router.git = FakeGitManager(is_git_repo=True, current_branch="main")

    update = make_update()
    bot = FakeBot()
    context = SimpleNamespace(args=["backend"], bot=bot)

    asyncio.run(router.handle_project(update, context))

    assert "Current branch: main" in bot.messages[-1][1]
    assert "If you do not set one, the bot will work on the current branch: main" in bot.messages[-1][1]
    assert store.get_chat_state("bot-a", 123)["current_branch"] == "main"


def test_project_command_warns_when_active_session_belongs_to_another_project(tmp_path: Path):
    runner = DummyRunner()
    cfg = make_config(tmp_path)
    store = SessionStore(cfg.state_file, cfg.state_backup_file)
    store.create_session("bot-a", 123, "sess_1", "old-session", "backend", "codex")
    router = CommandRouter(RouterDeps(cfg=cfg, store=store, agent_runner=runner, bot_id="bot-a"))

    update = make_update()
    bot = FakeBot()
    context = SimpleNamespace(args=["frontend"], bot=bot)

    asyncio.run(router.handle_project(update, context))

    message = bot.messages[-1][1]
    assert "Warning: the current active session is bound to a different project." in message
    assert "Session project: backend" in message
    assert "Start a new session with /new" in message


def test_branch_command_requires_project_first(tmp_path: Path):
    runner = DummyRunner()
    cfg = make_config(tmp_path)
    store = SessionStore(cfg.state_file, cfg.state_backup_file)
    router = CommandRouter(RouterDeps(cfg=cfg, store=store, agent_runner=runner, bot_id="bot-a"))

    update = make_update()
    bot = FakeBot()
    context = SimpleNamespace(args=[], bot=bot)

    asyncio.run(router.handle_branch(update, context))

    assert "No project selected." in bot.messages[-1][1]


def test_branch_command_lists_branches_when_project_is_set(tmp_path: Path):
    backend = tmp_path / "backend"
    backend.mkdir()
    runner = DummyRunner()
    cfg = make_config(tmp_path)
    store = SessionStore(cfg.state_file, cfg.state_backup_file)
    store.set_current_project_folder("bot-a", 123, "backend")
    router = CommandRouter(RouterDeps(cfg=cfg, store=store, agent_runner=runner, bot_id="bot-a"))
    router.git = FakeGitManager(
        is_git_repo=True,
        current_branch="feature-1",
        default_branch="main",
        local_branches=["main", "feature-1", "feature-2"],
    )
    router.git.refresh_result = SimpleNamespace(
        success=True,
        message="Updated branch 'feature-1' from origin.",
        current_branch="feature-1",
        default_branch="main",
        warnings=(),
    )

    update = make_update()
    bot = FakeBot()
    context = SimpleNamespace(args=[], bot=bot)

    asyncio.run(router.handle_branch(update, context))

    message = bot.messages[-1][1]
    assert "Project: backend" in message
    assert "Current branch: feature-1" in message
    assert "Default branch: main" in message
    assert "* feature-1" in message
    assert "- main" in message
    assert "/branch <new_branch>" in message


def test_branch_command_lists_branches_even_when_refresh_warns(tmp_path: Path):
    backend = tmp_path / "backend"
    backend.mkdir()
    runner = DummyRunner()
    cfg = make_config(tmp_path)
    store = SessionStore(cfg.state_file, cfg.state_backup_file)
    store.set_current_project_folder("bot-a", 123, "backend")
    router = CommandRouter(RouterDeps(cfg=cfg, store=store, agent_runner=runner, bot_id="bot-a"))
    router.git = FakeGitManager(
        is_git_repo=True,
        current_branch="feature-deleted-remote",
        default_branch="main",
        local_branches=["main", "feature-deleted-remote"],
    )
    router.git.refresh_result = SimpleNamespace(
        success=True,
        message="Updated branch 'feature-deleted-remote' from origin.",
        current_branch="feature-deleted-remote",
        default_branch="main",
        warnings=("git pull failed for branch: feature-deleted-remote",),
    )

    update = make_update()
    bot = FakeBot()
    context = SimpleNamespace(args=[], bot=bot)

    asyncio.run(router.handle_branch(update, context))

    message = bot.messages[-1][1]
    assert "Refresh warnings:" in message
    assert "git pull failed for branch: feature-deleted-remote" in message
    assert "* feature-deleted-remote" in message
    assert "- main" in message


def test_branch_command_uses_default_branch_when_origin_not_provided(tmp_path: Path):
    backend = tmp_path / "backend"
    backend.mkdir()
    runner = DummyRunner()
    cfg = make_config(tmp_path)
    store = SessionStore(cfg.state_file, cfg.state_backup_file)
    store.set_current_project_folder("bot-a", 123, "backend")
    router = CommandRouter(RouterDeps(cfg=cfg, store=store, agent_runner=runner, bot_id="bot-a"))
    router.git = FakeGitManager(
        prepare_result=SimpleNamespace(
            success=True,
            message="Created branch 'feature-1' from 'main'.",
            current_branch="feature-1",
            default_branch="main",
        )
    )

    update = make_update()
    bot = FakeBot()
    context = SimpleNamespace(args=["feature-1"], bot=bot)

    asyncio.run(router.handle_branch(update, context))

    assert "Created branch 'feature-1' from 'main'." in bot.messages[-1][1]
    assert "Current branch: feature-1" in bot.messages[-1][1]
    assert store.get_chat_state("bot-a", 123)["current_branch"] == "feature-1"


def test_new_command_supports_copilot_provider(tmp_path: Path):
    backend = tmp_path / "backend"
    backend.mkdir()
    runner = DummyRunner()
    cfg = make_config(tmp_path)
    store = SessionStore(cfg.state_file, cfg.state_backup_file)
    store.set_current_project_folder("bot-a", 123, "backend")
    router = CommandRouter(RouterDeps(cfg=cfg, store=store, agent_runner=runner, bot_id="bot-a"))

    update = make_update()
    bot = FakeBot()
    context = SimpleNamespace(args=["my-session", "copilot"], bot=bot)

    asyncio.run(router.handle_new(update, context))
    state = store.get_chat_state("bot-a", 123)
    sess = state["sessions"][state["active_session_id"]]
    assert sess["provider"] == "copilot"
    assert bot.messages[0][1] == "Creating session..."
    assert "Session ID: sess_abc123" in bot.messages[-1][1]


def test_new_command_skips_git_repo_check_for_trusted_project(tmp_path: Path):
    backend = tmp_path / "backend"
    backend.mkdir()
    runner = DummyRunner()
    cfg = make_config(tmp_path)
    store = SessionStore(cfg.state_file, cfg.state_backup_file)
    store.trust_project("backend")
    store.set_current_project_folder("bot-a", 123, "backend")
    router = CommandRouter(RouterDeps(cfg=cfg, store=store, agent_runner=runner, bot_id="bot-a"))

    update = make_update()
    bot = FakeBot()
    context = SimpleNamespace(args=["my-session"], bot=bot)

    asyncio.run(router.handle_new(update, context))

    assert runner.create_calls[-1]["skip_git_repo_check"] is True
    assert bot.messages[0][1] == "Creating session..."
    assert "Session ID: sess_abc123" in bot.messages[-1][1]


def test_new_command_rejects_duplicate_session_name(tmp_path: Path):
    backend = tmp_path / "backend"
    backend.mkdir()
    runner = DummyRunner()
    cfg = make_config(tmp_path)
    store = SessionStore(cfg.state_file, cfg.state_backup_file)
    store.set_current_project_folder("bot-a", 123, "backend")
    store.create_session("bot-a", 123, "sess_existing", "my-session", "backend", "codex")
    router = CommandRouter(RouterDeps(cfg=cfg, store=store, agent_runner=runner, bot_id="bot-a"))

    update = make_update()
    bot = FakeBot()
    context = SimpleNamespace(args=["my-session"], bot=bot)

    asyncio.run(router.handle_new(update, context))

    assert runner.create_calls == []
    assert "Session name already exists: my-session" in bot.messages[-1][1]


def test_switch_lists_latest_10_sessions_by_default(tmp_path: Path):
    runner = DummyRunner()
    cfg = make_config(tmp_path)
    store = SessionStore(cfg.state_file, cfg.state_backup_file)
    router = CommandRouter(RouterDeps(cfg=cfg, store=store, agent_runner=runner, bot_id="bot-a"))

    for idx in range(12):
        store.create_session("bot-a", 123, f"sess_{idx}", f"session-{idx}", "backend", "codex")

    update = make_update()
    bot = FakeBot()
    context = SimpleNamespace(args=[], bot=bot)

    asyncio.run(router.handle_switch(update, context))

    message = bot.messages[-1][1]
    assert "Available sessions (page 1/2):" in message
    assert "session-11" in message
    assert "session-2" in message
    assert "session-1" not in message
    assert "Pages: /switch page 1 ... /switch page 2" in message
    assert "/switch <session_id>" in message


def test_switch_lists_requested_page(tmp_path: Path):
    runner = DummyRunner()
    cfg = make_config(tmp_path)
    store = SessionStore(cfg.state_file, cfg.state_backup_file)
    router = CommandRouter(RouterDeps(cfg=cfg, store=store, agent_runner=runner, bot_id="bot-a"))

    for idx in range(12):
        store.create_session("bot-a", 123, f"sess_{idx}", f"session-{idx}", "backend", "codex")

    update = make_update()
    bot = FakeBot()
    context = SimpleNamespace(args=["page", "2"], bot=bot)

    asyncio.run(router.handle_switch(update, context))

    message = bot.messages[-1][1]
    assert "Available sessions (page 2/2):" in message
    assert "session-1" in message
    assert "session-0" in message
    assert "session-11" not in message


def test_switch_by_session_id_still_works(tmp_path: Path):
    runner = DummyRunner()
    cfg = make_config(tmp_path)
    store = SessionStore(cfg.state_file, cfg.state_backup_file)
    store.create_session("bot-a", 123, "sess_a", "session-a", "backend", "codex")
    store.create_session("bot-a", 123, "sess_b", "session-b", "backend", "codex")
    router = CommandRouter(RouterDeps(cfg=cfg, store=store, agent_runner=runner, bot_id="bot-a"))

    update = make_update()
    bot = FakeBot()
    context = SimpleNamespace(args=["sess_a"], bot=bot)

    asyncio.run(router.handle_switch(update, context))

    assert "Switched to session: session-a" in bot.messages[-1][1]


def test_switch_does_not_persist_if_branch_checkout_fails(tmp_path: Path):
    backend = tmp_path / "backend"
    backend.mkdir()
    runner = DummyRunner()
    cfg = make_config(tmp_path)
    store = SessionStore(cfg.state_file, cfg.state_backup_file)
    store.create_session("bot-a", 123, "sess_a", "session-a", "backend", "codex", branch_name="missing-branch")
    store.create_session("bot-a", 123, "sess_b", "session-b", "backend", "codex")
    router = CommandRouter(RouterDeps(cfg=cfg, store=store, agent_runner=runner, bot_id="bot-a"))
    router.git = FakeGitManager(
        is_git_repo=True,
        checkout_result=SimpleNamespace(success=False, message="Failed to checkout branch: missing-branch"),
    )

    update = make_update()
    bot = FakeBot()
    context = SimpleNamespace(args=["sess_a"], bot=bot)

    asyncio.run(router.handle_switch(update, context))

    assert "Failed to checkout branch: missing-branch" in bot.messages[-1][1]
    assert store.get_chat_state("bot-a", 123)["active_session_id"] == "sess_b"


def test_switch_rejects_missing_project_folder(tmp_path: Path):
    runner = DummyRunner()
    cfg = make_config(tmp_path)
    store = SessionStore(cfg.state_file, cfg.state_backup_file)
    store.create_session("bot-a", 123, "sess_a", "session-a", "deleted-project", "codex")
    store.create_session("bot-a", 123, "sess_b", "session-b", "backend", "codex")
    router = CommandRouter(RouterDeps(cfg=cfg, store=store, agent_runner=runner, bot_id="bot-a"))

    update = make_update()
    bot = FakeBot()
    context = SimpleNamespace(args=["sess_a"], bot=bot)

    asyncio.run(router.handle_switch(update, context))

    assert "Project folder no longer exists for this session: deleted-project" in bot.messages[-1][1]
    assert store.get_chat_state("bot-a", 123)["active_session_id"] == "sess_b"
