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


def test_refresh_current_branch_reports_pull_warnings(tmp_path: Path):
    project = tmp_path / "repo"
    project.mkdir()
    manager = GitWorkspaceManager()

    _git(project, "init", "-b", "main")
    _git(project, "config", "user.name", "Test User")
    _git(project, "config", "user.email", "test@example.com")
    (project / "README.md").write_text("hello\n", encoding="utf-8")
    _git(project, "add", "README.md")
    _git(project, "commit", "-m", "init")

    result = manager.refresh_current_branch(project)

    assert result.success is True
    assert result.current_branch == "main"
    assert result.warnings
    assert "git fetch origin failed." in result.warnings[0] or "fatal:" in result.warnings[0]


def test_run_git_command_returns_stdout_on_success(tmp_path: Path):
    project = tmp_path / "repo"
    project.mkdir()
    manager = GitWorkspaceManager()

    _git(project, "init", "-b", "main")

    result = manager.run_git_command(project, ["rev-parse", "--is-inside-work-tree"])

    assert result.success is True
    assert result.stdout == "true"
    assert result.message == "true"


def test_run_git_command_returns_stderr_on_failure(tmp_path: Path):
    project = tmp_path / "repo"
    project.mkdir()
    manager = GitWorkspaceManager()

    _git(project, "init", "-b", "main")

    result = manager.run_git_command(project, ["checkout", "missing-branch"])

    assert result.success is False
    assert "pathspec 'missing-branch'" in result.message
    assert "pathspec 'missing-branch'" in result.stderr


def test_push_branch_returns_error_for_missing_remote(tmp_path: Path):
    project = tmp_path / "repo"
    project.mkdir()
    manager = GitWorkspaceManager()

    _git(project, "init", "-b", "main")
    _git(project, "config", "user.name", "Test User")
    _git(project, "config", "user.email", "test@example.com")
    (project / "README.md").write_text("hello\n", encoding="utf-8")
    _git(project, "add", "README.md")
    _git(project, "commit", "-m", "init")

    result = manager.push_branch(project, "main")

    assert result.success is False
    assert "origin" in result.message


def test_run_safe_commit_command_preserves_local_git_identity(tmp_path: Path):
    project = tmp_path / "repo"
    project.mkdir()
    manager = GitWorkspaceManager()

    _git(project, "init", "-b", "main")
    _git(project, "config", "user.name", "Test User")
    _git(project, "config", "user.email", "test@example.com")
    (project / "README.md").write_text("hello\n", encoding="utf-8")
    _git(project, "add", "README.md")

    result = manager.run_safe_commit_command(project, ["commit", "-m", "init"])

    assert result.success is True
    name = (
        __import__("subprocess")
        .run(
            ["git", "log", "-1", "--format=%an <%ae>"],
            cwd=project,
            check=True,
            capture_output=True,
            text=True,
        )
        .stdout.strip()
    )
    assert name == "Test User <test@example.com>"


def test_run_safe_commit_command_prefers_explicit_git_identity_env(tmp_path: Path, monkeypatch):
    project = tmp_path / "repo"
    project.mkdir()
    manager = GitWorkspaceManager()

    _git(project, "init", "-b", "main")
    _git(project, "config", "user.name", "Config User")
    _git(project, "config", "user.email", "config@example.com")
    monkeypatch.setenv("GIT_AUTHOR_NAME", "Env User")
    monkeypatch.setenv("GIT_AUTHOR_EMAIL", "env@example.com")
    monkeypatch.setenv("GIT_COMMITTER_NAME", "Env User")
    monkeypatch.setenv("GIT_COMMITTER_EMAIL", "env@example.com")
    (project / "README.md").write_text("hello\n", encoding="utf-8")
    _git(project, "add", "README.md")

    result = manager.run_safe_commit_command(project, ["commit", "-m", "init"])

    assert result.success is True
    name = (
        __import__("subprocess")
        .run(
            ["git", "log", "-1", "--format=%an <%ae>"],
            cwd=project,
            check=True,
            capture_output=True,
            text=True,
        )
        .stdout.strip()
    )
    assert name == "Env User <env@example.com>"


# ---------------------------------------------------------------------------
# _validate_branch_name
# ---------------------------------------------------------------------------


def test_validate_branch_name_accepts_valid_names():
    from coding_agent_telegram.git_utils import _validate_branch_name

    assert _validate_branch_name("main") is True
    assert _validate_branch_name("feature/TICKET-123") is True
    assert _validate_branch_name("hotfix-1.0") is True
    assert _validate_branch_name("origin/main") is True
    assert _validate_branch_name("A" * 200) is True


def test_validate_branch_name_rejects_flag_like():
    from coding_agent_telegram.git_utils import _validate_branch_name

    assert _validate_branch_name("-b") is False
    assert _validate_branch_name("--exec") is False
    assert _validate_branch_name("") is False


def test_validate_branch_name_rejects_special_chars():
    from coding_agent_telegram.git_utils import _validate_branch_name

    assert _validate_branch_name("branch;rm") is False
    assert _validate_branch_name("branch name") is False  # space
    assert _validate_branch_name("branch\x00null") is False
    assert _validate_branch_name("a" * 201) is False  # too long


def test_checkout_branch_rejects_invalid_name(tmp_path: Path):
    """checkout_branch must reject branch names that fail validation without making git calls."""
    project = tmp_path / "repo"
    project.mkdir()
    manager = GitWorkspaceManager()

    result = manager.checkout_branch(project, "--malicious")

    assert result.success is False
    assert "Invalid branch name" in result.message


def test_prepare_branch_rejects_invalid_new_branch(tmp_path: Path):
    """prepare_branch must reject an invalid new_branch without making git calls."""
    project = tmp_path / "repo"
    project.mkdir()
    _git(project, "init", "-b", "main")
    _git(project, "config", "user.name", "Test")
    _git(project, "config", "user.email", "t@t.com")
    (project / "f").write_text("x")
    _git(project, "add", "f")
    _git(project, "commit", "-m", "init")

    manager = GitWorkspaceManager()
    result = manager.prepare_branch(project, origin_branch=None, new_branch="-exec")

    assert result.success is False
    assert "Invalid branch name" in result.message


def test_prepare_branch_rejects_invalid_origin_branch(tmp_path: Path):
    """prepare_branch must reject an invalid origin_branch without making git calls."""
    project = tmp_path / "repo"
    project.mkdir()
    _git(project, "init", "-b", "main")
    _git(project, "config", "user.name", "Test")
    _git(project, "config", "user.email", "t@t.com")
    (project / "f").write_text("x")
    _git(project, "add", "f")
    _git(project, "commit", "-m", "init")

    manager = GitWorkspaceManager()
    result = manager.prepare_branch(project, origin_branch="--bad", new_branch="good-branch")

    assert result.success is False
    assert "Invalid" in result.message
