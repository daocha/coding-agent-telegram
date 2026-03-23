from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass
class FileDiff:
    path: str
    diff: str


def _git(project_path: Path, args: list[str]) -> str:
    proc = subprocess.run(["git", "-C", str(project_path), *args], capture_output=True, text=True, check=False)
    return proc.stdout


def changed_files(project_path: Path) -> list[str]:
    output = _git(project_path, ["diff", "--name-only"])
    return [line.strip() for line in output.splitlines() if line.strip()]


def collect_diffs(project_path: Path, files: list[str]) -> list[FileDiff]:
    results: list[FileDiff] = []
    for path in files:
        diff = _git(project_path, ["diff", "--", path])
        results.append(FileDiff(path=path, diff=diff.strip()))
    return results


def build_summary(session_name: str, project_folder: str, files: list[str]) -> str:
    lines = [
        "Task completed.",
        f"Session: {session_name}",
        f"Project: {project_folder}",
        "",
        "Changed files:",
    ]
    if files:
        lines.extend([f"- {f}" for f in files])
    else:
        lines.append("- (none)")
    return "\n".join(lines)


def chunk_fenced_diff(file_path: str, diff_text: str, max_length: int) -> list[str]:
    if not diff_text:
        return []
    body_limit = max(500, max_length - 64)
    lines = diff_text.splitlines()

    chunks: list[str] = []
    current: list[str] = []
    current_len = 0

    for line in lines:
        candidate_len = current_len + len(line) + 1
        if current and candidate_len > body_limit:
            chunks.append("\n".join(current))
            current = [line]
            current_len = len(line) + 1
        else:
            current.append(line)
            current_len = candidate_len

    if current:
        chunks.append("\n".join(current))

    total = len(chunks)
    out: list[str] = []
    for index, chunk in enumerate(chunks, start=1):
        header = f"{file_path} ({index}/{total})"
        out.append(f"{header}\n```diff\n{chunk}\n```")
    return out
