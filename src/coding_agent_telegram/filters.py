from __future__ import annotations

import fnmatch
import importlib.resources
import re
from functools import lru_cache
from pathlib import Path

PROJECT_FOLDER_RE = re.compile(r"^[A-Za-z0-9._-]+$")


@lru_cache(maxsize=1)
def _sensitive_patterns() -> tuple[str, ...]:
    resource = importlib.resources.files("coding_agent_telegram").joinpath("resources/sensitive_path_globs.txt")
    return tuple(
        line.strip()
        for line in resource.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    )


def is_valid_project_folder(folder: str) -> bool:
    if folder in {".", ".."}:
        return False
    if not PROJECT_FOLDER_RE.fullmatch(folder):
        return False
    if "/" in folder or "\\" in folder:
        return False
    return True


def resolve_project_path(workspace_root: Path, project_folder: str) -> Path:
    return (workspace_root / project_folder).resolve()


def is_sensitive_path(path: str) -> bool:
    normalized = path.replace("\\", "/")
    name = normalized.split("/")[-1]
    for pattern in _sensitive_patterns():
        if fnmatch.fnmatch(normalized, pattern) or fnmatch.fnmatch(name, pattern):
            return True
    return False
