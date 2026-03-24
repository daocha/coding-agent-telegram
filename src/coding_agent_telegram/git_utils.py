from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


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
    def _run(self, project_path: Path, *args: str) -> subprocess.CompletedProcess:
        return subprocess.run(
            ["git", *args],
            cwd=project_path,
            capture_output=True,
            text=True,
            check=False,
        )

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

    def refresh_current_branch(self, project_path: Path) -> BranchOperationResult:
        if not self.is_git_repo(project_path):
            return BranchOperationResult(False, "Current project is not a git repository.")

        current_branch = self.current_branch(project_path)
        if not current_branch:
            return BranchOperationResult(False, "Could not determine the current branch for this repository.")

        warnings: list[str] = []

        fetch = self._run(project_path, "fetch", "origin")
        if fetch.returncode != 0:
            warnings.append(fetch.stderr.strip() or "git fetch origin failed.")
        else:
            pull = self._run(project_path, "pull", "--ff-only", "origin", current_branch)
            if pull.returncode != 0:
                warnings.append(pull.stderr.strip() or f"git pull failed for branch: {current_branch}")

        return BranchOperationResult(
            True,
            f"Updated branch '{current_branch}' from origin.",
            current_branch=current_branch,
            default_branch=self.default_branch(project_path),
            warnings=tuple(warnings),
        )

    def checkout_branch(self, project_path: Path, branch_name: str) -> BranchOperationResult:
        result = self._run(project_path, "checkout", branch_name)
        if result.returncode != 0:
            return BranchOperationResult(False, result.stderr.strip() or f"Failed to checkout branch: {branch_name}")
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

        current_branch = self.current_branch(project_path)
        default_branch = self.default_branch(project_path)
        base_branch = origin_branch or default_branch
        if not base_branch:
            return BranchOperationResult(False, "Could not determine the default branch for this repository.")

        fetch = self._run(project_path, "fetch", "origin")
        if fetch.returncode != 0:
            return BranchOperationResult(False, fetch.stderr.strip() or "git fetch origin failed.")

        checkout_base = self._run(project_path, "checkout", base_branch)
        if checkout_base.returncode != 0:
            return BranchOperationResult(False, checkout_base.stderr.strip() or f"Failed to checkout base branch: {base_branch}")

        pull = self._run(project_path, "pull", "--ff-only", "origin", base_branch)
        if pull.returncode != 0:
            return BranchOperationResult(False, pull.stderr.strip() or f"git pull failed for branch: {base_branch}")

        existing = self._run(project_path, "show-ref", "--verify", f"refs/heads/{new_branch}")
        if existing.returncode == 0:
            return BranchOperationResult(False, f"Branch already exists: {new_branch}")

        create = self._run(project_path, "checkout", "-b", new_branch)
        if create.returncode != 0:
            return BranchOperationResult(False, create.stderr.strip() or f"Failed to create branch: {new_branch}")

        return BranchOperationResult(
            True,
            f"Created branch '{new_branch}' from '{base_branch}'.",
            current_branch=new_branch,
            default_branch=default_branch,
        )

    def run_git_command(self, project_path: Path, args: list[str]) -> GitCommandResult:
        result = self._run(project_path, *args)
        stdout = result.stdout.strip()
        stderr = result.stderr.strip()
        if result.returncode != 0:
            return GitCommandResult(False, stderr or f"git {' '.join(args)} failed.", stdout=stdout, stderr=stderr)
        message = stdout or stderr or f"git {' '.join(args)} completed."
        return GitCommandResult(True, message, stdout=stdout, stderr=stderr)

    def push_branch(self, project_path: Path, branch_name: str) -> BranchOperationResult:
        result = self._run(project_path, "push", "origin", branch_name)
        if result.returncode != 0:
            return BranchOperationResult(False, result.stderr.strip() or f"Failed to push branch: {branch_name}")
        message = result.stdout.strip() or f"Pushed branch '{branch_name}' to origin."
        return BranchOperationResult(True, message, current_branch=branch_name)
