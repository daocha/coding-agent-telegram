from coding_agent_telegram.diff_utils import FileDiff, TEXTUAL_DIFF_UNAVAILABLE
from coding_agent_telegram.session_runtime import SessionRuntime


def _runtime() -> SessionRuntime:
    return SessionRuntime(
        cfg=None,
        store=None,
        agent_runner=None,
        bot_id="bot-a",
        git=None,
        run_with_typing=None,
    )


def test_merge_snapshot_diffs_prefers_snapshot_delta_over_git_diff():
    runtime = _runtime()
    git_diffs = [FileDiff(path="src/app.py", diff="diff-from-git-head")]
    snapshot_diffs = {
        "src/app.py": FileDiff(path="src/app.py", diff="diff-from-current-run"),
    }

    merged = runtime._merge_snapshot_diffs(git_diffs, snapshot_diffs)

    assert merged[0].diff == "diff-from-current-run"


def test_merge_snapshot_diffs_falls_back_to_git_diff_when_snapshot_unavailable():
    runtime = _runtime()
    git_diffs = [FileDiff(path="src/app.py", diff="diff-from-git-head")]
    snapshot_diffs = {
        "src/app.py": FileDiff(path="src/app.py", diff=TEXTUAL_DIFF_UNAVAILABLE),
    }

    merged = runtime._merge_snapshot_diffs(git_diffs, snapshot_diffs)

    assert merged[0].diff == "diff-from-git-head"


# ---------------------------------------------------------------------------
# _chunk_assistant_prose — splitting large prose
# ---------------------------------------------------------------------------


def test_chunk_assistant_prose_returns_empty_for_blank_text():
    runtime = _runtime()
    runtime.cfg = type("Cfg", (), {"max_telegram_message_length": 3000})()
    result = runtime._chunk_assistant_prose("Output", "   ")
    assert result == []


def test_chunk_assistant_prose_returns_single_chunk_for_short_text():
    runtime = _runtime()
    runtime.cfg = type("Cfg", (), {"max_telegram_message_length": 3000})()
    chunks = runtime._chunk_assistant_prose("Output", "Short message.")
    assert len(chunks) == 1
    assert "Short message." in chunks[0]


def test_chunk_assistant_prose_splits_text_that_exceeds_max_length():
    runtime = _runtime()
    runtime.cfg = type("Cfg", (), {"max_telegram_message_length": 100})()
    long_text = "word " * 50  # 250 chars — way over 100 including the title
    chunks = runtime._chunk_assistant_prose("Out", long_text)
    assert len(chunks) > 1
    for chunk in chunks:
        assert len(chunk) <= 100 + 50  # allow a little slack for HTML tags


# ---------------------------------------------------------------------------
# _split_assistant_body
# ---------------------------------------------------------------------------


def test_split_assistant_body_splits_multiline_at_midpoint():
    runtime = _runtime()
    runtime.cfg = None
    lines = ["line1", "line2", "line3", "line4"]
    body = "\n".join(lines)
    left, right = runtime._split_assistant_body(body)
    assert left
    assert right
    assert "line1" in left
    assert "line3" in right or "line4" in right


def test_split_assistant_body_handles_single_long_line():
    runtime = _runtime()
    runtime.cfg = None
    body = "a" * 200
    left, right = runtime._split_assistant_body(body)
    assert left
    assert right


# ---------------------------------------------------------------------------
# _merge_snapshot_diffs — edge cases
# ---------------------------------------------------------------------------


def test_merge_snapshot_diffs_uses_git_diff_when_no_snapshot_for_path():
    runtime = _runtime()
    git_diffs = [FileDiff(path="new_file.py", diff="diff-only-in-git")]
    snapshot_diffs: dict = {}

    merged = runtime._merge_snapshot_diffs(git_diffs, snapshot_diffs)

    assert len(merged) == 1
    assert merged[0].diff == "diff-only-in-git"


def test_merge_snapshot_diffs_handles_empty_inputs():
    runtime = _runtime()
    merged = runtime._merge_snapshot_diffs([], {})
    assert merged == []
