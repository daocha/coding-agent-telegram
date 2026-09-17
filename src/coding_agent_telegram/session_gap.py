from __future__ import annotations

"""Best-effort "how long has this native session been idle, and how big is it" detection.

Used to warn a user before resuming a session that has been idle long enough for the
provider's prompt cache to have expired, since resuming past that point forces the
whole accumulated conversation to be reprocessed instead of read from cache (see the
"does this app burn more tokens" FAQ in README.md).

Deliberately uses filesystem/db modification time and, where cheaply available, a
provider-reported token count as proxies rather than parsing the full transcript on
every incoming message:

- Claude: no official idle-based cache-expiry document exists, but real session
  transcripts show the extended prompt-cache checkpoint holding for about an hour and
  a full-context reprocess happening reliably past that (see README FAQ).
- Codex: OpenAI doesn't document an idle-based cache-expiry number either; there is an
  open feature request against the Codex CLI for auto-compacting idle sessions before
  the prompt cache expires, for the same reason. Codex's local session database does
  track a cumulative `tokens_used` counter per thread, which is used here as a proxy
  for "how expensive would reprocessing this session be" so small/cheap sessions don't
  trigger a warning just because they sat idle.
- Copilot: GitHub's own docs state Copilot CLI has no inactivity timeout, and Copilot
  manages context itself (auto-compacting around ~80% of the context window, waiting
  for compaction to finish around ~95%). There's no idle-based cache-expiry concern to
  warn about, so this module intentionally has no Copilot size signal, and the
  provider's idle-warning threshold defaults to disabled (see config.py) — Copilot's
  own native compaction is the mechanism to trust here, not an invented one.
"""

import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, NamedTuple, Optional

from coding_agent_telegram.native_claude_sessions import claude_projects_root
from coding_agent_telegram.native_codex_sessions import query_codex_state_db
from coding_agent_telegram.native_copilot_sessions import copilot_session_roots

# How far from the end of a Claude transcript to read looking for the most recent
# assistant usage entry. Bounded so a multi-megabyte transcript still costs one cheap
# tail read rather than a full parse.
_CLAUDE_TAIL_READ_BYTES = 65536


class SessionActivity(NamedTuple):
    last_activity: Optional[datetime]
    size_tokens: Optional[int]  # best-effort proxy for accumulated context size; None if unknown


def _mtime_utc(path: Path) -> Optional[datetime]:
    try:
        return datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)
    except OSError:
        return None


def _tail_bytes(path: Path, max_bytes: int) -> bytes:
    try:
        size = path.stat().st_size
        with path.open("rb") as handle:
            if size > max_bytes:
                handle.seek(size - max_bytes)
            return handle.read()
    except OSError:
        return b""


def _claude_last_assistant_usage_tokens(path: Path) -> Optional[int]:
    text = _tail_bytes(path, _CLAUDE_TAIL_READ_BYTES).decode("utf-8", errors="ignore")
    for line in reversed(text.splitlines()):
        line = line.strip()
        if not line:
            continue
        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            continue
        if entry.get("type") != "assistant":
            continue
        message = entry.get("message") or {}
        usage = message.get("usage")
        if not isinstance(usage, dict):
            continue
        total = 0
        for key in ("input_tokens", "cache_creation_input_tokens", "cache_read_input_tokens"):
            value = usage.get(key)
            if isinstance(value, (int, float)):
                total += int(value)
        if total == 0:
            # Claude Code fabricates client-side "assistant" entries for cases where it
            # never called the API at all -- hitting the rate limit, being logged out,
            # or skipping a priming/continuation nudge that needed no reply (tagged with
            # a "<synthetic>" model marker). Every one of those reports zero usage, and a
            # genuine API turn never does (even a minimal one bills a couple of baseline
            # input tokens), so treat an all-zero usage block as a stub regardless of the
            # model marker's exact spelling -- which keeps this working even if Claude
            # Code renames that marker -- and keep scanning for the last turn that
            # actually hit the API.
            continue
        return total
    return None


def _claude_activity(session_id: str) -> SessionActivity:
    projects_root = claude_projects_root()
    if not projects_root.exists():
        return SessionActivity(None, None)
    # Session IDs are UUIDs, unique across every project directory, so a glob by
    # filename alone finds the right transcript without needing to reimplement
    # Claude Code's project-path-to-folder-name encoding.
    try:
        matches = sorted(projects_root.glob(f"*/{session_id}.jsonl"))
    except OSError:
        return SessionActivity(None, None)
    if not matches:
        return SessionActivity(None, None)
    path = matches[0]
    return SessionActivity(_mtime_utc(path), _claude_last_assistant_usage_tokens(path))


def _codex_activity(session_id: str) -> SessionActivity:
    rows = query_codex_state_db("SELECT updated_at, tokens_used FROM threads WHERE id = ?", (session_id,))
    if not rows or not rows[0][0]:
        return SessionActivity(None, None)
    updated_at, tokens_used = rows[0]
    size_tokens = int(tokens_used) if isinstance(tokens_used, (int, float)) else None
    return SessionActivity(datetime.fromtimestamp(updated_at, tz=timezone.utc), size_tokens)


def _copilot_activity(session_id: str) -> SessionActivity:
    latest: Optional[datetime] = None
    for root in copilot_session_roots(Path.home()):
        session_dir = root / "session-state" / session_id
        for name in ("workspace.yaml", "events.jsonl"):
            candidate = _mtime_utc(session_dir / name)
            if candidate is not None and (latest is None or candidate > latest):
                latest = candidate
    # No local, cheaply-available token/context-size signal for Copilot -- see the
    # module docstring for why that's fine (no idle-based cache-expiry concern there).
    return SessionActivity(latest, None)


# One entry per provider this module knows how to inspect. A provider missing here
# (or not yet added) falls back to "unknown activity" below, rather than needing its
# own if/elif branch kept in sync with this dict.
_ACTIVITY_LOOKUP: dict[str, Callable[[str], SessionActivity]] = {
    "claude": _claude_activity,
    "codex": _codex_activity,
    "copilot": _copilot_activity,
}


def native_session_activity(provider: str, session_id: str) -> SessionActivity:
    """Return (last_activity, size_tokens) for *session_id*'s native transcript."""
    if not session_id:
        return SessionActivity(None, None)
    normalized_provider = (provider or "").strip().lower()
    lookup = _ACTIVITY_LOOKUP.get(normalized_provider)
    if lookup is None:
        return SessionActivity(None, None)
    return lookup(session_id)


def gap_seconds_since(last_activity: Optional[datetime]) -> Optional[float]:
    """Seconds since *last_activity*, or None if it's unknown."""
    if last_activity is None:
        return None
    now = datetime.now(timezone.utc)
    return max(0.0, (now - last_activity).total_seconds())


def humanize_gap_seconds(seconds: float) -> str:
    """Render a gap as a short human string, e.g. "12h 30m" or "45m"."""
    total_minutes = int(seconds // 60)
    days, remainder_minutes = divmod(total_minutes, 24 * 60)
    hours, minutes = divmod(remainder_minutes, 60)
    parts: list[str] = []
    if days:
        parts.append(f"{days}d")
    if hours:
        parts.append(f"{hours}h")
    if minutes or not parts:
        parts.append(f"{minutes}m")
    return " ".join(parts[:2])


# Largest-to-smallest so the first divisor a count actually reaches wins.
_TOKEN_COUNT_UNITS: tuple[tuple[int, str], ...] = (
    (1_000_000_000, "B"),
    (1_000_000, "M"),
    (1_000, "k"),
)


def humanize_token_count(tokens: int) -> str:
    """Render a token count as a short human string, e.g. "800", "1k", "200k", "1M",
    "11M". Rounds down to one decimal place rather than to nearest, so a count just
    under a unit's boundary (e.g. 999,999) reads as "999.9k" rather than rolling over
    to a misleading "1000k"."""
    if tokens < 1000:
        return str(tokens)
    for divisor, suffix in _TOKEN_COUNT_UNITS:
        if tokens < divisor:
            continue
        value = math.floor((tokens / divisor) * 10) / 10
        return f"{value:g}{suffix}"
    return str(tokens)
