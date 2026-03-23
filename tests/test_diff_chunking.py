from coding_agent_telegram.diff_utils import chunk_fenced_diff


def test_chunk_fenced_diff_limits():
    content = "\n".join([f"+ line {i}" for i in range(1000)])
    chunks = chunk_fenced_diff("src/api.py", content, 3000)
    assert len(chunks) > 1
    for msg in chunks:
        assert msg.count("```") == 2
        assert "src/api.py" in msg
