from coding_agent_telegram.bot import default_bot_commands


def test_default_bot_commands_hide_commit_and_push_when_disabled():
    commands = default_bot_commands(enable_commit_command=False)
    names = [command.command for command in commands]

    assert "provider" in names
    assert "commit" not in names
    assert "push" in names


def test_default_bot_commands_show_commit_and_push_when_enabled():
    commands = default_bot_commands(enable_commit_command=True)
    names = [command.command for command in commands]

    assert "provider" in names
    assert "commit" in names
    assert "push" in names
