from __future__ import annotations

"""Best-effort quota lookups for each coding-agent provider.

None of Claude Code, Codex, or Copilot expose 5-hour/weekly rate-limit
percentages through a documented non-interactive flag -- those numbers only
render inside each CLI's own interactive TUI (Claude's ``/usage``, Codex's
``/status``, Copilot's ``/usage``).

- Claude: every real ``-p`` turn's ``stream-json`` output includes a
  ``rate_limit_event`` with a ``unifiedWindows`` object carrying
  ``five_hour``/``seven_day`` utilization -- present only for Pro/Max
  subscribers authenticated via OAuth (API-key billing has no such windows).
  Since it rides along on any Claude call the bot was already going to make,
  ``observe_claude_rate_limit_event`` opportunistically caches it from every
  such call (see ``agent_runner._run``), and ``get_claude_usage`` reads
  *only* that cache -- there is no live fallback probe. A window that has
  never been observed, or whose cached value has rolled past its own
  ``resets_at``, reports N/A rather than paying for a dedicated API call just
  to answer a status check; it starts reporting again the next time any real
  Claude call happens to observe it. The two windows are tracked and expired
  independently, since a bot idle for a few hours can easily have a stale
  five-hour window sitting next to a still-fresh weekly one.
- Codex: its ``app-server`` JSON-RPC daemon exposes ``account/rateLimits/read``,
  returning ``primary`` (5h) / ``secondary`` (weekly) ``usedPercent`` from a
  pure local query -- no model call, no cost, so it's always fetched live.

Copilot has no equivalent, and not just because the API is missing: since
GitHub retired premium requests for a monthly AI-credit balance (June 2026),
Copilot no longer has a 5-hour/weekly rolling window at all -- credits burn
against a monthly cycle, viewable only on GitHub's billing page, with no CLI
or API exposing an individual account's remaining balance. ``fetch_copilot_usage``
always reports unavailable rather than inventing a window that doesn't exist.
"""

import json
import logging
import subprocess
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import portalocker

logger = logging.getLogger(__name__)

CODEX_APP_SERVER_TIMEOUT_SECONDS = 15.0

# Shown in place of a window's percentage when this cache has nothing usable
# for it. Two distinct reasons, so the message matches reality: a window we
# have simply never seen reads differently from one we saw and watched expire.
CLAUDE_WINDOW_NEVER_OBSERVED_NOTE = "no data yet -- will show after your next Claude turn"
CLAUDE_WINDOW_EXPIRED_NOTE = "past its reset time -- will update after your next Claude turn"


@dataclass(frozen=True)
class RateWindow:
    used_percent: float
    resets_at: Optional[int] = None  # unix epoch seconds


@dataclass(frozen=True)
class ProviderUsage:
    provider: str
    available: bool
    five_hour: Optional[RateWindow] = None
    weekly: Optional[RateWindow] = None
    plan: Optional[str] = None
    error: Optional[str] = None
    # Set only when a window came from the passive cache -- lets callers show
    # "as of X ago". None (never cached) reads the same as a live value here.
    observed_at: Optional[float] = None
    # Populated per-window only for Claude, only when that window is None,
    # explaining why (see CLAUDE_WINDOW_*_NOTE above) instead of a bare
    # "unknown" -- Codex/Copilot don't need this, they're never partially
    # available.
    five_hour_note: Optional[str] = None
    weekly_note: Optional[str] = None


@dataclass(frozen=True)
class _ClaudeRateLimitSnapshot:
    five_hour: Optional[RateWindow]
    weekly: Optional[RateWindow]
    observed_at: float


# Process-wide: the underlying `claude` CLI's OAuth login is per-machine, not
# per Telegram bot/chat, so one cache shared across every bot instance on this
# host matches the actual scope of what it's caching. Optionally backed by its
# own small file on disk (see configure_persistence) so a bot restart doesn't
# throw away a window that's still live -- without that, /status would
# misreport "no data yet" for whatever's left of the window after every
# restart, not just report genuinely fresh state.
#
# Deliberately its own file rather than a key in the main session state.json:
# this snapshot refreshes on every real Claude turn (not just rare
# session-lifecycle events like /new or /switch), and it's disposable --
# worst case a lost write just means one more "no data yet" until the next
# Claude turn observes it again. Writing it into state.json would mean
# re-copying the entire session/backup blob on every single turn just to
# protect a few bytes of best-effort telemetry, and would serialize these
# frequent writes against unrelated, rarer session-lifecycle writes sharing
# that file's lock.
_claude_rate_limit_cache: Optional[_ClaudeRateLimitSnapshot] = None
_claude_rate_limit_lock = threading.Lock()
_claude_rate_limit_path: Optional[Path] = None
_RATE_LIMIT_LOCK_TIMEOUT_SECONDS = 5


def _rate_window_to_dict(window: Optional[RateWindow]) -> Optional[dict]:
    if window is None:
        return None
    return {"used_percent": window.used_percent, "resets_at": window.resets_at}


def _rate_window_from_dict(data: object) -> Optional[RateWindow]:
    if not isinstance(data, dict):
        return None
    used_percent = data.get("used_percent")
    if not isinstance(used_percent, (int, float)):
        return None
    resets_at = data.get("resets_at")
    return RateWindow(
        used_percent=float(used_percent),
        resets_at=resets_at if isinstance(resets_at, int) else None,
    )


def _snapshot_to_dict(snapshot: _ClaudeRateLimitSnapshot) -> dict:
    return {
        "five_hour": _rate_window_to_dict(snapshot.five_hour),
        "weekly": _rate_window_to_dict(snapshot.weekly),
        "observed_at": snapshot.observed_at,
    }


def _snapshot_from_dict(data: dict) -> Optional[_ClaudeRateLimitSnapshot]:
    observed_at = data.get("observed_at")
    if not isinstance(observed_at, (int, float)):
        return None
    return _ClaudeRateLimitSnapshot(
        five_hour=_rate_window_from_dict(data.get("five_hour")),
        weekly=_rate_window_from_dict(data.get("weekly")),
        observed_at=float(observed_at),
    )


def _read_locked_json_file(path: Path) -> Optional[dict]:
    """Return the parsed JSON object at *path*, or None if it doesn't exist,
    is empty, or isn't a JSON object. Locked against other processes writing
    the same file (see the module-level comment on why this isn't state.json)."""
    lock_file = path.with_suffix(path.suffix + ".lock")
    path.parent.mkdir(parents=True, exist_ok=True)
    with portalocker.Lock(str(lock_file), timeout=_RATE_LIMIT_LOCK_TIMEOUT_SECONDS):
        if not path.exists():
            return None
        raw = path.read_text(encoding="utf-8").strip()
    if not raw:
        return None
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return None
    return data if isinstance(data, dict) else None


def _write_locked_json_file(path: Path, data: dict) -> None:
    """Atomically (temp file + rename) and lock-safely overwrite *path* with
    *data*. No backup copy -- unlike state.json, this file's contents are
    disposable/self-healing, so there's nothing worth preserving a prior
    version of."""
    lock_file = path.with_suffix(path.suffix + ".lock")
    temp_file = path.with_suffix(path.suffix + ".tmp")
    path.parent.mkdir(parents=True, exist_ok=True)
    serialized = json.dumps(data, indent=2, ensure_ascii=False)
    with portalocker.Lock(str(lock_file), timeout=_RATE_LIMIT_LOCK_TIMEOUT_SECONDS):
        temp_file.write_text(serialized + "\n", encoding="utf-8")
        temp_file.replace(path)


def configure_persistence(path: Path) -> None:
    """Back the passive rate-limit cache with a dedicated JSON file at *path*
    and seed the cache from it if present.

    Called once at startup. Loading here (rather than lazily on first read)
    means the very first ``/status`` after a restart can already show the
    last-observed window instead of "no data yet", as long as that window
    hasn't rolled past its own reset time -- get_claude_usage's existing
    expiry check handles that either way.
    """
    global _claude_rate_limit_path, _claude_rate_limit_cache
    _claude_rate_limit_path = path
    try:
        data = _read_locked_json_file(path)
    except (OSError, portalocker.LockException):
        logger.warning("Could not load persisted Claude rate-limit snapshot; starting empty.", exc_info=True)
        return
    if data is None:
        return
    snapshot = _snapshot_from_dict(data)
    if snapshot is None:
        return
    with _claude_rate_limit_lock:
        _claude_rate_limit_cache = snapshot


def _claude_rate_window(window: Optional[dict]) -> Optional[RateWindow]:
    if not isinstance(window, dict):
        return None
    utilization = window.get("utilization")
    if not isinstance(utilization, (int, float)):
        return None
    resets_at = window.get("resetsAt")
    return RateWindow(
        used_percent=round(float(utilization) * 100, 1),
        resets_at=resets_at if isinstance(resets_at, int) else None,
    )


def parse_claude_rate_limit_event(raw_events: list) -> Optional[ProviderUsage]:
    """Extract usage windows from a claude ``-p`` run's parsed jsonl events.

    Uses the *last* ``rate_limit_event``, not the first: a single ``-p``
    invocation can make more than one real API turn internally (e.g. a
    tool-use loop), each capable of emitting its own event as utilization
    climbs, and only the final one reflects the run's actual ending usage.
    """
    usage: Optional[ProviderUsage] = None
    for event in raw_events:
        if not isinstance(event, dict) or event.get("type") != "rate_limit_event":
            continue
        windows = (event.get("rate_limit_info") or {}).get("unifiedWindows") or {}
        usage = ProviderUsage(
            provider="claude",
            available=True,
            five_hour=_claude_rate_window(windows.get("five_hour")),
            weekly=_claude_rate_window(windows.get("seven_day")),
        )
    return usage


def _store_claude_snapshot(usage: ProviderUsage) -> None:
    global _claude_rate_limit_cache
    snapshot = _ClaudeRateLimitSnapshot(
        five_hour=usage.five_hour,
        weekly=usage.weekly,
        observed_at=time.time(),
    )
    with _claude_rate_limit_lock:
        _claude_rate_limit_cache = snapshot
        path = _claude_rate_limit_path
    if path is not None:
        # Best-effort: a failed disk write must not lose the in-memory update
        # above, which is what every real Claude call up to this point relied
        # on already existing.
        try:
            _write_locked_json_file(path, _snapshot_to_dict(snapshot))
        except (OSError, portalocker.LockException):
            logger.warning("Could not persist Claude rate-limit snapshot to disk.", exc_info=True)


def observe_claude_rate_limit_event(raw_events: list) -> None:
    """Best-effort cache update from any real claude call's raw events.

    Called after every claude subprocess run (see ``agent_runner._run``)
    regardless of which command triggered it, so ``get_claude_usage`` can
    usually answer ``/status`` from a real, recent observation instead of
    paying for a dedicated probe on every check.
    """
    usage = parse_claude_rate_limit_event(raw_events)
    if usage is not None:
        _store_claude_snapshot(usage)


def _resolve_window(window: Optional[RateWindow], now: float) -> tuple[Optional[RateWindow], Optional[str]]:
    """Return the window if it's still trustworthy, else ``(None, reason)``.

    A cached window is trustworthy only until its own reported reset time --
    past that point the real window has already rolled over to a fresh count
    this cache never observed, so continuing to show the old percentage would
    be actively wrong, not just stale.
    """
    if window is None:
        return None, CLAUDE_WINDOW_NEVER_OBSERVED_NOTE
    if window.resets_at is not None and now >= window.resets_at:
        return None, CLAUDE_WINDOW_EXPIRED_NOTE
    return window, None


def get_claude_usage() -> ProviderUsage:
    """Read Claude's usage from the passive cache only -- no live fallback.

    The five-hour and weekly windows are resolved independently: an idle bot
    can easily have one window sitting well past its reset while the other is
    still fresh, and treating them as a pair would throw away the still-good
    one just because its sibling expired.
    """
    now = time.time()
    with _claude_rate_limit_lock:
        snapshot = _claude_rate_limit_cache

    five_hour, five_hour_note = _resolve_window(snapshot.five_hour if snapshot else None, now)
    weekly, weekly_note = _resolve_window(snapshot.weekly if snapshot else None, now)

    return ProviderUsage(
        provider="claude",
        available=True,
        five_hour=five_hour,
        five_hour_note=five_hour_note,
        weekly=weekly,
        weekly_note=weekly_note,
        observed_at=snapshot.observed_at if snapshot is not None else None,
    )


def _codex_percent_window(window: Optional[dict]) -> Optional[RateWindow]:
    if not isinstance(window, dict):
        return None
    used_percent = window.get("usedPercent")
    if not isinstance(used_percent, (int, float)):
        return None
    resets_at = window.get("resetsAt")
    return RateWindow(
        used_percent=round(float(used_percent), 1),
        resets_at=resets_at if isinstance(resets_at, int) else None,
    )


def parse_codex_rate_limits_result(result: dict) -> ProviderUsage:
    rate_limits = result.get("rateLimits") or {}
    return ProviderUsage(
        provider="codex",
        available=True,
        five_hour=_codex_percent_window(rate_limits.get("primary")),
        weekly=_codex_percent_window(rate_limits.get("secondary")),
        plan=rate_limits.get("planType") if isinstance(rate_limits.get("planType"), str) else None,
    )


def _send_json_rpc(proc: subprocess.Popen, message: dict) -> None:
    proc.stdin.write(json.dumps(message) + "\n")
    proc.stdin.flush()


def fetch_codex_usage(codex_bin: str) -> ProviderUsage:
    """Query Codex's local app-server daemon over JSON-RPC for rate limits.

    Spawns a fresh, short-lived ``codex app-server`` process rather than
    reusing a persistent daemon -- this is an on-demand status check, not
    something worth keeping a background process alive for.
    """
    try:
        proc = subprocess.Popen(
            [codex_bin, "app-server"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
        )
    except OSError as exc:
        return ProviderUsage(provider="codex", available=False, error=str(exc))

    outcome: dict = {}
    done = threading.Event()

    def read_stdout() -> None:
        try:
            for line in proc.stdout:
                stripped = line.strip()
                if not stripped:
                    continue
                try:
                    message = json.loads(stripped)
                except json.JSONDecodeError:
                    continue
                if message.get("id") != 2:
                    continue
                if "result" in message:
                    outcome["result"] = message["result"]
                elif "error" in message:
                    outcome["error"] = message["error"]
                done.set()
                return
        except (OSError, ValueError):
            done.set()

    reader = threading.Thread(target=read_stdout, daemon=True)
    reader.start()

    try:
        _send_json_rpc(
            proc,
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {"clientInfo": {"name": "coding-agent-telegram", "version": "1.0.0"}},
            },
        )
        _send_json_rpc(proc, {"jsonrpc": "2.0", "method": "initialized", "params": {}})
        _send_json_rpc(proc, {"jsonrpc": "2.0", "id": 2, "method": "account/rateLimits/read", "params": {}})
        done.wait(timeout=CODEX_APP_SERVER_TIMEOUT_SECONDS)
    except (BrokenPipeError, OSError) as exc:
        outcome.setdefault("error", str(exc))
    finally:
        try:
            proc.terminate()
            proc.wait(timeout=3)
        except Exception:
            proc.kill()

    if "result" in outcome:
        return parse_codex_rate_limits_result(outcome["result"])

    error = outcome.get("error")
    if isinstance(error, dict):
        error_text = error.get("message") or str(error)
    elif error:
        error_text = str(error)
    else:
        try:
            error_text = (proc.stderr.read() or "").strip()
        except Exception:
            error_text = ""
    return ProviderUsage(provider="codex", available=False, error=error_text or "No response from codex app-server.")


def fetch_copilot_usage() -> ProviderUsage:
    return ProviderUsage(
        provider="copilot",
        available=False,
        error=(
            "Copilot bills against a monthly AI-credit balance, not a 5-hour/weekly window, and there's "
            "no CLI or API to read an individual account's remaining credits (only the GitHub billing page)."
        ),
    )
