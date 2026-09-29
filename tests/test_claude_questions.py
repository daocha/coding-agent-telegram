from __future__ import annotations

import asyncio
import io
import json
from concurrent.futures import Future
from types import SimpleNamespace

import pytest

from coding_agent_telegram.claude_control import ClaudeControl
from coding_agent_telegram.claude_questions import ClaudeQuestions
from coding_agent_telegram.agent_runner import MultiAgentRunner


PAYLOAD = {"questions": [
    {"question": "选择语言？", "options": [{"label": "中文"}, {"label": "English"}], "multiSelect": False},
    {"question": "哪些功能？", "options": [{"label": "搜索"}, {"label": "导出"}], "multiSelect": True},
]}


class Output(io.StringIO):
    def close(self):
        self.saved = self.getvalue()
        super().close()


class Bot:
    def __init__(self):
        self.messages = []
        self.removed = []

    async def send_message(self, **kwargs):
        self.messages.append(kwargs)
        return SimpleNamespace(message_id=len(self.messages))

    async def edit_message_reply_markup(self, **kwargs):
        self.removed.append(kwargs)


def update(chat_id=1):
    return SimpleNamespace(effective_chat=SimpleNamespace(id=chat_id), effective_user=None)


async def click(ui, context, data, chat_id=1):
    async def answer(*args):
        pass
    async def edit(**kwargs):
        pass
    event = update(chat_id)
    event.callback_query = SimpleNamespace(data=data, answer=answer, edit_message_reply_markup=edit)
    await ui.handle_callback(event, context)


def test_questions_collect_multiple_localized_answers():
    async def scenario():
        ui = ClaudeQuestions()
        context = SimpleNamespace(bot=Bot())
        task = asyncio.create_task(ui.ask(update(), context, PAYLOAD))
        await asyncio.sleep(0)
        token = next(iter(ui.pending))
        await click(ui, context, f"claudeq:{token}:submit")
        assert not task.done()
        # A different chat cannot change the pending request.
        await click(ui, context, f"claudeq:{token}:0:0", chat_id=2)
        assert not ui.pending[token].selected[0]
        await click(ui, context, f"claudeq:{token}:0:1")
        await click(ui, context, f"claudeq:{token}:0:0")
        await click(ui, context, f"claudeq:{token}:1:0")
        await click(ui, context, f"claudeq:{token}:1:1")
        await click(ui, context, f"claudeq:{token}:submit")
        result = await task
        assert result["updatedInput"]["answers"] == {"选择语言？": "中文", "哪些功能？": "搜索, 导出"}
        assert not ui.pending
        assert len(context.bot.removed) == 2
        await click(ui, context, f"claudeq:{token}:0:0")  # expired token
    asyncio.run(scenario())


def test_typed_new_question_releases_wait_without_selecting_options():
    async def scenario():
        ui = ClaudeQuestions()
        context = SimpleNamespace(bot=Bot())
        task = asyncio.create_task(ui.ask(update(), context, PAYLOAD))
        await asyncio.sleep(0)
        assert not ui.redirect(2, "other chat")
        assert ui.redirect(1, "先解释这个错误可以吗？")
        assert not ui.redirect(1, "next message must use normal routing")
        result = await task
        assert result["behavior"] == "deny"
        assert "先解释这个错误可以吗？" in result["message"]
        assert not ui.pending
    asyncio.run(scenario())


@pytest.mark.parametrize("cancel", [True, False])
def test_questions_cleanup_on_abort_or_dismissal(cancel):
    async def scenario():
        ui = ClaudeQuestions()
        context = SimpleNamespace(bot=Bot())
        task = asyncio.create_task(ui.ask(update(), context, PAYLOAD))
        await asyncio.sleep(0)
        token = next(iter(ui.pending))
        if cancel:
            task.cancel()
            with pytest.raises(asyncio.CancelledError):
                await task
        else:
            await click(ui, context, f"claudeq:{token}:cancel")
            assert (await task)["behavior"] == "deny"
        assert not ui.pending
        assert len(context.bot.removed) == 2
    asyncio.run(scenario())


def request(request_id="q1", tool="AskUserQuestion"):
    return {"type": "control_request", "request_id": request_id,
            "request": {"subtype": "can_use_tool", "tool_name": tool, "input": PAYLOAD}}


def test_control_handshake_answers_and_final_output():
    output = Output()
    future = Future()
    control = ClaudeControl(output, "hello", lambda payload: future)
    control.start()
    control.handle({"type": "control_response", "response": {"request_id": "telegram-init", "subtype": "success"}})
    control.handle(request())
    assert control.waiting
    future.set_result({"behavior": "allow", "updatedInput": {**PAYLOAD, "answers": {"选择语言？": "中文"}}})
    events = [json.loads(line) for line in output.getvalue().splitlines()]
    assert events[1]["message"]["content"] == "hello"
    assert events[2]["response"]["request_id"] == "q1"
    assert events[2]["response"]["response"]["updatedInput"]["answers"] == {"选择语言？": "中文"}
    assert not control.waiting
    control.handle({"type": "result"})
    assert output.closed


def test_control_denies_other_permissions_and_cancels_pending_on_exit():
    output = Output()
    future = Future()
    control = ClaudeControl(output, "hello", lambda payload: future)
    control.handle(request(tool="Bash"))
    assert json.loads(output.getvalue())["response"]["response"]["behavior"] == "deny"
    control.handle(request())
    control.close()
    assert future.cancelled()
    assert not control.waiting


def test_control_cancel_does_not_send_late_answer():
    output = Output()
    future = Future()
    control = ClaudeControl(output, "hello", lambda payload: future)
    control.handle(request())
    control.handle({"type": "control_cancel_request", "request_id": "q1"})
    assert future.cancelled()
    assert output.getvalue() == ""


def test_control_ui_failure_is_reported_to_claude():
    output = Output()
    future = Future()
    control = ClaudeControl(output, "hello", lambda payload: future)
    control.handle(request())
    future.set_exception(RuntimeError("Telegram unavailable"))
    assert json.loads(output.getvalue())["response"]["response"]["behavior"] == "deny"


def test_control_frames_cannot_replace_claude_answer():
    runner = MultiAgentRunner("codex", "copilot", "never", "workspace-write")
    stdout = "\n".join(json.dumps(e) for e in [
        {"type": "assistant", "message": {"content": [{"type": "text", "text": "The answer."}]}},
        {"type": "control_response", "response": {"message": "internal control metadata"}},
        {"type": "result", "is_error": False, "result": "The final answer."},
        {"type": "system", "message": "idle"},
    ])
    assert runner._parse_claude_jsonl(stdout)[2] == "The final answer."


@pytest.mark.parametrize("mode", ["typed", "buttons", "abort"])
def test_router_and_cli_exchange_structured_question_without_losing_answer(tmp_path, mode):
    import sys
    from pathlib import Path
    from test_command_router import make_config, make_update, FakeGitManager
    from coding_agent_telegram.command_router import CommandRouter, RouterDeps
    from coding_agent_telegram.session_store import SessionStore

    cli = tmp_path / "fake-claude"
    cli.write_text(
        f"#!{sys.executable}\n"
        "import sys,json\n"
        "def emit(e): print(json.dumps(e), flush=True)\n"
        "init=json.loads(sys.stdin.readline())\n"
        "assert init['request']['subtype']=='initialize'\n"
        "emit({'type':'control_response','response':{'subtype':'success','request_id':init['request_id']}})\n"
        "prompt=json.loads(sys.stdin.readline())\n"
        "assert prompt['message']['content']=='Help me choose'\n"
        f"emit({request()!r})\n"
        "answer=json.loads(sys.stdin.readline())['response']['response']\n"
        "if answer['behavior']=='deny':\n"
        " assert 'Explain the error instead' in answer['message']\n"
        "else:\n"
        " assert answer['updatedInput']['answers']=={'选择语言？':'中文','哪些功能？':'搜索'}\n"
        "emit({'type':'result','is_error':False,'session_id':'sess_opt','result':'Here is your answer.'})\n"
        "assert sys.stdin.read()==''\n"
    )
    cli.chmod(0o755)
    (tmp_path / "backend").mkdir()
    runner = MultiAgentRunner("codex", "copilot", "never", "workspace-write", claude_bin=str(cli), hard_timeout_seconds=10)
    cfg = make_config(tmp_path)
    store = SessionStore(cfg.state_file, cfg.state_backup_file)
    store.create_session("bot-a", 123, "sess_opt", "opt-session", "backend", "claude")
    router = CommandRouter(RouterDeps(cfg=cfg, store=store, agent_runner=runner, bot_id="bot-a"))
    router.git = FakeGitManager(is_git_repo=False)
    context = SimpleNamespace(args=[], bot=Bot())

    async def scenario():
        run = asyncio.create_task(router.handle_message(make_update(text="Help me choose"), context))
        for _ in range(200):
            if router.claude_questions.pending:
                break
            if run.done():
                await run
                pytest.fail("Claude finished before asking a question")
            await asyncio.sleep(0.01)
        assert router.claude_questions.pending
        if mode == "typed":
            await router.handle_message(make_update(text="Explain the error instead"), context)
            assert not router._has_pending_queue_files(123)
        elif mode == "abort":
            assert await asyncio.to_thread(runner.abort_running_process, tmp_path / "backend")
        else:
            token = next(iter(router.claude_questions.pending))
            await click(router.claude_questions, context, f"claudeq:{token}:0:0", chat_id=123)
            await click(router.claude_questions, context, f"claudeq:{token}:1:0", chat_id=123)
            await click(router.claude_questions, context, f"claudeq:{token}:submit", chat_id=123)
        await asyncio.wait_for(run, 10)
        if mode != "abort":
            assert any("Here is your answer." in message["text"] for message in context.bot.messages)
        else:
            assert any("abort" in message["text"].lower() for message in context.bot.messages)
        assert not router.claude_questions.pending
        assert not runner._running_processes
    asyncio.run(scenario())


def test_control_keeps_channel_open_for_background_followup():
    output = Output()
    future = Future()
    control = ClaudeControl(output, "hello", lambda payload: future)
    control.handle({"type": "system", "subtype": "session_state_changed", "state": "running"})
    control.handle({"type": "result"})
    assert not output.closed
    control.handle(request())
    future.set_result({"behavior": "deny", "message": "Explain instead"})
    assert not output.closed
    control.handle({"type": "assistant", "message": {"content": "The follow-up answer"}})
    control.handle({"type": "system", "subtype": "session_state_changed", "state": "idle"})
    assert not output.closed
    control.handle({"type": "result"})
    assert output.closed


def test_typed_message_after_switch_is_not_sent_to_previous_claude_session():
    async def scenario():
        ui = ClaudeQuestions()
        context = SimpleNamespace(bot=Bot())
        task = asyncio.create_task(ui.ask(update(), context, PAYLOAD, session_id="claude-session"))
        await asyncio.sleep(0)
        assert not ui.redirect(1, "New Codex question", session_id="codex-session")
        assert not task.done()
        assert ui.redirect(1, "Claude follow-up", session_id="claude-session")
        assert "Claude follow-up" in (await task)["message"]
    asyncio.run(scenario())
