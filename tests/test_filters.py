from coding_agent_telegram.filters import is_sensitive_path


def test_is_sensitive_path_matches_resource_patterns():
    assert is_sensitive_path(".env") is True
    assert is_sensitive_path(".env.local") is True
    assert is_sensitive_path(".env_coding_agent_telegram") is True
    assert is_sensitive_path("config/secrets.toml") is True
    assert is_sensitive_path(".ssh/id_ed25519") is True
    assert is_sensitive_path("src/app.py") is False
