from pathlib import Path
from types import SimpleNamespace

from coding_agent_telegram.agent_runner import MultiAgentRunner


def test_codex_runner_skips_git_repo_check(monkeypatch):
    calls = []

    def fake_run(args, capture_output, text, check, cwd=None, env=None):
        calls.append((args, cwd, env))
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.setattr("coding_agent_telegram.agent_runner.subprocess.run", fake_run)

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

    def fake_run(args, capture_output, text, check, cwd=None, env=None):
        calls.append((args, cwd, env))
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.setattr("coding_agent_telegram.agent_runner.subprocess.run", fake_run)

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

    def fake_run(args, capture_output, text, check, cwd=None, env=None):
        calls.append((args, cwd, env))
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.setattr("coding_agent_telegram.agent_runner.subprocess.run", fake_run)

    runner = MultiAgentRunner(
        codex_bin="codex",
        copilot_bin="copilot",
        approval_policy="never",
        sandbox_mode="workspace-write",
    )

    runner.resume_session("codex", "sess_1", Path("/tmp/project"), "hello again", skip_git_repo_check=True)

    assert calls[0][0] == ["codex", "exec", "resume", "--skip-git-repo-check", "--json", "sess_1", "hello again"]


def test_copilot_runner_uses_prompt_mode_shape(monkeypatch):
    calls = []

    def fake_run(args, capture_output, text, check, cwd=None, env=None):
        calls.append((args, cwd, env))
        return SimpleNamespace(returncode=0, stdout='{"sessionId":"sess_copilot"}\n', stderr="")

    monkeypatch.setattr("coding_agent_telegram.agent_runner.subprocess.run", fake_run)

    runner = MultiAgentRunner(
        codex_bin="codex",
        copilot_bin="copilot",
        approval_policy="never",
        sandbox_mode="workspace-write",
    )

    result = runner.create_session("copilot", Path("/tmp/project"), "hello", skip_git_repo_check=False)

    assert calls[0][0] == ["copilot", "--output-format=json", "--prompt", runner.PROMPT_PREFIX + "hello"]
    assert calls[0][1] == Path("/tmp/project")
    assert result.session_id == "sess_copilot"


def test_copilot_runner_resume_uses_resume_flag(monkeypatch):
    calls = []

    def fake_run(args, capture_output, text, check, cwd=None, env=None):
        calls.append((args, cwd, env))
        return SimpleNamespace(returncode=0, stdout='{"threadId":"sess_copilot"}\n', stderr="")

    monkeypatch.setattr("coding_agent_telegram.agent_runner.subprocess.run", fake_run)

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
        "--output-format=json",
        "--prompt",
        runner.PROMPT_PREFIX + "hello again",
    ]
    assert result.session_id == "sess_copilot"


def test_copilot_runner_uses_project_scoped_home_for_trusted_mode(monkeypatch):
    calls = []

    def fake_run(args, capture_output, text, check, cwd=None, env=None):
        calls.append((args, cwd, env))
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.setattr("coding_agent_telegram.agent_runner.subprocess.run", fake_run)

    runner = MultiAgentRunner(
        codex_bin="codex",
        copilot_bin="copilot",
        approval_policy="never",
        sandbox_mode="workspace-write",
    )

    runner.create_session("copilot", Path("/tmp/project"), "hello", skip_git_repo_check=True)

    assert calls[0][2]["COPILOT_HOME"] == "/tmp/project/.copilot"
    assert calls[0][2]["COPILOT_ALLOW_ALL"] == "true"


def test_codex_runner_passes_model_when_configured(monkeypatch):
    calls = []

    def fake_run(args, capture_output, text, check, cwd=None, env=None):
        calls.append((args, cwd, env))
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.setattr("coding_agent_telegram.agent_runner.subprocess.run", fake_run)

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

    def fake_run(args, capture_output, text, check, cwd=None, env=None):
        calls.append((args, cwd, env))
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.setattr("coding_agent_telegram.agent_runner.subprocess.run", fake_run)

    runner = MultiAgentRunner(
        codex_bin="codex",
        copilot_bin="copilot",
        approval_policy="never",
        sandbox_mode="workspace-write",
        copilot_model="gpt-5",
    )

    runner.create_session("copilot", Path("/tmp/project"), "hello", skip_git_repo_check=False)

    assert calls[0][0][:5] == ["copilot", "--model", "gpt-5", "--output-format=json", "--prompt"]
