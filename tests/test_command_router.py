import asyncio
from pathlib import Path
from types import SimpleNamespace

from coding_agent_telegram.agent_runner import AgentRunResult
from coding_agent_telegram.command_router import CommandRouter, RouterDeps
from coding_agent_telegram.config import AppConfig
from coding_agent_telegram.session_store import SessionStore


class DummyRunner:
    def create_session(self, provider, project_path, user_message):
        return AgentRunResult(
            session_id="sess_abc123",
            success=True,
            assistant_text="",
            error_message=None,
            raw_events=[],
        )

    def resume_session(self, provider, session_id, project_path, user_message):
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

    async def send_message(self, chat_id, text):
        self.messages.append((chat_id, text))


def make_update(chat_id=123, chat_type="private", text="hello"):
    return SimpleNamespace(
        effective_chat=SimpleNamespace(id=chat_id, type=chat_type),
        message=SimpleNamespace(text=text),
    )


def test_project_command_rejects_path(tmp_path: Path):
    cfg = AppConfig(
        workspace_root=tmp_path,
        state_file=tmp_path / "state.json",
        state_backup_file=tmp_path / "state.json.bak",
        log_level="INFO",
        telegram_bot_token="x",
        allowed_chat_ids={123},
        codex_bin="codex",
        copilot_bin="copilot",
        codex_approval_policy="never",
        codex_sandbox_mode="workspace-write",
        max_telegram_message_length=3000,
        enable_group_chats=False,
        enable_sensitive_diff_filter=True,
        default_agent_provider="codex",
    )
    store = SessionStore(cfg.state_file, cfg.state_backup_file)
    router = CommandRouter(RouterDeps(cfg=cfg, store=store, agent_runner=DummyRunner()))

    update = make_update()
    bot = FakeBot()
    context = SimpleNamespace(args=["backend/api"], bot=bot)

    asyncio.run(router.handle_project(update, context))
    assert "Invalid project folder" in bot.messages[-1][1]


def test_new_command_supports_copilot_provider(tmp_path: Path):
    backend = tmp_path / "backend"
    backend.mkdir()
    cfg = AppConfig(
        workspace_root=tmp_path,
        state_file=tmp_path / "state.json",
        state_backup_file=tmp_path / "state.json.bak",
        log_level="INFO",
        telegram_bot_token="x",
        allowed_chat_ids={123},
        codex_bin="codex",
        copilot_bin="copilot",
        codex_approval_policy="never",
        codex_sandbox_mode="workspace-write",
        max_telegram_message_length=3000,
        enable_group_chats=False,
        enable_sensitive_diff_filter=True,
        default_agent_provider="codex",
    )
    store = SessionStore(cfg.state_file, cfg.state_backup_file)
    store.set_current_project_folder(123, "backend")
    router = CommandRouter(RouterDeps(cfg=cfg, store=store, agent_runner=DummyRunner()))

    update = make_update()
    bot = FakeBot()
    context = SimpleNamespace(args=["my-session", "copilot"], bot=bot)

    asyncio.run(router.handle_new(update, context))
    state = store.get_chat_state(123)
    sess = state["sessions"][state["active_session_id"]]
    assert sess["provider"] == "copilot"
