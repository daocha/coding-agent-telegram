from __future__ import annotations

import difflib
import os
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass
class FileDiff:
    path: str
    diff: str


@dataclass
class CodeChunk:
    header: str
    code: str
    language: Optional[str]


def _read_snapshot_text(file_path: Path) -> Optional[str]:
    try:
        data = file_path.read_bytes()
    except OSError:
        return None
    if len(data) > 200_000:
        return None
    if b"\x00" in data:
        return None
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError:
        return None


def snapshot_project_files(project_path: Path) -> dict[str, Optional[str]]:
    snapshots: dict[str, Optional[str]] = {}
    for root, dirs, files in os.walk(project_path):
        dirs[:] = [name for name in dirs if name != ".git"]
        root_path = Path(root)
        for file_name in files:
            file_path = root_path / file_name
            rel_path = file_path.relative_to(project_path).as_posix()
            snapshots[rel_path] = _read_snapshot_text(file_path)
    return snapshots


def changed_files_from_snapshots(before: dict[str, Optional[str]], after: dict[str, Optional[str]]) -> set[str]:
    files = set(before) | set(after)
    return {path for path in files if before.get(path) != after.get(path)}


def collect_snapshot_diffs(
    before: dict[str, Optional[str]],
    after: dict[str, Optional[str]],
    files: list[str],
) -> list[FileDiff]:
    results: list[FileDiff] = []
    for path in files:
        before_text = before.get(path)
        after_text = after.get(path)
        if before_text == after_text:
            continue

        if before_text is None and after_text is None:
            results.append(FileDiff(path=path, diff="Binary or large file changed; textual diff unavailable."))
            continue

        before_lines = [] if before_text is None else before_text.splitlines()
        after_lines = [] if after_text is None else after_text.splitlines()
        fromfile = "/dev/null" if before_text is None else f"a/{path}"
        tofile = "/dev/null" if after_text is None else f"b/{path}"
        diff = "\n".join(
            difflib.unified_diff(
                before_lines,
                after_lines,
                fromfile=fromfile,
                tofile=tofile,
                lineterm="",
            )
        )
        if not diff:
            diff = "Binary or large file changed; textual diff unavailable."
        results.append(FileDiff(path=path, diff=diff))
    return results


def _git(project_path: Path, args: list[str]) -> str:
    proc = subprocess.run(["git", "-C", str(project_path), *args], capture_output=True, text=True, check=False)
    return proc.stdout


def _parse_status_paths(output: str) -> list[str]:
    paths: list[str] = []
    for line in output.splitlines():
        if len(line) < 4:
            continue
        path = line[3:].strip()
        if " -> " in path:
            path = path.split(" -> ", 1)[1].strip()
        if path:
            paths.append(path)
    return paths


def changed_files(project_path: Path) -> list[str]:
    output = _git(project_path, ["status", "--short", "--untracked-files=all"])
    return _parse_status_paths(output)


def _collect_diff_for_file(project_path: Path, path: str) -> str:
    return _git(project_path, ["diff", "--", path]).strip()


def collect_diffs(project_path: Path, files: list[str]) -> list[FileDiff]:
    results: list[FileDiff] = []
    for path in files:
        diff = _collect_diff_for_file(project_path, path)
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


def _simplify_diff_text(diff_text: str) -> str:
    skip_prefixes = (
        "diff --git ",
        "index ",
        "new file mode ",
        "deleted file mode ",
        "similarity index ",
        "rename from ",
        "rename to ",
    )
    lines = [line for line in diff_text.splitlines() if not line.startswith(skip_prefixes)]
    return "\n".join(lines).strip()


def _diff_stats(diff_text: str) -> tuple[int, int]:
    additions = 0
    deletions = 0
    for line in diff_text.splitlines():
        if line.startswith("+++ ") or line.startswith("--- "):
            continue
        if line.startswith("+"):
            additions += 1
        elif line.startswith("-"):
            deletions += 1
    return additions, deletions


def _language_for_path(file_path: str) -> str:
    lowered = file_path.lower()
    mapping = {
        ".py": "python",
        ".js": "javascript",
        ".jsx": "javascript",
        ".ts": "typescript",
        ".tsx": "typescript",
        ".java": "java",
        ".kt": "kotlin",
        ".go": "go",
        ".rs": "rust",
        ".rb": "ruby",
        ".php": "php",
        ".sh": "bash",
        ".bash": "bash",
        ".zsh": "bash",
        ".yml": "yaml",
        ".yaml": "yaml",
        ".json": "json",
        ".toml": "toml",
        ".md": "markdown",
        ".css": "css",
        ".html": "html",
        ".xml": "xml",
        ".sql": "sql",
        ".swift": "swift",
        ".c": "c",
        ".h": "c",
        ".cpp": "cpp",
        ".cc": "cpp",
        ".cxx": "cpp",
        ".hpp": "cpp",
    }
    for suffix, language in mapping.items():
        if lowered.endswith(suffix):
            return language
    return ""


def _is_new_file_diff(diff_text: str) -> bool:
    return "--- /dev/null" in diff_text and "+++ /dev/null" not in diff_text


def _extract_new_file_content(diff_text: str) -> str:
    lines: list[str] = []
    for line in diff_text.splitlines():
        if line.startswith("+++ ") or line.startswith("--- ") or line.startswith("@@"):
            continue
        if line.startswith("+"):
            lines.append(line[1:])
    return "\n".join(lines).strip("\n")


def _chunk_code_block(file_path: str, code_text: str, max_length: int) -> list[CodeChunk]:
    language = _language_for_path(file_path)
    body_limit = max(400, max_length - 128)
    lines = code_text.splitlines()

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
    out: list[CodeChunk] = []
    for index, chunk in enumerate(chunks, start=1):
        header = f"{file_path} (new file) ({index}/{total})"
        out.append(CodeChunk(header=header, code=chunk, language=language or None))
    return out


def chunk_fenced_diff(file_path: str, diff_text: str, max_length: int) -> list[CodeChunk]:
    if _is_new_file_diff(diff_text):
        return _chunk_code_block(file_path, _extract_new_file_content(diff_text), max_length)

    simplified = _simplify_diff_text(diff_text)
    if not simplified:
        return []
    body_limit = max(400, max_length - 128)
    lines = simplified.splitlines()

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
    out: list[CodeChunk] = []
    additions, deletions = _diff_stats(simplified)
    for index, chunk in enumerate(chunks, start=1):
        header = f"{file_path} (+{additions} -{deletions}) ({index}/{total})"
        out.append(CodeChunk(header=header, code=chunk, language=None))
    return out


def chunk_plain_text(title: str, text: str, max_length: int) -> list[str]:
    normalized = text.strip()
    if not normalized:
        return []

    body_limit = max(500, max_length - len(title) - 16)
    lines = normalized.splitlines() or [normalized]

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
    return [f"{title} ({index}/{total})\n{chunk}" for index, chunk in enumerate(chunks, start=1)]
