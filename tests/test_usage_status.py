from __future__ import annotations

import time
from pathlib import Path

import pytest

from coding_agent_telegram.session_store import SessionStore
from coding_agent_telegram.usage_status import (
    CLAUDE_WINDOW_EXPIRED_NOTE,
    CLAUDE_WINDOW_NEVER_OBSERVED_NOTE,
    ProviderUsage,
    configure_persistence,
    fetch_copilot_usage,
    get_claude_usage,
    observe_claude_rate_limit_event,
    parse_claude_rate_limit_event,
    parse_codex_rate_limits_result,
)


@pytest.fixture(autouse=True)
def _reset_claude_rate_limit_cache(monkeypatch):
    """The passive cache and its optional persistence backing are process-wide
    module state; isolate each test from whatever an earlier test left behind."""
    monkeypatch.setattr("coding_agent_telegram.usage_status._claude_rate_limit_cache", None)
    monkeypatch.setattr("coding_agent_telegram.usage_status._claude_rate_limit_store", None)
    yield


def test_parse_claude_rate_limit_event_extracts_both_windows():
    events = [
        {"type": "system", "subtype": "init"},
        {
            "type": "rate_limit_event",
            "rate_limit_info": {
                "unifiedWindows": {
                    "five_hour": {"utilization": 0.53, "resetsAt": 1788990600},
                    "seven_day": {"utilization": 0.05, "resetsAt": 1789570800},
                }
            },
        },
    ]

    usage = parse_claude_rate_limit_event(events)

    assert usage is not None
    assert usage.provider == "claude"
    assert usage.available is True
    assert usage.five_hour.used_percent == 53.0
    assert usage.five_hour.resets_at == 1788990600
    assert usage.weekly.used_percent == 5.0
    assert usage.weekly.resets_at == 1789570800


def test_parse_claude_rate_limit_event_uses_last_not_first_when_multiple_present():
    """A single -p invocation can make more than one real API turn internally
    (e.g. a tool-use loop), each capable of emitting its own rate_limit_event
    as utilization climbs -- only the last one reflects the run's ending usage."""
    events = [
        {
            "type": "rate_limit_event",
            "rate_limit_info": {
                "unifiedWindows": {
                    "five_hour": {"utilization": 0.10, "resetsAt": 1},
                    "seven_day": {"utilization": 0.01, "resetsAt": 2},
                }
            },
        },
        {"type": "assistant", "message": {}},
        {
            "type": "rate_limit_event",
            "rate_limit_info": {
                "unifiedWindows": {
                    "five_hour": {"utilization": 0.15, "resetsAt": 1},
                    "seven_day": {"utilization": 0.02, "resetsAt": 2},
                }
            },
        },
    ]

    usage = parse_claude_rate_limit_event(events)

    assert usage.five_hour.used_percent == 15.0
    assert usage.weekly.used_percent == 2.0


def test_parse_claude_rate_limit_event_missing_returns_none():
    events = [{"type": "system", "subtype": "init"}, {"type": "result", "result": "hi"}]

    assert parse_claude_rate_limit_event(events) is None


def test_parse_codex_rate_limits_result_extracts_primary_and_secondary():
    result = {
        "rateLimits": {
            "primary": {"usedPercent": 0, "windowDurationMins": 300, "resetsAt": 1789005642},
            "secondary": {"usedPercent": 23, "windowDurationMins": 10080, "resetsAt": 1789446557},
            "planType": "plus",
        }
    }

    usage = parse_codex_rate_limits_result(result)

    assert usage.provider == "codex"
    assert usage.available is True
    assert usage.five_hour.used_percent == 0.0
    assert usage.five_hour.resets_at == 1789005642
    assert usage.weekly.used_percent == 23.0
    assert usage.plan == "plus"


def test_parse_codex_rate_limits_result_handles_missing_windows():
    usage = parse_codex_rate_limits_result({"rateLimits": {}})

    assert usage.available is True
    assert usage.five_hour is None
    assert usage.weekly is None
    assert usage.plan is None


def test_fetch_copilot_usage_always_unavailable():
    usage = fetch_copilot_usage()

    assert isinstance(usage, ProviderUsage)
    assert usage.provider == "copilot"
    assert usage.available is False
    assert usage.error


def _rate_limit_events(*, five_hour_resets_at: float, weekly_resets_at: float) -> list:
    return [
        {
            "type": "rate_limit_event",
            "rate_limit_info": {
                "unifiedWindows": {
                    "five_hour": {"utilization": 0.4, "resetsAt": int(five_hour_resets_at)},
                    "seven_day": {"utilization": 0.1, "resetsAt": int(weekly_resets_at)},
                }
            },
        }
    ]


def test_get_claude_usage_reports_na_for_both_windows_when_never_observed():
    usage = get_claude_usage()

    assert usage.provider == "claude"
    assert usage.available is True
    assert usage.five_hour is None
    assert usage.five_hour_note == CLAUDE_WINDOW_NEVER_OBSERVED_NOTE
    assert usage.weekly is None
    assert usage.weekly_note == CLAUDE_WINDOW_NEVER_OBSERVED_NOTE
    assert usage.observed_at is None


def test_get_claude_usage_serves_both_windows_from_cache_when_fresh():
    now = time.time()
    observe_claude_rate_limit_event(_rate_limit_events(five_hour_resets_at=now + 3600, weekly_resets_at=now + 86400))

    usage = get_claude_usage()

    assert usage.five_hour.used_percent == 40.0
    assert usage.five_hour_note is None
    assert usage.weekly.used_percent == 10.0
    assert usage.weekly_note is None
    assert usage.observed_at is not None


def test_get_claude_usage_reports_na_for_five_hour_window_that_has_reset_but_keeps_fresh_weekly():
    now = time.time()
    # five_hour already rolled past its reset; weekly is still within its window.
    observe_claude_rate_limit_event(_rate_limit_events(five_hour_resets_at=now - 10, weekly_resets_at=now + 86400))

    usage = get_claude_usage()

    assert usage.five_hour is None
    assert usage.five_hour_note == CLAUDE_WINDOW_EXPIRED_NOTE
    # The still-fresh weekly window is not thrown away just because its sibling expired.
    assert usage.weekly.used_percent == 10.0
    assert usage.weekly_note is None
    # A snapshot still exists (just partially expired), so "last observed" stays meaningful.
    assert usage.observed_at is not None


def test_get_claude_usage_reports_na_for_weekly_window_that_has_reset_but_keeps_fresh_five_hour():
    now = time.time()
    observe_claude_rate_limit_event(_rate_limit_events(five_hour_resets_at=now + 3600, weekly_resets_at=now - 10))

    usage = get_claude_usage()

    assert usage.five_hour.used_percent == 40.0
    assert usage.five_hour_note is None
    assert usage.weekly is None
    assert usage.weekly_note == CLAUDE_WINDOW_EXPIRED_NOTE


def test_get_claude_usage_never_makes_a_subprocess_call(monkeypatch):
    """There is no live-probe fallback anymore -- get_claude_usage must be a
    pure, free cache read regardless of cache state."""

    def fail_if_called(*args, **kwargs):
        raise AssertionError("get_claude_usage must not spawn a subprocess")

    monkeypatch.setattr("coding_agent_telegram.usage_status.subprocess.run", fail_if_called)
    monkeypatch.setattr("coding_agent_telegram.usage_status.subprocess.Popen", fail_if_called)

    # No cache at all.
    assert get_claude_usage().five_hour is None

    # Cache present but expired.
    now = time.time()
    observe_claude_rate_limit_event(_rate_limit_events(five_hour_resets_at=now - 10, weekly_resets_at=now - 10))
    usage = get_claude_usage()
    assert usage.five_hour is None
    assert usage.weekly is None


def _make_store(tmp_path: Path) -> SessionStore:
    return SessionStore(tmp_path / "state.json", tmp_path / "state.json.bak")


def test_observed_rate_limit_survives_a_restart_via_persistence(tmp_path: Path):
    """Reproduces the bug report: a real Claude turn observes usage, the bot
    process restarts (wiping the in-memory-only cache), and /status should
    still show the last-observed window instead of "no data yet"."""
    store = _make_store(tmp_path)
    configure_persistence(store)
    now = time.time()
    observe_claude_rate_limit_event(_rate_limit_events(five_hour_resets_at=now + 3600, weekly_resets_at=now + 86400))

    # Simulate a process restart: fresh cache, fresh SessionStore instance
    # pointed at the same state file, re-wired the same way cli.py does.
    from coding_agent_telegram import usage_status as usage_status_module

    usage_status_module._claude_rate_limit_cache = None
    restarted_store = _make_store(tmp_path)
    configure_persistence(restarted_store)

    usage = get_claude_usage()
    assert usage.five_hour.used_percent == 40.0
    assert usage.five_hour_note is None
    assert usage.weekly.used_percent == 10.0
    assert usage.observed_at is not None


def test_configure_persistence_with_no_prior_snapshot_leaves_cache_empty(tmp_path: Path):
    store = _make_store(tmp_path)

    configure_persistence(store)

    usage = get_claude_usage()
    assert usage.five_hour is None
    assert usage.five_hour_note == CLAUDE_WINDOW_NEVER_OBSERVED_NOTE


def test_persisted_rate_limit_snapshot_is_not_nested_under_chats(tmp_path: Path):
    store = _make_store(tmp_path)
    configure_persistence(store)
    now = time.time()

    observe_claude_rate_limit_event(_rate_limit_events(five_hour_resets_at=now + 3600, weekly_resets_at=now + 86400))

    state = store.load()
    assert "claude_rate_limit" in state
    assert state.get("chats", {}) == {}


def test_restart_after_window_rolled_over_reports_expired_not_stale_data(tmp_path: Path):
    """A snapshot persisted just before its reset time should be reported as
    expired after a restart, not served as if it were still live."""
    store = _make_store(tmp_path)
    configure_persistence(store)
    now = time.time()
    observe_claude_rate_limit_event(_rate_limit_events(five_hour_resets_at=now - 1, weekly_resets_at=now + 86400))

    from coding_agent_telegram import usage_status as usage_status_module

    usage_status_module._claude_rate_limit_cache = None
    configure_persistence(_make_store(tmp_path))

    usage = get_claude_usage()
    assert usage.five_hour is None
    assert usage.five_hour_note == CLAUDE_WINDOW_EXPIRED_NOTE
    assert usage.weekly.used_percent == 10.0
