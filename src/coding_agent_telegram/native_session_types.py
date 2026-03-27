from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class NativeSessionRecord:
    session_id: str
    name: str
    project_folder: str
    provider: str
    branch_name: str
    created_at: str
    updated_at: str
    source_label: str
    initialized_from: str
