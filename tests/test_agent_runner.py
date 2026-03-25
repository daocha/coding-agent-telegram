import io
from pathlib import Path

from coding_agent_telegram.agent_runner import MultiAgentRunner


class FakePopen:
    def __init__(self, stdout: str = "", stderr: str = "", returncode: int = 0):
        self.stdout = io.StringIO(stdout)
        self.stderr = io.StringIO(stderr)
        self.returncode = returncode

    def poll(self):
        return self.returncode


def make_fake_popen(
    calls: list[tuple[list[str], Path | None, dict | None]],
    *,
    process_stdout: str = "",
    process_stderr: str = "",
    returncode: int = 0,
):
    def fake_popen(args, cwd=None, env=None, stdout=None, stderr=None, text=None):
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
        "--autopilot",
        "--no-ask-user",
        "--allow-all",
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


def test_copilot_runner_uses_project_scoped_home_for_trusted_mode(monkeypatch):
    calls = []
    monkeypatch.setattr("coding_agent_telegram.agent_runner.subprocess.Popen", make_fake_popen(calls))

    runner = MultiAgentRunner(
        codex_bin="codex",
        copilot_bin="copilot",
        approval_policy="never",
        sandbox_mode="workspace-write",
    )

    runner.create_session("copilot", Path("/tmp/project"), "hello", skip_git_repo_check=True)

    assert calls[0][2]["COPILOT_HOME"] == "/tmp/project/.copilot"
    assert "--allow-all" in calls[0][0]


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

    assert calls[0][0][:8] == [
        "copilot",
        "--model",
        "gpt-5",
        "--autopilot",
        "--no-ask-user",
        "--allow-all",
        "--output-format=json",
        "--prompt",
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

    assert "--allow-all-tools" in calls[0][0]
    assert calls[0][0].count("--allow-tool") == 2
    assert "shell(git)" in calls[0][0]
    assert "shell(npm)" in calls[0][0]
    assert "--deny-tool" in calls[0][0]
    assert "shell(rm)" in calls[0][0]
    assert "--available-tools" in calls[0][0]
    assert "shell,apply_patch" in calls[0][0]
