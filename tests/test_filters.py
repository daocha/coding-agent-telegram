from coding_agent_telegram.filters import is_sensitive_path


def test_is_sensitive_path_matches_resource_patterns():
    assert is_sensitive_path(".env") is True
    assert is_sensitive_path(".env.local") is True
    assert is_sensitive_path(".env_coding_agent_telegram") is True
    assert is_sensitive_path("config/secrets.toml") is True
    assert is_sensitive_path(".ssh/id_ed25519") is True
    assert is_sensitive_path("src/app.py") is False


# ---------------------------------------------------------------------------
# is_valid_project_folder — backslash rejection (line 28)
# ---------------------------------------------------------------------------


def test_is_valid_project_folder_rejects_backslash():
    from coding_agent_telegram.filters import is_valid_project_folder

    assert is_valid_project_folder("back\\slash") is False
