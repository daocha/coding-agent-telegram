from __future__ import annotations

import io
import threading
import time
from pathlib import Path
from typing import Optional

from coding_agent_telegram.agent_runner import MultiAgentRunner


class FakePopen:
    def __init__(self, stdout: str = "", stderr: str = "", returncode: int = 0):
        self.stdout = io.StringIO(stdout)
        self.stderr = io.StringIO(stderr)
        self.returncode = returncode
        self.killed = False
        self.terminated = False

    def poll(self):
        return self.returncode

    def kill(self):
        self.killed = True
        self.returncode = -9

    def terminate(self):
        self.terminated = True
        self.returncode = -15


class FakeBlockingPopen(FakePopen):
    def __init__(self):
        super().__init__(stdout="", stderr="", returncode=0)
        self.returncode = None

    def poll(self):
        return self.returncode


def make_fake_popen(
    calls: list[tuple[list[str], Optional[Path], Optional[dict]]],
    *,
    process_stdout: str = "",
    process_stderr: str = "",
    returncode: int = 0,
):
    def fake_popen(args, cwd=None, env=None, stdout=None, stderr=None, text=None, start_new_session=None):
        calls.append((args, cwd, env))
        return FakePopen(stdout=process_stdout, stderr=process_stderr, returncode=returncode)

    return fake_popen


def test_codex_runner_skips_git_repo_check(monkeypatch):
    calls = []
    monkeypatch.setattr("coding_agent_telegram.agent_runner.subprocess.Popen", make_fake_popen(calls))

    runner = MultiAgentRunner(
        codex_bin="codex",
        copilot_bin="copilot",
        approval_policy="never",
        sandbox_mode="workspace-write",
    )

    runner.create_session("codex", Path("/tmp/project"), "hello", skip_git_repo_check=True)
    runner.resume_session("codex", "sess_1", Path("/tmp/project"), "hello again", skip_git_repo_check=True)

    assert "--skip-git-repo-check" in calls[0][0]
    assert "--skip-git-repo-check" in calls[1][0]
    assert calls[0][1] == Path("/tmp/project")
    assert calls[1][1] == Path("/tmp/project")


def test_codex_runner_respects_git_repo_check_setting(monkeypatch):
    calls = []
    monkeypatch.setattr("coding_agent_telegram.agent_runner.subprocess.Popen", make_fake_popen(calls))

    runner = MultiAgentRunner(
        codex_bin="codex",
        copilot_bin="copilot",
        approval_policy="never",
        sandbox_mode="workspace-write",
    )

    runner.create_session("codex", Path("/tmp/project"), "hello", skip_git_repo_check=False)

    assert "--skip-git-repo-check" not in calls[0][0]


def test_codex_runner_resume_uses_resume_subcommand_shape(monkeypatch):
    calls = []
    monkeypatch.setattr("coding_agent_telegram.agent_runner.subprocess.Popen", make_fake_popen(calls))

    runner = MultiAgentRunner(
        codex_bin="codex",
        copilot_bin="copilot",
        approval_policy="never",
        sandbox_mode="workspace-write",
    )

    runner.resume_session("codex", "sess_1", Path("/tmp/project"), "hello again", skip_git_repo_check=True)

    args = calls[0][0]
    assert args[:9] == [
        "codex",
        "exec",
        "resume",
        "--skip-git-repo-check",
        "-c",
        "approval_policy=never",
        "-c",
        "sandbox_mode=workspace-write",
        "--json",
    ]
    assert args[9] == "--output-last-message"
    assert args[11:] == ["sess_1", runner.PROMPT_PREFIX + "hello again"]


def test_copilot_runner_uses_prompt_mode_shape(monkeypatch):
    calls = []
    monkeypatch.setattr(
        "coding_agent_telegram.agent_runner.subprocess.Popen",
        make_fake_popen(calls, process_stdout='{"sessionId":"sess_copilot"}\n'),
    )

    runner = MultiAgentRunner(
        codex_bin="codex",
        copilot_bin="copilot",
        approval_policy="never",
        sandbox_mode="workspace-write",
    )

    result = runner.create_session("copilot", Path("/tmp/project"), "hello", skip_git_repo_check=False)

    assert calls[0][0] == [
        "copilot",
        "--no-ask-user",
        "--output-format=json",
        "--prompt",
        runner.PROMPT_PREFIX + "hello",
    ]
    assert calls[0][1] == Path("/tmp/project")
    assert result.session_id == "sess_copilot"


def test_copilot_runner_resume_uses_resume_flag(monkeypatch):
    calls = []
    monkeypatch.setattr(
        "coding_agent_telegram.agent_runner.subprocess.Popen",
        make_fake_popen(calls, process_stdout='{"threadId":"sess_copilot"}\n'),
    )

    runner = MultiAgentRunner(
        codex_bin="codex",
        copilot_bin="copilot",
        approval_policy="never",
        sandbox_mode="workspace-write",
    )

    result = runner.resume_session("copilot", "sess_1", Path("/tmp/project"), "hello again", skip_git_repo_check=False)

    assert calls[0][0] == [
        "copilot",
        "--resume=sess_1",
        "--autopilot",
        "--no-ask-user",
        "--allow-all",
        "--output-format=json",
        "--prompt",
        runner.PROMPT_PREFIX + "hello again",
    ]
    assert result.session_id == "sess_copilot"


def test_codex_runner_attaches_images_for_create_and_resume(monkeypatch):
    calls = []
    monkeypatch.setattr("coding_agent_telegram.agent_runner.subprocess.Popen", make_fake_popen(calls))

    runner = MultiAgentRunner(
        codex_bin="codex",
        copilot_bin="copilot",
        approval_policy="never",
        sandbox_mode="workspace-write",
    )

    image_path = Path("/tmp/project/.coding-agent-telegram/telegram_attachments/img.jpg")
    runner.create_session("codex", Path("/tmp/project"), "hello", image_paths=(image_path,))
    runner.resume_session("codex", "sess_1", Path("/tmp/project"), "hello again", image_paths=(image_path,))

    assert "--image" in calls[0][0]
    assert str(image_path) in calls[0][0]
    assert "--image" in calls[1][0]
    assert str(image_path) in calls[1][0]


def test_copilot_runner_rejects_image_attachments():
    runner = MultiAgentRunner(
        codex_bin="codex",
        copilot_bin="copilot",
        approval_policy="never",
        sandbox_mode="workspace-write",
    )

    image_path = Path("/tmp/project/.coding-agent-telegram/telegram_attachments/img.jpg")
    result = runner.create_session("copilot", Path("/tmp/project"), "hello", image_paths=(image_path,))

    assert result.success is False
    assert result.error_message == "Image attachments are not supported for Copilot sessions."


def test_copilot_runner_uses_native_home_when_copilot_home_is_unset(monkeypatch):
    calls = []
    monkeypatch.setattr("coding_agent_telegram.agent_runner.subprocess.Popen", make_fake_popen(calls))
    monkeypatch.delenv("COPILOT_HOME", raising=False)

    runner = MultiAgentRunner(
        codex_bin="codex",
        copilot_bin="copilot",
        approval_policy="never",
        sandbox_mode="workspace-write",
    )

    runner.create_session("copilot", Path("/tmp/project"), "hello", skip_git_repo_check=True)

    assert "COPILOT_HOME" not in calls[0][2]
    assert "--allow-all" not in calls[0][0]
    assert "--allow-all-tools" not in calls[0][0]


def test_copilot_runner_preserves_explicit_copilot_home(monkeypatch):
    calls = []
    monkeypatch.setattr("coding_agent_telegram.agent_runner.subprocess.Popen", make_fake_popen(calls))
    monkeypatch.setenv("COPILOT_HOME", "/tmp/custom-copilot-home")

    runner = MultiAgentRunner(
        codex_bin="codex",
        copilot_bin="copilot",
        approval_policy="never",
        sandbox_mode="workspace-write",
    )

    runner.create_session("copilot", Path("/tmp/project"), "hello", skip_git_repo_check=True)

    assert calls[0][2]["COPILOT_HOME"] == "/tmp/custom-copilot-home"


def test_copilot_runner_emits_progress_updates(monkeypatch):
    calls = []
    monkeypatch.setattr(
        "coding_agent_telegram.agent_runner.subprocess.Popen",
        make_fake_popen(
            calls,
            process_stdout='{"assistant_text":"partial output"}\n{"sessionId":"sess_copilot"}\n',
        ),
    )

    runner = MultiAgentRunner(
        codex_bin="codex",
        copilot_bin="copilot",
        approval_policy="never",
        sandbox_mode="workspace-write",
    )
    runner.PROGRESS_UPDATE_INTERVAL_SECONDS = 0
    captured = []

    runner.create_session("copilot", Path("/tmp/project"), "hello", on_progress=captured.append)

    assert captured
    assert captured[0].text == "partial output"
    assert captured[0].source == "stdout"


def test_copilot_runner_progress_falls_back_to_raw_json_when_no_text_field_exists(monkeypatch):
    calls = []
    monkeypatch.setattr(
        "coding_agent_telegram.agent_runner.subprocess.Popen",
        make_fake_popen(
            calls,
            process_stdout='{"type":"session.update","sessionId":"sess_copilot","state":"running"}\n',
        ),
    )

    runner = MultiAgentRunner(
        codex_bin="codex",
        copilot_bin="copilot",
        approval_policy="never",
        sandbox_mode="workspace-write",
    )
    runner.PROGRESS_UPDATE_INTERVAL_SECONDS = 0
    captured = []

    runner.create_session("copilot", Path("/tmp/project"), "hello", on_progress=captured.append)

    assert captured
    assert '"type": "session.update"' in captured[0].text
    assert '"state": "running"' in captured[0].text


def test_copilot_runner_progress_includes_nested_item_started_details(monkeypatch):
    calls = []
    monkeypatch.setattr(
        "coding_agent_telegram.agent_runner.subprocess.Popen",
        make_fake_popen(
            calls,
            process_stdout='{"type":"item.started","item":{"type":"shell","command":"git status","description":"Check repo state"}}\n',
        ),
    )

    runner = MultiAgentRunner(
        codex_bin="codex",
        copilot_bin="copilot",
        approval_policy="never",
        sandbox_mode="workspace-write",
    )
    runner.PROGRESS_UPDATE_INTERVAL_SECONDS = 0
    captured = []

    runner.create_session("copilot", Path("/tmp/project"), "hello", on_progress=captured.append)

    assert captured
    assert captured[0].text == "Check repo state"


def test_codex_runner_progress_includes_nested_item_completed_details(monkeypatch):
    calls = []
    monkeypatch.setattr(
        "coding_agent_telegram.agent_runner.subprocess.Popen",
        make_fake_popen(
            calls,
            process_stdout='{"type":"item.completed","item":{"type":"shell","command":"git status","status":"completed"}}\n',
        ),
    )

    runner = MultiAgentRunner(
        codex_bin="codex",
        copilot_bin="copilot",
        approval_policy="never",
        sandbox_mode="workspace-write",
    )
    runner.PROGRESS_UPDATE_INTERVAL_SECONDS = 0
    captured = []

    runner.create_session("codex", Path("/tmp/project"), "hello", on_progress=captured.append)

    assert captured
    assert captured[0].text == "git status (completed)"


def test_copilot_runner_progress_extracts_nested_agent_message_text(monkeypatch):
    calls = []
    monkeypatch.setattr(
        "coding_agent_telegram.agent_runner.subprocess.Popen",
        make_fake_popen(
            calls,
            process_stdout='{"type":"item.completed","item":{"type":"agent_message","text":"I am checking the provider integration points first."}}\n',
        ),
    )

    runner = MultiAgentRunner(
        codex_bin="codex",
        copilot_bin="copilot",
        approval_policy="never",
        sandbox_mode="workspace-write",
    )
    runner.PROGRESS_UPDATE_INTERVAL_SECONDS = 0
    captured = []

    runner.create_session("copilot", Path("/tmp/project"), "hello", on_progress=captured.append)

    assert captured
    assert captured[0].text == "I am checking the provider integration points first."


def test_copilot_runner_progress_summarizes_command_execution(monkeypatch):
    calls = []
    monkeypatch.setattr(
        "coding_agent_telegram.agent_runner.subprocess.Popen",
        make_fake_popen(
            calls,
            process_stdout=(
                '{"type":"item.started","item":{"type":"command_execution","command":"/bin/zsh -lc \\"rg -n foo\\"","status":"in_progress"}}\n'
            ),
        ),
    )

    runner = MultiAgentRunner(
        codex_bin="codex",
        copilot_bin="copilot",
        approval_policy="never",
        sandbox_mode="workspace-write",
    )
    runner.PROGRESS_UPDATE_INTERVAL_SECONDS = 0
    captured = []

    runner.create_session("copilot", Path("/tmp/project"), "hello", on_progress=captured.append)

    assert captured
    assert captured[0].text == '/bin/zsh -lc "rg -n foo"'


def test_copilot_runner_extracts_assistant_message_delta_content(monkeypatch):
    calls = []
    monkeypatch.setattr(
        "coding_agent_telegram.agent_runner.subprocess.Popen",
        make_fake_popen(
            calls,
            process_stdout='{"type":"assistant.message_delta","data":{"messageId":"abc","deltaContent":" log"}}\n',
        ),
    )

    runner = MultiAgentRunner(
        codex_bin="codex",
        copilot_bin="copilot",
        approval_policy="never",
        sandbox_mode="workspace-write",
    )
    runner.PROGRESS_UPDATE_INTERVAL_SECONDS = 0
    captured = []

    runner.create_session("copilot", Path("/tmp/project"), "hello", on_progress=captured.append)

    assert captured
    assert captured[0].text == "log"


def test_copilot_runner_extracts_assistant_message_content(monkeypatch):
    calls = []
    monkeypatch.setattr(
        "coding_agent_telegram.agent_runner.subprocess.Popen",
        make_fake_popen(
            calls,
            process_stdout='{"type":"assistant.message","data":{"messageId":"abc","content":"Hello from Copilot"}}\n',
        ),
    )

    runner = MultiAgentRunner(
        codex_bin="codex",
        copilot_bin="copilot",
        approval_policy="never",
        sandbox_mode="workspace-write",
    )
    runner.PROGRESS_UPDATE_INTERVAL_SECONDS = 0
    captured = []

    runner.create_session("copilot", Path("/tmp/project"), "hello", on_progress=captured.append)

    assert captured
    assert captured[0].text == "Hello from Copilot"


def test_codex_runner_passes_model_when_configured(monkeypatch):
    calls = []
    monkeypatch.setattr("coding_agent_telegram.agent_runner.subprocess.Popen", make_fake_popen(calls))

    runner = MultiAgentRunner(
        codex_bin="codex",
        copilot_bin="copilot",
        approval_policy="never",
        sandbox_mode="workspace-write",
        codex_model="gpt-5-codex",
    )

    runner.create_session("codex", Path("/tmp/project"), "hello", skip_git_repo_check=False)

    assert calls[0][0][:4] == ["codex", "exec", "-m", "gpt-5-codex"]


def test_copilot_runner_passes_model_when_configured(monkeypatch):
    calls = []
    monkeypatch.setattr("coding_agent_telegram.agent_runner.subprocess.Popen", make_fake_popen(calls))

    runner = MultiAgentRunner(
        codex_bin="codex",
        copilot_bin="copilot",
        approval_policy="never",
        sandbox_mode="workspace-write",
        copilot_model="gpt-5",
    )

    runner.create_session("copilot", Path("/tmp/project"), "hello", skip_git_repo_check=False)

    assert calls[0][0][:5] == [
        "copilot",
        "--model",
        "gpt-5",
        "--no-ask-user",
        "--output-format=json",
    ]


def test_copilot_runner_passes_tool_permission_flags(monkeypatch):
    calls = []
    monkeypatch.setattr("coding_agent_telegram.agent_runner.subprocess.Popen", make_fake_popen(calls))

    runner = MultiAgentRunner(
        codex_bin="codex",
        copilot_bin="copilot",
        approval_policy="never",
        sandbox_mode="workspace-write",
        copilot_autopilot=False,
        copilot_no_ask_user=False,
        copilot_allow_all=False,
        copilot_allow_all_tools=True,
        copilot_allow_tools=("shell(git)", "shell(npm)"),
        copilot_deny_tools=("shell(rm)",),
        copilot_available_tools=("shell", "apply_patch"),
    )

    runner.create_session("copilot", Path("/tmp/project"), "hello", skip_git_repo_check=False)

    assert "--allow-all-tools" not in calls[0][0]
    assert "--allow-tool" not in calls[0][0]
    assert "--deny-tool" not in calls[0][0]
    assert "--available-tools" not in calls[0][0]


# ---------------------------------------------------------------------------
# Claude provider
# ---------------------------------------------------------------------------


def test_claude_runner_uses_print_mode_shape(monkeypatch):
    calls = []
    monkeypatch.setattr(
        "coding_agent_telegram.agent_runner.subprocess.Popen",
        make_fake_popen(
            calls,
            process_stdout='{"type":"result","subtype":"success","is_error":false,"result":"Done.","session_id":"sess_claude"}\n',
        ),
    )

    runner = MultiAgentRunner(
        codex_bin="codex",
        copilot_bin="copilot",
        approval_policy="never",
        sandbox_mode="workspace-write",
    )

    result = runner.create_session("claude", Path("/tmp/project"), "hello")

    assert calls[0][0] == [
        "claude",
        "--permission-mode",
        "bypassPermissions",
        "--output-format",
        "stream-json",
        "--verbose",
        "-p",
        runner.PROMPT_PREFIX + "hello",
    ]
    assert calls[0][1] == Path("/tmp/project")
    assert result.success is True
    assert result.session_id == "sess_claude"
    assert result.assistant_text == "Done."


def test_claude_runner_resume_uses_resume_flag(monkeypatch):
    calls = []
    monkeypatch.setattr(
        "coding_agent_telegram.agent_runner.subprocess.Popen",
        make_fake_popen(
            calls,
            process_stdout='{"type":"result","subtype":"success","is_error":false,"result":"Done again.","session_id":"sess_claude"}\n',
        ),
    )

    runner = MultiAgentRunner(
        codex_bin="codex",
        copilot_bin="copilot",
        approval_policy="never",
        sandbox_mode="workspace-write",
    )

    result = runner.resume_session("claude", "sess_1", Path("/tmp/project"), "hello again")

    assert calls[0][0][:3] == ["claude", "--resume", "sess_1"]
    assert result.session_id == "sess_claude"
    assert result.assistant_text == "Done again."


def test_claude_runner_passes_model_and_tool_flags_when_configured(monkeypatch):
    calls = []
    monkeypatch.setattr("coding_agent_telegram.agent_runner.subprocess.Popen", make_fake_popen(calls))

    runner = MultiAgentRunner(
        codex_bin="codex",
        copilot_bin="copilot",
        approval_policy="never",
        sandbox_mode="workspace-write",
        claude_model="opus",
        claude_permission_mode="dontAsk",
        claude_allowed_tools=("Read", "Edit"),
        claude_disallowed_tools=("Bash(rm *)",),
    )

    runner.create_session("claude", Path("/tmp/project"), "hello")

    assert calls[0][0] == [
        "claude",
        "--model",
        "opus",
        "--permission-mode",
        "dontAsk",
        "--allowedTools",
        "Read,Edit",
        "--disallowedTools",
        "Bash(rm *)",
        "--output-format",
        "stream-json",
        "--verbose",
        "-p",
        runner.PROMPT_PREFIX + "hello",
    ]


def test_claude_runner_reports_failure_from_result_event(monkeypatch):
    calls = []
    monkeypatch.setattr(
        "coding_agent_telegram.agent_runner.subprocess.Popen",
        make_fake_popen(
            calls,
            process_stdout='{"type":"result","subtype":"error_max_turns","is_error":true,"result":"","session_id":"sess_claude"}\n',
        ),
    )

    runner = MultiAgentRunner(
        codex_bin="codex",
        copilot_bin="copilot",
        approval_policy="never",
        sandbox_mode="workspace-write",
    )

    result = runner.create_session("claude", Path("/tmp/project"), "hello")

    assert result.success is False
    assert result.error_message == "error_max_turns"
    assert result.session_id == "sess_claude"


def test_claude_runner_extracts_assistant_message_text_as_progress(monkeypatch):
    calls = []
    monkeypatch.setattr(
        "coding_agent_telegram.agent_runner.subprocess.Popen",
        make_fake_popen(
            calls,
            process_stdout=(
                '{"type":"assistant","message":{"role":"assistant","content":[{"type":"text","text":"Looking at the code now."}]},'
                '"session_id":"sess_claude"}\n'
            ),
        ),
    )

    runner = MultiAgentRunner(
        codex_bin="codex",
        copilot_bin="copilot",
        approval_policy="never",
        sandbox_mode="workspace-write",
    )
    runner.PROGRESS_UPDATE_INTERVAL_SECONDS = 0
    captured = []

    runner.create_session("claude", Path("/tmp/project"), "hello", on_progress=captured.append)

    assert captured
    assert captured[0].text == "Looking at the code now."


def test_claude_runner_summarizes_tool_use_as_progress(monkeypatch):
    calls = []
    monkeypatch.setattr(
        "coding_agent_telegram.agent_runner.subprocess.Popen",
        make_fake_popen(
            calls,
            process_stdout=(
                '{"type":"assistant","message":{"role":"assistant","content":[{"type":"tool_use","name":"Bash","input":{"command":"ls"}}]},'
                '"session_id":"sess_claude"}\n'
            ),
        ),
    )

    runner = MultiAgentRunner(
        codex_bin="codex",
        copilot_bin="copilot",
        approval_policy="never",
        sandbox_mode="workspace-write",
    )
    runner.PROGRESS_UPDATE_INTERVAL_SECONDS = 0
    captured = []

    runner.create_session("claude", Path("/tmp/project"), "hello", on_progress=captured.append)

    assert captured
    assert captured[0].text == "Using Bash"


def test_claude_runner_progress_surfaces_api_retry(monkeypatch):
    calls = []
    monkeypatch.setattr(
        "coding_agent_telegram.agent_runner.subprocess.Popen",
        make_fake_popen(
            calls,
            process_stdout=(
                '{"type":"system","subtype":"api_retry","attempt":1,"max_retries":3,"retry_delay_ms":500,'
                '"error_status":429,"error":"rate_limit","uuid":"u1","session_id":"sess_claude"}\n'
            ),
        ),
    )

    runner = MultiAgentRunner(
        codex_bin="codex",
        copilot_bin="copilot",
        approval_policy="never",
        sandbox_mode="workspace-write",
    )
    runner.PROGRESS_UPDATE_INTERVAL_SECONDS = 0
    captured = []

    runner.create_session("claude", Path("/tmp/project"), "hello", on_progress=captured.append)

    assert captured
    assert captured[0].text == "Retrying after rate_limit (attempt 1/3)"


def test_claude_runner_rejects_flag_like_session_id(monkeypatch):
    calls = []
    monkeypatch.setattr(
        "coding_agent_telegram.agent_runner.subprocess.Popen",
        make_fake_popen(
            calls,
            process_stdout='{"type":"result","is_error":false,"result":"ok","session_id":"--malicious"}\n',
        ),
    )

    runner = MultiAgentRunner(
        codex_bin="codex",
        copilot_bin="copilot",
        approval_policy="never",
        sandbox_mode="workspace-write",
    )

    result = runner.create_session("claude", Path("/tmp/project"), "hello")

    assert result.session_id is None


def test_claude_runner_ignores_image_paths_without_error(monkeypatch):
    calls = []
    monkeypatch.setattr("coding_agent_telegram.agent_runner.subprocess.Popen", make_fake_popen(calls))

    runner = MultiAgentRunner(
        codex_bin="codex",
        copilot_bin="copilot",
        approval_policy="never",
        sandbox_mode="workspace-write",
    )

    image_path = Path("/tmp/project/.coding-agent-telegram/telegram_attachments/img.jpg")
    result = runner.create_session("claude", Path("/tmp/project"), "hello", image_paths=(image_path,))

    assert "--image" not in calls[0][0]
    assert result.success is True


def test_claude_priming_session_creation_runs_read_only(monkeypatch):
    calls = []
    monkeypatch.setattr("coding_agent_telegram.agent_runner.subprocess.Popen", make_fake_popen(calls))

    runner = MultiAgentRunner(
        codex_bin="codex",
        copilot_bin="copilot",
        approval_policy="never",
        sandbox_mode="workspace-write",
        claude_permission_mode="bypassPermissions",
    )

    runner.create_session("claude", Path("/tmp/project"), "prime me", priming_only=True)

    args = calls[0][0]
    assert args[args.index("--permission-mode") + 1] == "plan"
    assert "bypassPermissions" not in args


def test_claude_session_creation_with_real_prompt_keeps_configured_permission_mode(monkeypatch):
    calls = []
    monkeypatch.setattr("coding_agent_telegram.agent_runner.subprocess.Popen", make_fake_popen(calls))

    runner = MultiAgentRunner(
        codex_bin="codex",
        copilot_bin="copilot",
        approval_policy="never",
        sandbox_mode="workspace-write",
        claude_permission_mode="bypassPermissions",
    )

    # The replacement-session path passes the real user request here, so it must not
    # be downgraded to read-only.
    runner.create_session("claude", Path("/tmp/project"), "fix the bug")

    args = calls[0][0]
    assert args[args.index("--permission-mode") + 1] == "bypassPermissions"


def test_claude_resume_keeps_configured_permission_mode(monkeypatch):
    calls = []
    monkeypatch.setattr("coding_agent_telegram.agent_runner.subprocess.Popen", make_fake_popen(calls))

    runner = MultiAgentRunner(
        codex_bin="codex",
        copilot_bin="copilot",
        approval_policy="never",
        sandbox_mode="workspace-write",
        claude_permission_mode="bypassPermissions",
    )

    runner.resume_session("claude", "sess_abc", Path("/tmp/project"), "keep working")

    args = calls[0][0]
    assert args[args.index("--permission-mode") + 1] == "bypassPermissions"


# ---------------------------------------------------------------------------
# _validate_session_id
# ---------------------------------------------------------------------------


def test_validate_session_id_accepts_valid_ids():
    from coding_agent_telegram.agent_runner import _validate_session_id

    assert _validate_session_id("abc123") == "abc123"
    assert _validate_session_id("sess-1.0_abc") == "sess-1.0_abc"
    assert _validate_session_id("A" * 128) == "A" * 128


def test_validate_session_id_rejects_flag_like():
    from coding_agent_telegram.agent_runner import _validate_session_id

    assert _validate_session_id("--exec") is None
    assert _validate_session_id("-c") is None


def test_validate_session_id_rejects_special_chars():
    from coding_agent_telegram.agent_runner import _validate_session_id

    assert _validate_session_id("sess;rm -rf") is None
    assert _validate_session_id("sess\x00null") is None
    assert _validate_session_id("a" * 129) is None  # too long


def test_validate_session_id_rejects_empty_and_none():
    from coding_agent_telegram.agent_runner import _validate_session_id

    assert _validate_session_id("") is None
    assert _validate_session_id(None) is None  # type: ignore[arg-type]


def test_parse_jsonl_rejects_flag_session_id(monkeypatch):
    """A session_id starting with '--' emitted by the LLM must not be stored."""
    calls: list = []
    monkeypatch.setattr(
        "coding_agent_telegram.agent_runner.subprocess.Popen",
        make_fake_popen(calls, process_stdout='{"session_id": "--malicious"}\n'),
    )
    runner = MultiAgentRunner(
        codex_bin="codex",
        copilot_bin="copilot",
        approval_policy="never",
        sandbox_mode="workspace-write",
    )
    result = runner.create_session("codex", Path("/tmp/project"), "hello", skip_git_repo_check=True)
    assert result.session_id is None


def test_parse_jsonl_accepts_valid_session_id(monkeypatch):
    """A well-formed session_id from the LLM must be stored and returned."""
    calls: list = []
    monkeypatch.setattr(
        "coding_agent_telegram.agent_runner.subprocess.Popen",
        make_fake_popen(calls, process_stdout='{"session_id": "valid-sess-123"}\n'),
    )
    runner = MultiAgentRunner(
        codex_bin="codex",
        copilot_bin="copilot",
        approval_policy="never",
        sandbox_mode="workspace-write",
    )
    result = runner.create_session("codex", Path("/tmp/project"), "hello", skip_git_repo_check=True)
    assert result.session_id == "valid-sess-123"


# ---------------------------------------------------------------------------
# Unsupported provider
# ---------------------------------------------------------------------------


def test_create_session_returns_failure_for_unsupported_provider(monkeypatch):
    calls: list = []
    monkeypatch.setattr("coding_agent_telegram.agent_runner.subprocess.Popen", make_fake_popen(calls))

    runner = MultiAgentRunner(
        codex_bin="codex",
        copilot_bin="copilot",
        approval_policy="never",
        sandbox_mode="workspace-write",
    )
    result = runner.create_session("badprovider", Path("/tmp/project"), "hello")

    assert result.success is False
    assert "Unsupported provider" in (result.error_message or "")
    assert calls == []  # no subprocess launched


def test_resume_session_returns_failure_for_unsupported_provider(monkeypatch):
    calls: list = []
    monkeypatch.setattr("coding_agent_telegram.agent_runner.subprocess.Popen", make_fake_popen(calls))

    runner = MultiAgentRunner(
        codex_bin="codex",
        copilot_bin="copilot",
        approval_policy="never",
        sandbox_mode="workspace-write",
    )
    result = runner.resume_session("badprovider", "sess_1", Path("/tmp/project"), "hello")

    assert result.success is False
    assert "Unsupported provider" in (result.error_message or "")
    assert calls == []


def test_copilot_resume_rejects_image_attachments(monkeypatch):
    calls: list = []
    monkeypatch.setattr("coding_agent_telegram.agent_runner.subprocess.Popen", make_fake_popen(calls))

    runner = MultiAgentRunner(
        codex_bin="codex",
        copilot_bin="copilot",
        approval_policy="never",
        sandbox_mode="workspace-write",
    )
    result = runner.resume_session(
        "copilot",
        "sess_1",
        Path("/tmp/project"),
        "hello",
        image_paths=[Path("/tmp/image.png")],
    )

    assert result.success is False
    assert "not supported" in (result.error_message or "").lower()
    assert calls == []  # no subprocess launched


def test_runner_uses_internal_code_for_generic_command_failure(monkeypatch):
    calls: list = []
    monkeypatch.setattr(
        "coding_agent_telegram.agent_runner.subprocess.Popen",
        make_fake_popen(calls, process_stdout="", process_stderr="", returncode=1),
    )

    runner = MultiAgentRunner(
        codex_bin="codex",
        copilot_bin="copilot",
        approval_policy="never",
        sandbox_mode="workspace-write",
    )
    result = runner.create_session("codex", Path("/tmp/project"), "hello")

    assert result.success is False
    assert result.error_code == "agent_command_failed"
    assert result.error_message is None


# ---------------------------------------------------------------------------
# _collect_text_fragments / _looks_textual_key heuristics
# ---------------------------------------------------------------------------


def test_looks_textual_key_matches_known_tokens():
    runner = MultiAgentRunner("codex", "copilot", "never", "workspace-write")
    assert runner._looks_textual_key("message") is True
    assert runner._looks_textual_key("content") is True
    assert runner._looks_textual_key("delta") is True
    assert runner._looks_textual_key("id") is False
    assert runner._looks_textual_key("") is False


def test_looks_metadata_key_matches_id_timestamp():
    runner = MultiAgentRunner("codex", "copilot", "never", "workspace-write")
    assert runner._looks_metadata_key("session_id") is True
    assert runner._looks_metadata_key("timestamp") is True
    assert runner._looks_metadata_key("text") is False
    assert runner._looks_metadata_key("") is False


def test_collect_text_fragments_extracts_from_nested_dict():
    runner = MultiAgentRunner("codex", "copilot", "never", "workspace-write")
    event = {"message": {"content": "hello from agent"}, "session_id": "ignored"}
    fragments = runner._collect_text_fragments(event)
    assert "hello from agent" in fragments


def test_extract_codex_assistant_text_handles_list_of_strings():
    runner = MultiAgentRunner("codex", "copilot", "never", "workspace-write")
    result = runner._extract_codex_assistant_text(["line 1", "line 2"])
    assert "line 1" in result
    assert "line 2" in result


# ---------------------------------------------------------------------------
# _parse_jsonl: error and session success fields
# ---------------------------------------------------------------------------


def test_parse_jsonl_extracts_success_false_from_error_field(monkeypatch):
    calls: list = []
    monkeypatch.setattr(
        "coding_agent_telegram.agent_runner.subprocess.Popen",
        make_fake_popen(calls, process_stdout='{"error": "agent crashed"}\n', returncode=1),
    )
    runner = MultiAgentRunner("codex", "copilot", "never", "workspace-write")
    result = runner.create_session("codex", Path("/tmp/project"), "hello", skip_git_repo_check=True)
    assert result.success is False


def test_agent_runner_can_abort_registered_process(monkeypatch):
    captured = {}

    def fake_popen(args, cwd=None, env=None, stdout=None, stderr=None, text=None, start_new_session=None):
        proc = FakeBlockingPopen()
        captured["proc"] = proc
        return proc

    monkeypatch.setattr("coding_agent_telegram.agent_runner.subprocess.Popen", fake_popen)

    runner = MultiAgentRunner(
        codex_bin="codex",
        copilot_bin="copilot",
        approval_policy="never",
        sandbox_mode="workspace-write",
    )

    thread = threading.Thread(
        target=lambda: runner.create_session("codex", Path("/tmp/project"), "hello"),
        daemon=True,
    )
    thread.start()

    deadline = time.time() + 1
    while "/tmp/project" not in runner._running_processes and time.time() < deadline:
        time.sleep(0.01)

    assert runner.abort_running_process(Path("/tmp/project")) is True
    assert captured["proc"].killed is True or captured["proc"].terminated is True
