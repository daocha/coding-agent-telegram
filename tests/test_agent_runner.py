from pathlib import Path
from types import SimpleNamespace

from coding_agent_telegram.agent_runner import MultiAgentRunner


def test_codex_runner_skips_git_repo_check(monkeypatch):
    calls = []

    def fake_run(args, capture_output, text, check, cwd=None):
        calls.append((args, cwd))
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

    def fake_run(args, capture_output, text, check, cwd=None):
        calls.append((args, cwd))
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

    def fake_run(args, capture_output, text, check, cwd=None):
        calls.append((args, cwd))
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
