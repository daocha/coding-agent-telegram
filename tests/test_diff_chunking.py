from pathlib import Path

from coding_agent_telegram.diff_utils import (
    _parse_status_paths,
    chunk_fenced_diff,
    chunk_plain_text,
    is_runtime_artifact_path,
    snapshot_project_files,
)


def test_chunk_fenced_diff_limits():
    content = "\n".join([f"+ line {i}" for i in range(1000)])
    chunks = chunk_fenced_diff("src/api.py", content, 3000)
    assert len(chunks) > 1
    for msg in chunks:
        assert msg.language == "diff"
        assert "src/api.py" in msg.header
        assert msg.code


def test_chunk_plain_text_limits():
    content = "\n".join([f"line {i}" for i in range(1000)])
    chunks = chunk_plain_text("Codex output", content, 3000)
    assert len(chunks) > 1
    for msg in chunks:
        assert "Codex output" in msg


def test_parse_status_paths_includes_renames_and_untracked():
    output = " M src/app.py\n?? src/new.py\nR  old.py -> new.py\n"
    assert _parse_status_paths(output) == ["src/app.py", "src/new.py", "new.py"]


def test_new_javascript_file_uses_language_code_block():
    diff = "\n".join(
        [
            "--- /dev/null",
            "+++ b/src/new-file.js",
            "@@ -0,0 +1,2 @@",
            "+const answer = 42;",
            "+console.log(answer);",
        ]
    )
    chunks = chunk_fenced_diff("src/new-file.js", diff, 3000)
    assert len(chunks) == 1
    assert chunks[0].language == "javascript"
    assert "new file" in chunks[0].header
    assert "+const answer" not in chunks[0].code


def test_modified_javascript_file_stays_diff_block():
    diff = "\n".join(
        [
            "--- a/src/app.js",
            "+++ b/src/app.js",
            "@@ -1 +1 @@",
            '-console.log("old");',
            '+console.log("new");',
        ]
    )
    chunks = chunk_fenced_diff("src/app.js", diff, 3000)
    assert len(chunks) == 1
    assert chunks[0].language == "diff"


def test_runtime_artifact_paths_are_ignored():
    assert is_runtime_artifact_path("logs/coding-agent-telegram.log") is True
    assert is_runtime_artifact_path("worker.out") is True
    assert is_runtime_artifact_path("state.json") is False
    assert is_runtime_artifact_path("logs/readme.md") is False
    assert is_runtime_artifact_path("src/app.py") is False


def test_snapshot_project_files_excludes_runtime_artifacts(tmp_path: Path):
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "app.py").write_text("print('ok')\n", encoding="utf-8")
    (tmp_path / "logs").mkdir()
    (tmp_path / "logs" / "coding-agent-telegram.log").write_text("runtime log\n", encoding="utf-8")
    (tmp_path / "logs" / "readme.md").write_text("keep me\n", encoding="utf-8")
    (tmp_path / "state.json").write_text('{"active": true}\n', encoding="utf-8")

    snapshots = snapshot_project_files(tmp_path)

    assert "src/app.py" in snapshots
    assert "logs/coding-agent-telegram.log" not in snapshots
    assert "logs/readme.md" in snapshots
    assert "state.json" in snapshots


def test_snapshot_project_files_respects_max_text_file_bytes(tmp_path: Path):
    (tmp_path / "big.txt").write_text("x" * 20, encoding="utf-8")

    snapshots = snapshot_project_files(tmp_path, max_text_file_bytes=10)

    assert snapshots["big.txt"] is None
