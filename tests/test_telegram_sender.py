import asyncio
from types import SimpleNamespace

import pytest
from telegram.error import BadRequest

from coding_agent_telegram.telegram_sender import (
    markdownish_to_html,
    send_code_block,
    send_html_text,
    send_markdown_text,
    send_text,
)


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
        async def send_message(self, chat_id, text, parse_mode=None, reply_to_message_id=None):
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
        async def send_message(self, chat_id, text, parse_mode=None, reply_to_message_id=None):
            calls.append((chat_id, text, parse_mode))

    update = SimpleNamespace(effective_chat=SimpleNamespace(id=123))
    context = SimpleNamespace(bot=FakeBot(), bot_data={"max_telegram_message_length": 500})

    asyncio.run(send_text(update, context, "a" * 1500))

    assert len(calls) >= 3
    assert all(len(call[1]) <= 500 for call in calls)


def test_send_html_text_chunks_long_messages_as_plain_text():
    calls = []

    class FakeBot:
        async def send_message(self, chat_id, text, parse_mode=None, reply_to_message_id=None):
            calls.append((chat_id, text, parse_mode))

    update = SimpleNamespace(effective_chat=SimpleNamespace(id=123))
    context = SimpleNamespace(bot=FakeBot(), bot_data={"max_telegram_message_length": 500})

    asyncio.run(send_html_text(update, context, "<b>" + ("a" * 1500) + "</b>"))

    assert len(calls) >= 3
    assert all(len(call[1]) <= 500 for call in calls)


def test_send_code_block_chunks_long_code_blocks():
    calls = []

    class FakeBot:
        async def send_message(self, chat_id, text, parse_mode=None, reply_to_message_id=None):
            calls.append((chat_id, text, parse_mode))

    update = SimpleNamespace(effective_chat=SimpleNamespace(id=123))
    context = SimpleNamespace(bot=FakeBot(), bot_data={"max_telegram_message_length": 500})

    asyncio.run(send_code_block(update, context, "Code", "x" * 1500, language="python"))

    assert len(calls) >= 4
    assert all(len(call[1]) <= 500 for call in calls)


# ---------------------------------------------------------------------------
# Null effective_chat guards
# ---------------------------------------------------------------------------


def test_send_text_does_nothing_when_effective_chat_is_none():
    """send_text must return without error when update.effective_chat is None."""
    called = []

    class FakeBot:
        async def send_message(self, chat_id, text, parse_mode=None, reply_to_message_id=None):
            called.append(text)

    update = SimpleNamespace(effective_chat=None)
    context = SimpleNamespace(bot=FakeBot())

    asyncio.run(send_text(update, context, "hello"))
    assert called == []


def test_send_html_text_does_nothing_when_effective_chat_is_none():
    called = []

    class FakeBot:
        async def send_message(self, chat_id, text, parse_mode=None, reply_to_message_id=None):
            called.append(text)

    update = SimpleNamespace(effective_chat=None)
    context = SimpleNamespace(bot=FakeBot())

    asyncio.run(send_html_text(update, context, "<b>hi</b>"))
    assert called == []


def test_send_code_block_does_nothing_when_effective_chat_is_none():
    called = []

    class FakeBot:
        async def send_message(self, chat_id, text, parse_mode=None, reply_to_message_id=None):
            called.append(text)

    update = SimpleNamespace(effective_chat=None)
    context = SimpleNamespace(bot=FakeBot())

    asyncio.run(send_code_block(update, context, "Output", "some code"))
    assert called == []


# ---------------------------------------------------------------------------
# _max_telegram_message_length fallbacks
# ---------------------------------------------------------------------------


def test_send_text_uses_default_length_when_no_bot_data():
    """Without bot_data, send_text must use the package default max length."""
    calls = []

    class FakeBot:
        async def send_message(self, chat_id, text, parse_mode=None, reply_to_message_id=None):
            calls.append(text)

    update = SimpleNamespace(effective_chat=SimpleNamespace(id=1))
    context = SimpleNamespace(bot=FakeBot())  # no bot_data attribute

    asyncio.run(send_text(update, context, "short message"))
    assert len(calls) == 1


# ---------------------------------------------------------------------------
# markdownish_to_html: non-http link falls back to code span
# ---------------------------------------------------------------------------


def test_markdownish_to_html_renders_non_http_link_as_code():
    from coding_agent_telegram.telegram_sender import markdownish_to_html

    result = markdownish_to_html("[relative/path](relative/path)")
    assert "<code>relative/path</code>" in result
    assert "<a href=" not in result


def test_markdownish_to_html_renders_bold_text():
    from coding_agent_telegram.telegram_sender import markdownish_to_html

    result = markdownish_to_html("This is **bold** text.")
    assert "<b>bold</b>" in result


def test_markdownish_to_html_does_not_double_escape_html_in_bold():
    from coding_agent_telegram.telegram_sender import markdownish_to_html

    result = markdownish_to_html("Use **git add & commit** to stage.")
    assert "<b>git add &amp; commit</b>" in result
    assert "&amp;amp;" not in result


# ---------------------------------------------------------------------------
# _split_plain_text_chunk edge cases
# ---------------------------------------------------------------------------


def test_split_text_chunks_handles_single_long_word_without_spaces():
    """A chunk with no whitespace must still be split at the midpoint."""
    from coding_agent_telegram.telegram_sender import _split_plain_text_chunk

    text = "A" * 200
    left, right = _split_plain_text_chunk(text)
    assert left
    assert right
    assert left + right == text or len(left) + len(right) <= len(text)


def test_split_text_chunks_prefers_whitespace_split():
    from coding_agent_telegram.telegram_sender import _split_plain_text_chunk

    text = "first half second half"
    left, right = _split_plain_text_chunk(text)
    assert left
    assert right
    assert " " not in left[-1] or " " not in right[0]


# ---------------------------------------------------------------------------
# send_markdown_text happy path
# ---------------------------------------------------------------------------


def test_send_markdown_text_sends_message():
    """send_markdown_text must call bot.send_message with MARKDOWN parse mode."""
    calls = []

    class FakeBot:
        async def send_message(self, chat_id, text, parse_mode=None, reply_to_message_id=None):
            calls.append((chat_id, text, parse_mode))

    from telegram.constants import ParseMode

    update = SimpleNamespace(effective_chat=SimpleNamespace(id=99))
    context = SimpleNamespace(bot=FakeBot())

    asyncio.run(send_markdown_text(update, context, "**hello**"))
    assert len(calls) == 1
    assert calls[0][0] == 99
    assert calls[0][1] == "**hello**"
    assert calls[0][2] == ParseMode.MARKDOWN


def test_send_markdown_text_does_nothing_when_no_chat():
    """send_markdown_text must silently return when effective_chat is None."""
    called = []

    class FakeBot:
        async def send_message(self, **kwargs):
            called.append(kwargs)

    update = SimpleNamespace(effective_chat=None)
    context = SimpleNamespace(bot=FakeBot())

    asyncio.run(send_markdown_text(update, context, "hi"))
    assert called == []


# ---------------------------------------------------------------------------
# send_html_text: BadRequest that is NOT a parse-entities error must re-raise
# ---------------------------------------------------------------------------


def test_send_html_text_reraises_non_parse_bad_request():
    """A BadRequest with a different message should propagate, not be swallowed."""
    from telegram.error import BadRequest

    class FakeBot:
        async def send_message(self, chat_id, text, parse_mode=None, reply_to_message_id=None):
            raise BadRequest("Message is too long")

    update = SimpleNamespace(effective_chat=SimpleNamespace(id=1))
    context = SimpleNamespace(bot=FakeBot(), bot_data={})

    import pytest

    with pytest.raises(BadRequest):
        asyncio.run(send_html_text(update, context, "<b>x</b>"))


# ---------------------------------------------------------------------------
# markdownish_to_html: HTTP link renders as anchor tag
# ---------------------------------------------------------------------------


def test_markdownish_to_html_renders_http_link_as_anchor():
    """A markdown link with an http/https URL must become an HTML anchor."""
    from coding_agent_telegram.telegram_sender import markdownish_to_html

    result = markdownish_to_html("[GitHub](https://github.com)")
    assert 'href="https://github.com"' in result
    assert "GitHub" in result


# ---------------------------------------------------------------------------
# _split_plain_text_chunk: multi-line path and fallback paths
# ---------------------------------------------------------------------------


def test_split_plain_text_chunk_splits_multiline_at_midpoint():
    """Multi-line text must be split at the midpoint line."""
    from coding_agent_telegram.telegram_sender import _split_plain_text_chunk

    text = "line1\nline2\nline3\nline4"
    left, right = _split_plain_text_chunk(text)
    assert left
    assert right
    assert "line1" in left
    assert "line3" in right


def test_split_plain_text_chunk_fallback_when_no_whitespace():
    """A string with no whitespace must still produce two non-empty parts."""
    from coding_agent_telegram.telegram_sender import _split_plain_text_chunk

    # Single-line with no internal whitespace forces the final fallback
    text = "abcdefghij"
    left, right = _split_plain_text_chunk(text)
    assert left
    assert right
    assert left + right  # both parts non-empty


# ---------------------------------------------------------------------------
# split_assistant_output: text with shell commands
# ---------------------------------------------------------------------------


def test_split_assistant_output_with_shell_command():
    """Lines starting with shell-command prefixes must become code segments."""
    from coding_agent_telegram.telegram_sender import split_assistant_output

    text = "Some description.\n$ git status\n$ git diff"
    segments = split_assistant_output(text)
    kinds = [s.kind for s in segments]
    assert "code" in kinds
    assert "prose" in kinds


def test_split_assistant_output_command_then_prose():
    """A command block followed by prose text must produce both segment types."""
    from coding_agent_telegram.telegram_sender import split_assistant_output

    text = "$ npm install\nDone. The packages are installed."
    segments = split_assistant_output(text)
    kinds = [s.kind for s in segments]
    assert "code" in kinds


# ---------------------------------------------------------------------------
# _looks_like_shell_block
# ---------------------------------------------------------------------------


def test_looks_like_shell_block_true():
    """Text where all lines look like shell commands must return True."""
    from coding_agent_telegram.telegram_sender import _looks_like_shell_block

    assert _looks_like_shell_block("$ echo hello\n$ ls -la")


def test_looks_like_shell_block_false():
    """Plain prose must not be recognised as a shell block."""
    from coding_agent_telegram.telegram_sender import _looks_like_shell_block

    assert not _looks_like_shell_block("This is just regular text.")


def test_looks_like_shell_block_empty():
    """Empty text must return False."""
    from coding_agent_telegram.telegram_sender import _looks_like_shell_block

    assert not _looks_like_shell_block("")


# ---------------------------------------------------------------------------
# send_code_block without language parameter
# ---------------------------------------------------------------------------


def test_send_code_block_without_language():
    """send_code_block with no language must use plain <pre><code> tags."""
    calls = []

    class FakeBot:
        async def send_message(self, chat_id, text, parse_mode=None, reply_to_message_id=None):
            calls.append(text)

    update = SimpleNamespace(effective_chat=SimpleNamespace(id=7))
    context = SimpleNamespace(bot=FakeBot(), bot_data={})

    asyncio.run(send_code_block(update, context, "Output", "hello world"))
    # Should produce a header message and a code message without language class
    code_msg = calls[-1]
    assert "<pre><code>" in code_msg
    assert "language-" not in code_msg


# ---------------------------------------------------------------------------
# _split_text_chunks: empty / whitespace-only input
# ---------------------------------------------------------------------------


def test_split_text_chunks_empty_string_returns_empty_list():
    from coding_agent_telegram.telegram_sender import _split_text_chunks

    assert _split_text_chunks("") == []
    assert _split_text_chunks("   ") == []


# ---------------------------------------------------------------------------
# _split_plain_text_chunk: edge cases that hit the left/right fill-in lines
# ---------------------------------------------------------------------------


def test_split_plain_text_chunk_single_char_fills_left():
    """Single char: midpoint=0, left becomes empty and is filled from text[:1]."""
    from coding_agent_telegram.telegram_sender import _split_plain_text_chunk

    left, right = _split_plain_text_chunk("x")
    assert left  # must not be empty
    assert right  # must not be empty


def test_split_plain_text_chunk_single_space_fills_both():
    """Single space: both halves become empty and are filled from text[:1]/text[-1:]."""
    from coding_agent_telegram.telegram_sender import _split_plain_text_chunk

    left, right = _split_plain_text_chunk(" ")
    assert left
    assert right


# ---------------------------------------------------------------------------
# split_assistant_output: blank line breaks command block (line 243)
# and continuation lines are absorbed (lines 245-247)
# ---------------------------------------------------------------------------


def test_split_assistant_output_blank_line_breaks_command():
    """A blank line after a command must end the command block."""
    from coding_agent_telegram.telegram_sender import split_assistant_output

    text = "$ git status\n\nSome prose after."
    segments = split_assistant_output(text)
    kinds = [s.kind for s in segments]
    assert "code" in kinds


def test_split_assistant_output_continuation_line_joins_command():
    """A continuation line (starting with &&, |, etc.) must be merged into the command."""
    from coding_agent_telegram.telegram_sender import split_assistant_output

    text = "$ git add .\n&& git commit -m 'msg'\nDone."
    segments = split_assistant_output(text)
    code_segs = [s for s in segments if s.kind == "code"]
    assert code_segs
    # The continuation line must be part of the command segment
    assert "&&" in code_segs[0].text
