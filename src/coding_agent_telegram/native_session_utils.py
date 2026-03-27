from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path


def iso_from_unix(timestamp: int | float | None) -> str:
    if not timestamp:
        return ""
    return datetime.fromtimestamp(timestamp, tz=timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def normalize_init_text(text: str, *, fallback: str) -> str:
    normalized = " ".join((text or "").strip().split())
    if not normalized:
        return fallback
    if len(normalized) > 120:
        return normalized[:117].rstrip() + "..."
    return normalized


def path_matches_project(candidate: str, project_path: Path) -> bool:
    if not candidate:
        return False
    try:
        candidate_path = Path(candidate).expanduser().resolve()
        project_root = project_path.resolve()
    except OSError:
        return False
    return candidate_path == project_root or project_root in candidate_path.parents


def first_copilot_user_message(events_path: Path) -> str:
    if not events_path.exists():
        return ""
    try:
        with events_path.open(encoding="utf-8") as handle:
            for line in handle:
                try:
                    payload = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if payload.get("type") != "user.message":
                    continue
                data = payload.get("data") or {}
                content = str(data.get("content") or "").strip()
                if content:
                    return content
    except OSError:
        return ""
    return ""


def read_simple_yaml_map(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return values
    for line in lines:
        if not line or line.lstrip().startswith("#") or ":" not in line:
            continue
        key, value = line.split(":", 1)
        values[key.strip()] = value.strip()
    return values
