from __future__ import annotations

import os
import re
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


def _sanitize_git_output(text: str) -> str:
    """Sanitize git command output to remove credential information."""
    if not text:
        return text
    
    # Remove HTTPS credentials: Match everything before first / after https://
    # This handles passwords with special characters like @ or :
    sanitized = re.sub(r'https://[^/]+@', 'https://***@', text)
    
    # Remove SSH host keys and connection info
    sanitized = re.sub(
        r'The authenticity of host .+? can\'t be established\..*',
        '(SSH host key verification)',
        sanitized,
        flags=re.DOTALL
    )
    
    return sanitized


# Allows letters, digits, dots, hyphens, forward-slashes (remote/branch).
# Must not start with '-' to prevent flag injection into git subcommands.
_BRANCH_NAME_RE = re.compile(r"^[A-Za-z0-9._/\-]{1,200}$")


def _validate_branch_name(name: str) -> bool:
    """Return True only if *name* is safe to pass as a git branch name argument."""
    if not name:
        return False
    if name.startswith("-"):
        return False
    return bool(_BRANCH_NAME_RE.match(name))


@dataclass
class GitCommandResult:
    success: bool
    message: str
    stdout: str = ""
    stderr: str = ""


@dataclass
class BranchOperationResult:
    success: bool
    message: str
    current_branch: Optional[str] = None
    default_branch: Optional[str] = None
    warnings: tuple[str, ...] = ()


class GitWorkspaceManager:
    SAFE_COMMIT_CONFIG = (
        "-c",
        f"core.hooksPath={os.devnull}",
        "-c",
        "filter.lfs.process=",
        "-c",
        "filter.lfs.smudge=",
        "-c",
        "filter.lfs.clean=",
    )

    def _run(self, project_path: Path, *args: str, env: Optional[dict[str, str]] = None) -> subprocess.CompletedProcess:
        return subprocess.run(
            ["git", *args],
            cwd=project_path,
            capture_output=True,
            text=True,
            check=False,
            env=env,
        )

    def _resolved_commit_identity(self, project_path: Path) -> dict[str, str]:
        identity: dict[str, str] = {}
        for key in ("GIT_AUTHOR_NAME", "GIT_AUTHOR_EMAIL", "GIT_COMMITTER_NAME", "GIT_COMMITTER_EMAIL"):
            value = os.environ.get(key, "").strip()
            if value:
                identity[key] = value

        if "GIT_AUTHOR_NAME" not in identity or "GIT_COMMITTER_NAME" not in identity:
            result = self._run(project_path, "config", "--get", "user.name")
            name = result.stdout.strip() if result.returncode == 0 else ""
            if name:
                identity.setdefault("GIT_AUTHOR_NAME", name)
                identity.setdefault("GIT_COMMITTER_NAME", name)

        if "GIT_AUTHOR_EMAIL" not in identity or "GIT_COMMITTER_EMAIL" not in identity:
            result = self._run(project_path, "config", "--get", "user.email")
            email = result.stdout.strip() if result.returncode == 0 else ""
            if email:
                identity.setdefault("GIT_AUTHOR_EMAIL", email)
                identity.setdefault("GIT_COMMITTER_EMAIL", email)

        return identity

    def is_git_repo(self, project_path: Path) -> bool:
        result = self._run(project_path, "rev-parse", "--is-inside-work-tree")
        return result.returncode == 0 and result.stdout.strip() == "true"

    def current_branch(self, project_path: Path) -> Optional[str]:
        result = self._run(project_path, "branch", "--show-current")
        if result.returncode != 0:
            return None
        branch = result.stdout.strip()
        return branch or None

    def default_branch(self, project_path: Path) -> Optional[str]:
        origin_head = self._run(project_path, "symbolic-ref", "--short", "refs/remotes/origin/HEAD")
        if origin_head.returncode == 0:
            value = origin_head.stdout.strip()
            if value.startswith("origin/"):
                return value.split("/", 1)[1]

        for candidate in ("main", "master"):
            check = self._run(project_path, "show-ref", "--verify", f"refs/heads/{candidate}")
            if check.returncode == 0:
                return candidate

        return self.current_branch(project_path)

    def list_local_branches(self, project_path: Path) -> list[str]:
        result = self._run(project_path, "for-each-ref", "--format=%(refname:short)", "refs/heads")
        if result.returncode != 0:
            return []
        return [line.strip() for line in result.stdout.splitlines() if line.strip()]

    def local_branch_exists(self, project_path: Path, branch_name: str) -> bool:
        if not _validate_branch_name(branch_name):
            return False
        result = self._run(project_path, "show-ref", "--verify", f"refs/heads/{branch_name}")
        return result.returncode == 0

    def remote_branch_exists(self, project_path: Path, branch_name: str) -> bool:
        if not _validate_branch_name(branch_name):
            return False
        result = self._run(project_path, "ls-remote", "--exit-code", "--heads", "origin", branch_name)
        return result.returncode == 0

    def branch_upstream(self, project_path: Path, branch_name: str) -> Optional[str]:
        if not _validate_branch_name(branch_name):
            return None
        result = self._run(project_path, "for-each-ref", "--format=%(upstream:short)", f"refs/heads/{branch_name}")
        if result.returncode == 0:
            upstream = result.stdout.strip()
            if upstream:
                return upstream
        remote_result = self._run(project_path, "config", "--get", f"branch.{branch_name}.remote")
        merge_result = self._run(project_path, "config", "--get", f"branch.{branch_name}.merge")
        remote_name = remote_result.stdout.strip() if remote_result.returncode == 0 else ""
        merge_ref = merge_result.stdout.strip() if merge_result.returncode == 0 else ""
        if not remote_name or not merge_ref.startswith("refs/heads/"):
            return None
        return f"{remote_name}/{merge_ref.removeprefix('refs/heads/')}"

    def _remote_exists(self, project_path: Path, remote_name: str) -> bool:
        if not remote_name:
            return False
        result = self._run(project_path, "remote", "get-url", remote_name)
        return result.returncode == 0

    def _set_branch_upstream(self, project_path: Path, branch_name: str, upstream: str) -> GitCommandResult:
        if not _validate_branch_name(branch_name):
            return GitCommandResult(False, f"Invalid branch name: {branch_name!r}")
        if not upstream or upstream.startswith("-"):
            return GitCommandResult(False, f"Invalid upstream branch: {upstream!r}")
        result = self._run(project_path, "branch", f"--set-upstream-to={upstream}", branch_name)
        if result.returncode != 0:
            message = _sanitize_git_output(result.stderr.strip()) or f"Failed to set upstream for branch: {branch_name}"
            return GitCommandResult(False, message, stdout=result.stdout.strip(), stderr=result.stderr.strip())
        message = result.stdout.strip() or f"Set upstream for branch '{branch_name}' to '{upstream}'."
        return GitCommandResult(True, message, stdout=result.stdout.strip(), stderr=result.stderr.strip())

    def _configure_branch_upstream_target(self, project_path: Path, branch_name: str, *, remote_name: str, remote_branch: str) -> GitCommandResult:
        if not _validate_branch_name(branch_name):
            return GitCommandResult(False, f"Invalid branch name: {branch_name!r}")
        if not remote_name or remote_name.startswith("-"):
            return GitCommandResult(False, f"Invalid remote name: {remote_name!r}")
        if not _validate_branch_name(remote_branch):
            return GitCommandResult(False, f"Invalid remote branch name: {remote_branch!r}")
        set_remote = self._run(project_path, "config", f"branch.{branch_name}.remote", remote_name)
        if set_remote.returncode != 0:
            message = _sanitize_git_output(set_remote.stderr.strip()) or f"Failed to configure remote for branch: {branch_name}"
            return GitCommandResult(False, message, stdout=set_remote.stdout.strip(), stderr=set_remote.stderr.strip())
        set_merge = self._run(project_path, "config", f"branch.{branch_name}.merge", f"refs/heads/{remote_branch}")
        if set_merge.returncode != 0:
            message = _sanitize_git_output(set_merge.stderr.strip()) or f"Failed to configure upstream branch for: {branch_name}"
            return GitCommandResult(False, message, stdout=set_merge.stdout.strip(), stderr=set_merge.stderr.strip())
        return GitCommandResult(True, f"Configured upstream target for branch '{branch_name}' as '{remote_name}/{remote_branch}'.")

    def refresh_current_branch(self, project_path: Path) -> BranchOperationResult:
        if not self.is_git_repo(project_path):
            return BranchOperationResult(False, "Current project is not a git repository.")

        current_branch = self.current_branch(project_path)
        if not current_branch:
            return BranchOperationResult(False, "Could not determine the current branch for this repository.")

        warnings: list[str] = []

        fetch = self._run(project_path, "fetch", "origin")
        if fetch.returncode != 0:
            warnings.append(_sanitize_git_output(fetch.stderr.strip()) or "git fetch origin failed.")
        else:
            pull = self._run(project_path, "pull", "--ff-only", "origin", current_branch)
            if pull.returncode != 0:
                warnings.append(_sanitize_git_output(pull.stderr.strip()) or f"git pull failed for branch: {current_branch}")

        return BranchOperationResult(
            True,
            f"Updated branch '{current_branch}' from origin.",
            current_branch=current_branch,
            default_branch=self.default_branch(project_path),
            warnings=tuple(warnings),
        )

    def checkout_branch(self, project_path: Path, branch_name: str) -> BranchOperationResult:
        if not _validate_branch_name(branch_name):
            return BranchOperationResult(False, f"Invalid branch name: {branch_name!r}")
        result = self._run(project_path, "checkout", branch_name)
        if result.returncode != 0:
            return BranchOperationResult(False, _sanitize_git_output(result.stderr.strip()) or f"Failed to checkout branch: {branch_name}")
        return BranchOperationResult(True, f"Checked out branch: {branch_name}", current_branch=branch_name)

    def prepare_branch(
        self,
        project_path: Path,
        *,
        origin_branch: Optional[str],
        new_branch: str,
    ) -> BranchOperationResult:
        if not self.is_git_repo(project_path):
            return BranchOperationResult(False, "Current project is not a git repository.")
        if not _validate_branch_name(new_branch):
            return BranchOperationResult(False, f"Invalid branch name: {new_branch!r}")
        if origin_branch and not _validate_branch_name(origin_branch):
            return BranchOperationResult(False, f"Invalid origin branch name: {origin_branch!r}")

        current_branch = self.current_branch(project_path)
        default_branch = self.default_branch(project_path)
        base_branch = origin_branch or default_branch
        if not base_branch:
            return BranchOperationResult(False, "Could not determine the default branch for this repository.")

        fetch = self._run(project_path, "fetch", "origin")
        if fetch.returncode != 0:
            return BranchOperationResult(False, fetch.stderr.strip() or "git fetch origin failed.")

        existing = self._run(project_path, "show-ref", "--verify", f"refs/heads/{new_branch}")
        if existing.returncode == 0:
            checkout_existing = self._run(project_path, "checkout", new_branch)
            if checkout_existing.returncode != 0:
                return BranchOperationResult(
                    False,
                    checkout_existing.stderr.strip() or f"Failed to checkout branch: {new_branch}",
                )

            if new_branch == base_branch:
                pull_existing = self._run(project_path, "pull", "--ff-only", "origin", new_branch)
                if pull_existing.returncode != 0:
                    return BranchOperationResult(
                        False,
                        pull_existing.stderr.strip() or f"git pull failed for branch: {new_branch}",
                    )

            message = (
                f"Already on branch '{new_branch}'."
                if current_branch == new_branch
                else f"Switched to existing branch '{new_branch}'."
            )
            return BranchOperationResult(
                True,
                message,
                current_branch=new_branch,
                default_branch=default_branch,
            )

        checkout_base = self._run(project_path, "checkout", base_branch)
        if checkout_base.returncode != 0:
            return BranchOperationResult(False, _sanitize_git_output(checkout_base.stderr.strip()) or f"Failed to checkout base branch: {base_branch}")

        pull = self._run(project_path, "pull", "--ff-only", "origin", base_branch)
        if pull.returncode != 0:
            return BranchOperationResult(False, _sanitize_git_output(pull.stderr.strip()) or f"git pull failed for branch: {base_branch}")

        create = self._run(project_path, "checkout", "-b", new_branch)
        if create.returncode != 0:
            return BranchOperationResult(False, _sanitize_git_output(create.stderr.strip()) or f"Failed to create branch: {new_branch}")

        return BranchOperationResult(
            True,
            f"Created branch '{new_branch}' from '{base_branch}'.",
            current_branch=new_branch,
            default_branch=default_branch,
        )

    def prepare_branch_from_source(
        self,
        project_path: Path,
        *,
        source_kind: str,
        source_branch: str,
        new_branch: str,
    ) -> BranchOperationResult:
        if not self.is_git_repo(project_path):
            return BranchOperationResult(False, "Current project is not a git repository.")
        if source_kind not in {"local", "origin"}:
            return BranchOperationResult(False, f"Invalid branch source kind: {source_kind!r}")
        if not _validate_branch_name(source_branch):
            return BranchOperationResult(False, f"Invalid source branch name: {source_branch!r}")
        if not _validate_branch_name(new_branch):
            return BranchOperationResult(False, f"Invalid branch name: {new_branch!r}")

        default_branch = self.default_branch(project_path)
        current_branch = self.current_branch(project_path)
        original_branch = current_branch

        def rollback_failure(message: str) -> BranchOperationResult:
            if not original_branch:
                return BranchOperationResult(False, message)
            active_branch = self.current_branch(project_path)
            if active_branch == original_branch:
                return BranchOperationResult(False, message)
            restore = self._run(project_path, "checkout", original_branch)
            if restore.returncode != 0:
                restore_message = _sanitize_git_output(restore.stderr.strip()) or (
                    f"Failed to restore previous branch: {original_branch}"
                )
                return BranchOperationResult(
                    False,
                    f"{message}\nAlso failed to restore previous branch '{original_branch}': {restore_message}",
                )
            return BranchOperationResult(False, message)

        if source_kind == "local":
            if not self.local_branch_exists(project_path, source_branch):
                return BranchOperationResult(False, f"Local branch does not exist: {source_branch}")
            if source_branch == new_branch:
                checkout = self._run(project_path, "checkout", new_branch)
                if checkout.returncode != 0:
                    return BranchOperationResult(
                        False,
                        _sanitize_git_output(checkout.stderr.strip()) or f"Failed to checkout branch: {new_branch}",
                    )
                message = (
                    f"Already on branch '{new_branch}'."
                    if current_branch == new_branch
                    else f"Switched to existing local branch '{new_branch}'."
                )
                return BranchOperationResult(True, message, current_branch=new_branch, default_branch=default_branch)

            checkout_source = self._run(project_path, "checkout", source_branch)
            if checkout_source.returncode != 0:
                return BranchOperationResult(
                    False,
                    _sanitize_git_output(checkout_source.stderr.strip()) or f"Failed to checkout source branch: {source_branch}",
                )
            existing = self.local_branch_exists(project_path, new_branch)
            if existing:
                checkout_existing = self._run(project_path, "checkout", new_branch)
                if checkout_existing.returncode != 0:
                    return rollback_failure(
                        _sanitize_git_output(checkout_existing.stderr.strip()) or f"Failed to checkout branch: {new_branch}",
                    )
                return BranchOperationResult(
                    True,
                    f"Switched to existing local branch '{new_branch}'.",
                    current_branch=new_branch,
                    default_branch=default_branch,
                )
            create = self._run(project_path, "checkout", "-b", new_branch)
            if create.returncode != 0:
                return rollback_failure(
                    _sanitize_git_output(create.stderr.strip()) or f"Failed to create branch: {new_branch}",
                )
            if self._remote_exists(project_path, "origin"):
                set_upstream = self._configure_branch_upstream_target(
                    project_path,
                    new_branch,
                    remote_name="origin",
                    remote_branch=new_branch,
                )
                if not set_upstream.success:
                    return rollback_failure(set_upstream.message)
            return BranchOperationResult(
                True,
                f"Created branch '{new_branch}' from local branch '{source_branch}'.",
                current_branch=new_branch,
                default_branch=default_branch,
            )

        fetch = self._run(project_path, "fetch", "origin")
        if fetch.returncode != 0:
            return BranchOperationResult(False, _sanitize_git_output(fetch.stderr.strip()) or "git fetch origin failed.")
        if not self.remote_branch_exists(project_path, source_branch):
            return BranchOperationResult(False, f"Remote branch does not exist: origin/{source_branch}")

        if source_branch == new_branch:
            if self.local_branch_exists(project_path, new_branch):
                if current_branch == new_branch:
                    pull = self._run(project_path, "pull", "--ff-only", "origin", source_branch)
                    if pull.returncode != 0:
                        return BranchOperationResult(
                            False,
                            _sanitize_git_output(pull.stderr.strip()) or f"git pull failed for branch: {source_branch}",
                        )
                else:
                    update_local = self._run(project_path, "fetch", "origin", f"{source_branch}:{new_branch}")
                    if update_local.returncode != 0:
                        return BranchOperationResult(
                            False,
                            _sanitize_git_output(update_local.stderr.strip())
                            or f"Failed to update local branch '{new_branch}' from origin/{source_branch}",
                        )
                    checkout_existing = self._run(project_path, "checkout", new_branch)
                    if checkout_existing.returncode != 0:
                        return BranchOperationResult(
                            False,
                            _sanitize_git_output(checkout_existing.stderr.strip()) or f"Failed to checkout branch: {new_branch}",
                        )
                current_upstream = self.branch_upstream(project_path, new_branch)
                desired_upstream = f"origin/{source_branch}"
                if current_upstream != desired_upstream:
                    set_upstream = self._set_branch_upstream(project_path, new_branch, desired_upstream)
                    if not set_upstream.success:
                        return BranchOperationResult(False, set_upstream.message)
            else:
                checkout_new = self._run(project_path, "checkout", "-b", new_branch, "--track", f"origin/{source_branch}")
                if checkout_new.returncode != 0:
                    return BranchOperationResult(
                        False,
                        _sanitize_git_output(checkout_new.stderr.strip()) or f"Failed to checkout branch: {new_branch}",
                    )
            return BranchOperationResult(
                True,
                f"Updated branch '{new_branch}' from origin/{source_branch} and switched to it.",
                current_branch=new_branch,
                default_branch=default_branch,
            )

        if self.local_branch_exists(project_path, new_branch):
            checkout_existing = self._run(project_path, "checkout", new_branch)
            if checkout_existing.returncode != 0:
                return BranchOperationResult(
                    False,
                    _sanitize_git_output(checkout_existing.stderr.strip()) or f"Failed to checkout branch: {new_branch}",
                )
            return BranchOperationResult(
                True,
                f"Switched to existing local branch '{new_branch}' after fetching origin/{source_branch}.",
                current_branch=new_branch,
                default_branch=default_branch,
            )

        create = self._run(project_path, "checkout", "-b", new_branch, f"origin/{source_branch}")
        if create.returncode != 0:
            return BranchOperationResult(
                False,
                _sanitize_git_output(create.stderr.strip()) or f"Failed to create branch: {new_branch}",
            )
        set_upstream = self._configure_branch_upstream_target(
            project_path,
            new_branch,
            remote_name="origin",
            remote_branch=new_branch,
        )
        if not set_upstream.success:
            return rollback_failure(set_upstream.message)
        return BranchOperationResult(
            True,
            f"Created branch '{new_branch}' from origin/{source_branch}.",
            current_branch=new_branch,
            default_branch=default_branch,
        )

    def run_git_command(self, project_path: Path, args: list[str]) -> GitCommandResult:
        result = self._run(project_path, *args)
        stdout = result.stdout.strip()
        stderr = result.stderr.strip()
        if result.returncode != 0:
            sanitized_stderr = _sanitize_git_output(stderr)
            return GitCommandResult(False, sanitized_stderr or f"git {' '.join(args)} failed.", stdout=sanitized_stderr, stderr=sanitized_stderr)
        sanitized_stdout = _sanitize_git_output(stdout)
        sanitized_stderr = _sanitize_git_output(stderr)
        message = sanitized_stdout or sanitized_stderr or f"git {' '.join(args)} completed."
        return GitCommandResult(True, message, stdout=sanitized_stdout, stderr=sanitized_stderr)

    def run_safe_commit_command(self, project_path: Path, args: list[str]) -> GitCommandResult:
        with tempfile.TemporaryDirectory(prefix="coding-agent-telegram-git-") as temp_home:
            env = os.environ.copy()
            env.update(
                {
                    "GIT_CONFIG_NOSYSTEM": "1",
                    "GIT_TERMINAL_PROMPT": "0",
                    "HOME": temp_home,
                    "XDG_CONFIG_HOME": temp_home,
                }
            )
            env.update(self._resolved_commit_identity(project_path))
            result = self._run(project_path, *self.SAFE_COMMIT_CONFIG, *args, env=env)

        stdout = result.stdout.strip()
        stderr = result.stderr.strip()
        if result.returncode != 0:
            sanitized_stderr = _sanitize_git_output(stderr)
            return GitCommandResult(False, sanitized_stderr or f"git {' '.join(args)} failed.", stdout=sanitized_stderr, stderr=sanitized_stderr)
        sanitized_stdout = _sanitize_git_output(stdout)
        sanitized_stderr = _sanitize_git_output(stderr)
        message = sanitized_stdout or sanitized_stderr or f"git {' '.join(args)} completed."
        return GitCommandResult(True, message, stdout=sanitized_stdout, stderr=sanitized_stderr)

    def push_branch(self, project_path: Path, branch_name: str) -> BranchOperationResult:
        result = self._run(project_path, "push", "origin", branch_name)
        if result.returncode != 0:
            return BranchOperationResult(False, _sanitize_git_output(result.stderr.strip()) or f"Failed to push branch: {branch_name}")
        message = result.stdout.strip() or f"Pushed branch '{branch_name}' to origin."
        return BranchOperationResult(True, message, current_branch=branch_name)
