from __future__ import annotations

import fnmatch
import re
from pathlib import Path

PROJECT_FOLDER_RE = re.compile(r"^[A-Za-z0-9._-]+$")

SENSITIVE_PATTERNS = [
    ".env",
    ".env.*",
    "*.pem",
    "*.key",
    "id_rsa",
    "id_ed25519",
    "secrets.*",
    "credentials.*",
    ".ssh/*",
    ".aws/*",
]


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
    for pattern in SENSITIVE_PATTERNS:
        if fnmatch.fnmatch(normalized, pattern) or fnmatch.fnmatch(name, pattern):
            return True
    return False
