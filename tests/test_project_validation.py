from coding_agent_telegram.filters import is_valid_project_folder


def test_valid_project_names():
    assert is_valid_project_folder("backend")
    assert is_valid_project_folder("frontend-app")
    assert is_valid_project_folder("my_repo")


def test_invalid_project_names():
    invalid = [
        ".",
        "..",
        "./backend",
        "../backend",
        "/tmp/backend",
        "backend/api",
        "backend\\api",
    ]
    for item in invalid:
        assert not is_valid_project_folder(item)
