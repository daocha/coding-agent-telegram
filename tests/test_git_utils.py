from pathlib import Path

from coding_agent_telegram.git_utils import GitWorkspaceManager


def _git(project_path: Path, *args: str) -> None:
    import subprocess

    subprocess.run(["git", *args], cwd=project_path, check=True, capture_output=True, text=True)


def test_prepare_branch_switches_to_existing_branch(tmp_path: Path):
    project = tmp_path / "repo"
    project.mkdir()
    manager = GitWorkspaceManager()

    _git(project, "init", "-b", "main")
    _git(project, "config", "user.name", "Test User")
    _git(project, "config", "user.email", "test@example.com")
    (project / "README.md").write_text("hello\n", encoding="utf-8")
    _git(project, "add", "README.md")
    _git(project, "commit", "-m", "init")
    _git(project, "branch", "feature-1")

    origin = tmp_path / "origin.git"
    _git(tmp_path, "init", "--bare", str(origin))
    _git(project, "remote", "add", "origin", str(origin))
    _git(project, "push", "-u", "origin", "main")
    _git(project, "push", "origin", "feature-1")
    _git(project, "checkout", "feature-1")

    result = manager.prepare_branch(project, origin_branch=None, new_branch="main")

    assert result.success is True
    assert result.current_branch == "main"
    assert result.message == "Switched to existing branch 'main'."
