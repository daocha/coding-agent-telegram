from coding_agent_telegram.diff_utils import _parse_status_paths, chunk_fenced_diff, chunk_plain_text


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
