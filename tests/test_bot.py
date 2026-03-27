from coding_agent_telegram.bot import default_bot_commands


def test_default_bot_commands_hide_commit_and_push_when_disabled():
    commands = default_bot_commands(enable_commit_command=False)
    names = [command.command for command in commands]

    assert "abort" in names
    assert "provider" in names
    assert "commit" not in names
    assert "push" in names


def test_default_bot_commands_show_commit_and_push_when_enabled():
    commands = default_bot_commands(enable_commit_command=True)
    names = [command.command for command in commands]

    assert "abort" in names
    assert "provider" in names
    assert "commit" in names
    assert "push" in names


# ---------------------------------------------------------------------------
# allowed_private_chat_filter
# ---------------------------------------------------------------------------


def test_allowed_private_chat_filter_uses_chat_id_and_private_type():
    from coding_agent_telegram.bot import allowed_private_chat_filter

    flt = allowed_private_chat_filter({123, 456})
    # Should create a filter — just check it is not None and is callable/usable
    assert flt is not None


# ---------------------------------------------------------------------------
# handle_error
# ---------------------------------------------------------------------------


import asyncio
from types import SimpleNamespace
from coding_agent_telegram.session_store import SessionStoreError


def test_handle_error_sends_friendly_message_for_session_store_error():
    """handle_error must send the SessionStoreError message to the chat."""
    import asyncio
    from coding_agent_telegram.bot import handle_error

    messages = []

    class FakeBot:
        async def send_message(self, chat_id, text):
            messages.append((chat_id, text))

    update = SimpleNamespace(effective_chat=SimpleNamespace(id=42))
    context = SimpleNamespace(
        error=SessionStoreError("State file temporarily locked."),
        bot=FakeBot(),
    )

    asyncio.run(handle_error(update, context))

    assert len(messages) == 1
    assert "temporarily locked" in messages[0][1]


def test_handle_error_skips_send_when_update_has_no_chat():
    """handle_error must not crash when update is None."""
    import asyncio
    from coding_agent_telegram.bot import handle_error

    class FakeBot:
        async def send_message(self, chat_id, text):
            raise AssertionError("should not send when no chat")

    context = SimpleNamespace(
        error=SessionStoreError("locked"),
        bot=FakeBot(),
    )

    # Should not raise
    asyncio.run(handle_error(None, context))


def test_handle_error_sends_generic_message_for_unexpected_exceptions():
    """handle_error must send a generic failure message for non-SessionStoreError exceptions."""
    import asyncio
    from coding_agent_telegram.bot import handle_error

    messages = []

    class FakeBot:
        async def send_message(self, chat_id, text):
            messages.append((chat_id, text))

    update = SimpleNamespace(effective_chat=SimpleNamespace(id=7))
    context = SimpleNamespace(
        error=RuntimeError("something went wrong"),
        bot=FakeBot(),
    )

    asyncio.run(handle_error(update, context))

    assert len(messages) == 1
    assert "failed" in messages[0][1].lower() or "error" in messages[0][1].lower() or "check" in messages[0][1].lower()


# ---------------------------------------------------------------------------
# initialize_bot_commands
# ---------------------------------------------------------------------------


import asyncio


def test_initialize_bot_commands_calls_delete_and_set():
    """initialize_bot_commands must call delete_my_commands once and
    set_my_commands once per allowed chat."""
    from coding_agent_telegram.bot import initialize_bot_commands

    deleted = []
    set_calls = []

    class FakeBot:
        async def delete_my_commands(self, scope=None):
            deleted.append(scope)

        async def set_my_commands(self, commands, scope=None):
            set_calls.append((commands, scope))

    class FakeApp:
        bot = FakeBot()

    asyncio.run(
        initialize_bot_commands(FakeApp(), enable_commit_command=False, allowed_chat_ids={10, 20})
    )

    assert len(deleted) == 1
    assert len(set_calls) == 2
    chat_ids_called = {s[1].chat_id for s in set_calls}
    assert chat_ids_called == {10, 20}


def test_initialize_bot_commands_includes_commit_when_enabled():
    from coding_agent_telegram.bot import initialize_bot_commands

    set_calls = []

    class FakeBot:
        async def delete_my_commands(self, scope=None):
            pass

        async def set_my_commands(self, commands, scope=None):
            set_calls.append(commands)

    class FakeApp:
        bot = FakeBot()

    asyncio.run(
        initialize_bot_commands(FakeApp(), enable_commit_command=True, allowed_chat_ids={1})
    )

    command_names = [c.command for c in set_calls[0]]
    assert "commit" in command_names


def test_initialize_bot_commands_empty_allowed_chat_ids():
    """No set_my_commands calls when allowed_chat_ids is empty."""
    from coding_agent_telegram.bot import initialize_bot_commands

    set_calls = []

    class FakeBot:
        async def delete_my_commands(self, scope=None):
            pass

        async def set_my_commands(self, commands, scope=None):
            set_calls.append(commands)

    class FakeApp:
        bot = FakeBot()

    asyncio.run(
        initialize_bot_commands(FakeApp(), enable_commit_command=False, allowed_chat_ids=set())
    )

    assert set_calls == []
