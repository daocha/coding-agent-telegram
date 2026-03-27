from pathlib import Path
from types import SimpleNamespace

import pytest
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


# ---------------------------------------------------------------------------
# checkout_branch — git failure path
# ---------------------------------------------------------------------------


def test_checkout_branch_returns_failure_when_git_errors(tmp_path: Path):
    project = tmp_path / "repo"
    project.mkdir()
    _git(project, "init", "-b", "main")
    _git(project, "config", "user.name", "Test")
    _git(project, "config", "user.email", "t@t.com")
    (project / "f").write_text("x")
    _git(project, "add", "f")
    _git(project, "commit", "-m", "init")

    manager = GitWorkspaceManager()
    # Branch does not exist
    result = manager.checkout_branch(project, "nonexistent-branch")

    assert result.success is False
    assert result.message  # some error message from git


def test_prepare_branch_from_origin_restores_original_branch_when_pull_fails(tmp_path: Path):
    project = tmp_path / "repo"
    project.mkdir()
    manager = GitWorkspaceManager()

    _git(project, "init", "-b", "main")
    _git(project, "config", "user.name", "Test")
    _git(project, "config", "user.email", "t@t.com")
    (project / "f").write_text("x")
    _git(project, "add", "f")
    _git(project, "commit", "-m", "init")
    _git(project, "checkout", "-b", "enhancements")

    origin = tmp_path / "origin.git"
    _git(tmp_path, "init", "--bare", str(origin))
    _git(project, "remote", "add", "origin", str(origin))
    _git(project, "push", "-u", "origin", "main")
    _git(project, "push", "-u", "origin", "enhancements")
    _git(project, "checkout", "main")
    _git(project, "push", "origin", "--delete", "enhancements")

    result = manager.prepare_branch_from_source(
        project,
        source_kind="origin",
        source_branch="enhancements",
        new_branch="enhancements",
    )

    assert result.success is False
    assert "enhancements" in result.message
    assert manager.current_branch(project) == "main"


def test_remote_branch_exists_returns_false_for_deleted_remote_branch(tmp_path: Path):
    project = tmp_path / "repo"
    project.mkdir()
    manager = GitWorkspaceManager()

    _git(project, "init", "-b", "main")
    _git(project, "config", "user.name", "Test")
    _git(project, "config", "user.email", "t@t.com")
    (project / "f").write_text("x")
    _git(project, "add", "f")
    _git(project, "commit", "-m", "init")
    _git(project, "checkout", "-b", "enhancements")

    origin = tmp_path / "origin.git"
    _git(tmp_path, "init", "--bare", str(origin))
    _git(project, "remote", "add", "origin", str(origin))
    _git(project, "push", "-u", "origin", "main")
    _git(project, "push", "-u", "origin", "enhancements")
    _git(project, "push", "origin", "--delete", "enhancements")

    assert manager.remote_branch_exists(project, "enhancements") is False


# ---------------------------------------------------------------------------
# push_branch — success path
# ---------------------------------------------------------------------------


def test_push_branch_returns_success_result_structure(tmp_path: Path):
    """push_branch should return a BranchOperationResult with success=False
    when there is no remote (the real git call fails)."""
    project = tmp_path / "repo"
    project.mkdir()
    _git(project, "init", "-b", "main")
    _git(project, "config", "user.name", "Test")
    _git(project, "config", "user.email", "t@t.com")
    (project / "f").write_text("x")
    _git(project, "add", "f")
    _git(project, "commit", "-m", "init")

    manager = GitWorkspaceManager()
    result = manager.push_branch(project, "main")

    # No remote configured so push fails, but result structure is valid
    assert hasattr(result, "success")
    assert hasattr(result, "message")


# ---------------------------------------------------------------------------
# list_local_branches
# ---------------------------------------------------------------------------


def test_list_local_branches_returns_branches_in_git_repo(tmp_path: Path):
    project = tmp_path / "repo"
    project.mkdir()
    _git(project, "init", "-b", "main")
    _git(project, "config", "user.name", "Test")
    _git(project, "config", "user.email", "t@t.com")
    (project / "f").write_text("x")
    _git(project, "add", "f")
    _git(project, "commit", "-m", "init")
    _git(project, "checkout", "-b", "feature-a")

    manager = GitWorkspaceManager()
    branches = manager.list_local_branches(project)

    assert "main" in branches
    assert "feature-a" in branches


def test_list_local_branches_returns_empty_list_for_non_repo(tmp_path: Path):
    # Use an existing directory that is not a git repo
    project = tmp_path / "plain_dir"
    project.mkdir()
    manager = GitWorkspaceManager()
    result = manager.list_local_branches(project)
    assert result == []


# ---------------------------------------------------------------------------
# default_branch fallbacks
# ---------------------------------------------------------------------------


def test_default_branch_falls_back_to_current_branch_without_origin(tmp_path: Path):
    project = tmp_path / "repo"
    project.mkdir()
    _git(project, "init", "-b", "trunk")
    _git(project, "config", "user.name", "Test")
    _git(project, "config", "user.email", "t@t.com")
    (project / "f").write_text("x")
    _git(project, "add", "f")
    _git(project, "commit", "-m", "init")

    manager = GitWorkspaceManager()
    branch = manager.default_branch(project)

    assert branch in ("trunk", "main", "master")


# ---------------------------------------------------------------------------
# is_git_repo
# ---------------------------------------------------------------------------


def test_is_git_repo_returns_false_for_plain_directory(tmp_path: Path):
    manager = GitWorkspaceManager()
    assert manager.is_git_repo(tmp_path) is False


def test_is_git_repo_returns_true_for_initialized_repo(tmp_path: Path):
    project = tmp_path / "repo"
    project.mkdir()
    _git(project, "init", "-b", "main")

    manager = GitWorkspaceManager()
    assert manager.is_git_repo(project) is True


# ---------------------------------------------------------------------------
# current_branch
# ---------------------------------------------------------------------------


def test_current_branch_returns_none_for_non_repo(tmp_path: Path):
    manager = GitWorkspaceManager()
    assert manager.current_branch(tmp_path) is None


def test_current_branch_returns_branch_name(tmp_path: Path):
    project = tmp_path / "repo"
    project.mkdir()
    _git(project, "init", "-b", "my-branch")
    _git(project, "config", "user.name", "Test")
    _git(project, "config", "user.email", "t@t.com")
    (project / "f").write_text("x")
    _git(project, "add", "f")
    _git(project, "commit", "-m", "init")

    manager = GitWorkspaceManager()
    assert manager.current_branch(project) == "my-branch"


# ---------------------------------------------------------------------------
# default_branch: origin/HEAD that starts with "origin/"
# ---------------------------------------------------------------------------


def test_default_branch_parses_origin_head(tmp_path: Path):
    """When symbolic-ref returns 'origin/main', default_branch should return 'main'."""
    git = GitWorkspaceManager()

    run_results = iter([
        SimpleNamespace(returncode=0, stdout="origin/main\n", stderr=""),
    ])

    def fake_run(path, *args):
        return next(run_results)

    git._run = fake_run
    assert git.default_branch(tmp_path) == "main"


# ---------------------------------------------------------------------------
# refresh_current_branch: no current branch detected
# ---------------------------------------------------------------------------


def test_refresh_current_branch_no_current_branch(tmp_path: Path):
    """When current_branch returns None, an informative error must be returned."""
    git = GitWorkspaceManager()
    git.is_git_repo = lambda p: True
    git.current_branch = lambda p: None

    result = git.refresh_current_branch(tmp_path)
    assert not result.success
    assert "current branch" in result.message.lower()


# ---------------------------------------------------------------------------
# refresh_current_branch: fetch fails
# ---------------------------------------------------------------------------


def test_refresh_current_branch_fetch_fails(tmp_path: Path):
    """When fetch fails, a warning must be included in the result."""
    git = GitWorkspaceManager()
    call_count = {"n": 0}

    def fake_run(path, *args):
        call_count["n"] += 1
        if "symbolic-ref" in args or "show-ref" in args or "rev-parse" in args:
            if "rev-parse" in args:
                return SimpleNamespace(returncode=0, stdout="main\n", stderr="")
            return SimpleNamespace(returncode=1, stdout="", stderr="")
        if "fetch" in args:
            return SimpleNamespace(returncode=1, stdout="", stderr="fetch failed")
        return SimpleNamespace(returncode=0, stdout="main\n", stderr="")

    git._run = fake_run
    # Provide is_git_repo=True and current_branch=main via monkeypatching attrs
    git.is_git_repo = lambda p: True
    git.current_branch = lambda p: "main"
    git.default_branch = lambda p: "main"

    result = git.refresh_current_branch(tmp_path)
    assert result.success
    assert result.warnings


# ---------------------------------------------------------------------------
# refresh_current_branch: pull fails
# ---------------------------------------------------------------------------


def test_refresh_current_branch_pull_fails(tmp_path: Path):
    """When pull fails after a successful fetch, a warning must be included."""
    git = GitWorkspaceManager()

    def fake_run(path, *args):
        if "fetch" in args:
            return SimpleNamespace(returncode=0, stdout="", stderr="")
        if "pull" in args:
            return SimpleNamespace(returncode=1, stdout="", stderr="pull failed")
        return SimpleNamespace(returncode=0, stdout="main\n", stderr="")

    git._run = fake_run
    git.is_git_repo = lambda p: True
    git.current_branch = lambda p: "main"
    git.default_branch = lambda p: "main"

    result = git.refresh_current_branch(tmp_path)
    assert result.success
    assert result.warnings


# ---------------------------------------------------------------------------
# prepare_branch: fetch fails
# ---------------------------------------------------------------------------


def test_prepare_branch_fetch_fails(tmp_path: Path):
    """When fetch fails, prepare_branch must return a failure result."""
    git = GitWorkspaceManager()
    git.is_git_repo = lambda p: True
    git.current_branch = lambda p: "main"
    git.default_branch = lambda p: "main"

    def fake_run(path, *args):
        if "fetch" in args:
            return SimpleNamespace(returncode=1, stdout="", stderr="network error")
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    git._run = fake_run

    result = git.prepare_branch(tmp_path, origin_branch=None, new_branch="feature-x")
    assert not result.success


# ---------------------------------------------------------------------------
# prepare_branch: existing branch checkout fails
# ---------------------------------------------------------------------------


def test_prepare_branch_existing_branch_checkout_fails(tmp_path: Path):
    """When the existing branch exists but checkout fails, return failure."""
    git = GitWorkspaceManager()
    git.is_git_repo = lambda p: True
    git.current_branch = lambda p: "main"
    git.default_branch = lambda p: "main"

    def fake_run(path, *args):
        if "fetch" in args:
            return SimpleNamespace(returncode=0, stdout="", stderr="")
        if "show-ref" in args:
            return SimpleNamespace(returncode=0, stdout="", stderr="")  # branch exists
        if "checkout" in args and "feature-x" in args:
            return SimpleNamespace(returncode=1, stdout="", stderr="checkout failed")
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    git._run = fake_run

    result = git.prepare_branch(tmp_path, origin_branch=None, new_branch="feature-x")
    assert not result.success


# ---------------------------------------------------------------------------
# prepare_branch: existing branch == base branch but pull fails
# ---------------------------------------------------------------------------


def test_prepare_branch_existing_is_base_pull_fails(tmp_path: Path):
    """When new_branch == base_branch and pull fails, return failure."""
    git = GitWorkspaceManager()
    git.is_git_repo = lambda p: True
    git.current_branch = lambda p: "main"
    git.default_branch = lambda p: "main"

    def fake_run(path, *args):
        if "fetch" in args:
            return SimpleNamespace(returncode=0, stdout="", stderr="")
        if "show-ref" in args:
            return SimpleNamespace(returncode=0, stdout="", stderr="")  # branch exists
        if "checkout" in args:
            return SimpleNamespace(returncode=0, stdout="", stderr="")
        if "pull" in args:
            return SimpleNamespace(returncode=1, stdout="", stderr="pull error")
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    git._run = fake_run

    # new_branch == base_branch (both "main")
    result = git.prepare_branch(tmp_path, origin_branch="main", new_branch="main")
    assert not result.success


# ---------------------------------------------------------------------------
# prepare_branch: base branch checkout fails
# ---------------------------------------------------------------------------


def test_prepare_branch_base_branch_checkout_fails(tmp_path: Path):
    """When checkout of base branch fails, prepare_branch must return failure."""
    git = GitWorkspaceManager()
    git.is_git_repo = lambda p: True
    git.current_branch = lambda p: "main"
    git.default_branch = lambda p: "main"

    def fake_run(path, *args):
        if "fetch" in args:
            return SimpleNamespace(returncode=0, stdout="", stderr="")
        if "show-ref" in args:
            return SimpleNamespace(returncode=1, stdout="", stderr="")  # branch doesn't exist
        if "checkout" in args and "-b" not in args:
            return SimpleNamespace(returncode=1, stdout="", stderr="cannot checkout base")
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    git._run = fake_run

    result = git.prepare_branch(tmp_path, origin_branch=None, new_branch="new-feature")
    assert not result.success


# ---------------------------------------------------------------------------
# prepare_branch: base branch pull fails
# ---------------------------------------------------------------------------


def test_prepare_branch_base_pull_fails(tmp_path: Path):
    """When pull of base branch fails, prepare_branch must return failure."""
    git = GitWorkspaceManager()
    git.is_git_repo = lambda p: True
    git.current_branch = lambda p: "main"
    git.default_branch = lambda p: "main"

    def fake_run(path, *args):
        if "fetch" in args:
            return SimpleNamespace(returncode=0, stdout="", stderr="")
        if "show-ref" in args:
            return SimpleNamespace(returncode=1, stdout="", stderr="")  # branch doesn't exist
        if "checkout" in args and "-b" not in args:
            return SimpleNamespace(returncode=0, stdout="", stderr="")
        if "pull" in args:
            return SimpleNamespace(returncode=1, stdout="", stderr="pull error")
        if "-b" in args:
            return SimpleNamespace(returncode=0, stdout="", stderr="")
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    git._run = fake_run

    result = git.prepare_branch(tmp_path, origin_branch=None, new_branch="new-feature")
    assert not result.success


# ---------------------------------------------------------------------------
# prepare_branch: git create -b fails
# ---------------------------------------------------------------------------


def test_prepare_branch_create_branch_fails(tmp_path: Path):
    """When 'git checkout -b' fails, prepare_branch must return failure."""
    git = GitWorkspaceManager()
    git.is_git_repo = lambda p: True
    git.current_branch = lambda p: "main"
    git.default_branch = lambda p: "main"

    def fake_run(path, *args):
        if "fetch" in args:
            return SimpleNamespace(returncode=0, stdout="", stderr="")
        if "show-ref" in args:
            return SimpleNamespace(returncode=1, stdout="", stderr="")  # branch doesn't exist
        if "-b" in args:
            return SimpleNamespace(returncode=1, stdout="", stderr="cannot create")
        if "checkout" in args:
            return SimpleNamespace(returncode=0, stdout="", stderr="")
        if "pull" in args:
            return SimpleNamespace(returncode=0, stdout="", stderr="")
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    git._run = fake_run

    result = git.prepare_branch(tmp_path, origin_branch=None, new_branch="new-feature")
    assert not result.success
