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
