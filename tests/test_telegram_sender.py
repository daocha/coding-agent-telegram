import asyncio
from types import SimpleNamespace

from telegram.error import BadRequest

from coding_agent_telegram.telegram_sender import markdownish_to_html, send_code_block, send_html_text, send_text


def test_markdownish_to_html_handles_mixed_links_code_and_bold_without_unbalanced_code_tags():
    text = "See [agent_runner.py](/tmp/agent_runner.py), `config.py`, and **plain bold**."

    rendered = markdownish_to_html(text)

    assert rendered.count("<code>") == rendered.count("</code>")
    assert "<code>agent_runner.py</code>" in rendered
    assert "<code>config.py</code>" in rendered
    assert "<b>plain bold</b>" in rendered


def test_markdownish_to_html_does_not_reprocess_generated_code_tags():
    text = "`[agent_runner.py](/tmp/agent_runner.py)`"

    rendered = markdownish_to_html(text)

    assert rendered == "<code>[agent_runner.py](/tmp/agent_runner.py)</code>"


def test_send_html_text_falls_back_to_plain_text_on_parse_error():
    calls = []

    class FakeBot:
        async def send_message(self, chat_id, text, parse_mode=None):
            calls.append((chat_id, text, parse_mode))
            if len(calls) == 1:
                raise BadRequest("Can't parse entities: can't find end tag corresponding to start tag \"code\"")

    update = SimpleNamespace(effective_chat=SimpleNamespace(id=123))
    context = SimpleNamespace(bot=FakeBot())

    asyncio.run(send_html_text(update, context, "<b>Codex output</b>\n<code>oops"))

    assert len(calls) == 2
    assert calls[1][1] == "Codex output\noops"


def test_send_text_chunks_long_messages():
    calls = []

    class FakeBot:
        async def send_message(self, chat_id, text, parse_mode=None):
            calls.append((chat_id, text, parse_mode))

    update = SimpleNamespace(effective_chat=SimpleNamespace(id=123))
    context = SimpleNamespace(bot=FakeBot())

    asyncio.run(send_text(update, context, "a" * 7000))

    assert len(calls) >= 3
    assert all(len(call[1]) <= 3000 for call in calls)


def test_send_html_text_chunks_long_messages_as_plain_text():
    calls = []

    class FakeBot:
        async def send_message(self, chat_id, text, parse_mode=None):
            calls.append((chat_id, text, parse_mode))

    update = SimpleNamespace(effective_chat=SimpleNamespace(id=123))
    context = SimpleNamespace(bot=FakeBot())

    asyncio.run(send_html_text(update, context, "<b>" + ("a" * 7000) + "</b>"))

    assert len(calls) >= 3
    assert all(len(call[1]) <= 3000 for call in calls)


def test_send_code_block_chunks_long_code_blocks():
    calls = []

    class FakeBot:
        async def send_message(self, chat_id, text, parse_mode=None):
            calls.append((chat_id, text, parse_mode))

    update = SimpleNamespace(effective_chat=SimpleNamespace(id=123))
    context = SimpleNamespace(bot=FakeBot())

    asyncio.run(send_code_block(update, context, "Code", "x" * 7000, language="python"))

    assert len(calls) >= 4
    assert all(len(call[1]) <= 3000 for call in calls)
