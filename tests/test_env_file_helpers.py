from coding_agent_telegram.config import read_env_value, remove_env_value, upsert_env_value


def test_upsert_env_value_appends_when_missing(tmp_path):
    env_path = tmp_path / ".env"
    env_path.write_text("WORKSPACE_ROOT=~/git\n", encoding="utf-8")

    upsert_env_value(env_path, "CLAUDE_CODE_OAUTH_TOKEN", "sk-ant-oat01-abc", comments=["# a comment"])

    text = env_path.read_text(encoding="utf-8")
    assert "WORKSPACE_ROOT=~/git" in text
    assert "CLAUDE_CODE_OAUTH_TOKEN=sk-ant-oat01-abc" in text
    assert "# a comment" in text


def test_upsert_env_value_overwrites_existing(tmp_path):
    env_path = tmp_path / ".env"
    env_path.write_text("CLAUDE_CODE_OAUTH_TOKEN=old-value\nOTHER=1\n", encoding="utf-8")

    upsert_env_value(env_path, "CLAUDE_CODE_OAUTH_TOKEN", "new-value")

    text = env_path.read_text(encoding="utf-8")
    assert "CLAUDE_CODE_OAUTH_TOKEN=new-value" in text
    assert "old-value" not in text
    assert "OTHER=1" in text


def test_upsert_env_value_creates_missing_file(tmp_path):
    env_path = tmp_path / "nested" / ".env"

    upsert_env_value(env_path, "KEY", "value")

    assert env_path.read_text(encoding="utf-8") == "KEY=value\n"


def test_read_env_value_returns_none_when_missing(tmp_path):
    env_path = tmp_path / ".env"
    env_path.write_text("OTHER=1\n", encoding="utf-8")

    assert read_env_value(env_path, "CLAUDE_CODE_OAUTH_TOKEN") is None


def test_read_env_value_returns_none_when_file_missing(tmp_path):
    assert read_env_value(tmp_path / "does-not-exist.env", "KEY") is None


def test_read_env_value_returns_current_value(tmp_path):
    env_path = tmp_path / ".env"
    env_path.write_text("CLAUDE_CODE_OAUTH_TOKEN=sk-ant-oat01-xyz\n", encoding="utf-8")

    assert read_env_value(env_path, "CLAUDE_CODE_OAUTH_TOKEN") == "sk-ant-oat01-xyz"


def test_remove_env_value_drops_only_matching_key(tmp_path):
    env_path = tmp_path / ".env"
    env_path.write_text("CLAUDE_CODE_OAUTH_TOKEN=sk-ant-oat01-xyz\nOTHER=1\n", encoding="utf-8")

    remove_env_value(env_path, "CLAUDE_CODE_OAUTH_TOKEN")

    text = env_path.read_text(encoding="utf-8")
    assert "CLAUDE_CODE_OAUTH_TOKEN" not in text
    assert "OTHER=1" in text


def test_remove_env_value_noop_when_file_missing(tmp_path):
    # Should not raise.
    remove_env_value(tmp_path / "does-not-exist.env", "KEY")
