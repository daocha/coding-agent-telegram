from __future__ import annotations

import html
import re
from dataclasses import dataclass
from typing import Optional

from telegram import Update
from telegram.constants import ParseMode
from telegram.error import BadRequest
from telegram.ext import ContextTypes

MARKDOWN_LINK_RE = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")
INLINE_CODE_RE = re.compile(r"`([^`]+)`")
BOLD_RE = re.compile(r"\*\*([^*]+)\*\*")
FENCED_BLOCK_RE = re.compile(r"```([A-Za-z0-9_+-]*)\n(.*?)```", re.DOTALL)
COMMAND_PREFIXES = (
    "$ ",
    "git ",
    "python ",
    "python3 ",
    "pip ",
    "pip3 ",
    "uv ",
    "npm ",
    "pnpm ",
    "yarn ",
    "docker ",
    "docker-compose ",
    "kubectl ",
    "make ",
    "bash ",
    "sh ",
    "zsh ",
    "node ",
    "npx ",
    "pytest ",
    "cargo ",
    "go ",
    "curl ",
    "wget ",
    "chmod ",
    "chown ",
    "ln ",
    "cp ",
    "mv ",
    "rm ",
    "mkdir ",
    "touch ",
    "cat ",
    "sed ",
    "awk ",
    "grep ",
    "rg ",
    "find ",
)
SHELL_LANGUAGES = {"bash", "console", "shell", "sh", "zsh"}


@dataclass(frozen=True)
class AssistantSegment:
    kind: str
    text: str
    header: str = ""
    language: Optional[str] = None


async def send_text(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str) -> None:
    if update.effective_chat is None:
        return
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=html.escape(text),
        parse_mode=ParseMode.HTML,
    )


async def send_markdown_text(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str) -> None:
    if update.effective_chat is None:
        return
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=text,
        parse_mode=ParseMode.MARKDOWN,
    )


async def send_html_text(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str) -> None:
    if update.effective_chat is None:
        return
    try:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=text,
            parse_mode=ParseMode.HTML,
        )
    except BadRequest as exc:
        if "Can't parse entities" not in str(exc):
            raise
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=html.escape(_strip_html_tags(text)),
            parse_mode=ParseMode.HTML,
        )


def markdownish_to_html(text: str) -> str:
    parts: list[str] = []
    last = 0

    token_re = re.compile(r"\[([^\]]+)\]\(([^)]+)\)|`([^`]+)`")
    for match in token_re.finditer(text):
        parts.append(_format_plain_markdownish(text[last : match.start()]))
        inline_code = match.group(3)
        if inline_code is not None:
            parts.append(f"<code>{html.escape(inline_code)}</code>")
        else:
            label = html.escape(match.group(1))
            url = match.group(2).strip()
            if url.startswith(("http://", "https://")):
                parts.append(f'<a href="{html.escape(url, quote=True)}">{label}</a>')
            else:
                parts.append(f"<code>{label}</code>")
        last = match.end()

    parts.append(_format_plain_markdownish(text[last:]))
    return "".join(parts)


def _format_plain_markdownish(text: str) -> str:
    escaped = html.escape(text)
    return BOLD_RE.sub(lambda match: f"<b>{html.escape(match.group(1))}</b>", escaped)


def _strip_html_tags(text: str) -> str:
    normalized = text.replace("<br>", "\n").replace("<br/>", "\n").replace("<br />", "\n")
    return html.unescape(re.sub(r"</?[^>]+>", "", normalized))


def split_assistant_output(text: str) -> list[AssistantSegment]:
    segments: list[AssistantSegment] = []
    last = 0

    for match in FENCED_BLOCK_RE.finditer(text):
        prose = text[last : match.start()]
        segments.extend(_split_prose_and_commands(prose))

        language = (match.group(1) or "").strip().lower() or None
        code = match.group(2).strip("\n")
        if code:
            header = "Command" if language in SHELL_LANGUAGES or _looks_like_shell_block(code) else "Code"
            segments.append(AssistantSegment(kind="code", text=code, header=header, language=language))
        last = match.end()

    segments.extend(_split_prose_and_commands(text[last:]))
    return [segment for segment in segments if segment.text.strip()]


def _split_prose_and_commands(text: str) -> list[AssistantSegment]:
    lines = text.splitlines()
    if not lines:
        return []

    out: list[AssistantSegment] = []
    prose_lines: list[str] = []
    index = 0

    while index < len(lines):
        line = lines[index]
        if _looks_like_shell_command(line):
            if prose_lines:
                prose = "\n".join(prose_lines).strip()
                if prose:
                    out.append(AssistantSegment(kind="prose", text=prose))
                prose_lines = []

            command_lines = [line]
            index += 1
            while index < len(lines):
                next_line = lines[index]
                previous_line = command_lines[-1].rstrip()
                if not next_line.strip():
                    break
                if previous_line.endswith("\\") or next_line.startswith(("  ", "\t", "--", "&&", "||", "|")):
                    command_lines.append(next_line)
                    index += 1
                    continue
                break
            out.append(AssistantSegment(kind="code", text="\n".join(command_lines).strip(), header="Command", language="bash"))
            continue

        prose_lines.append(line)
        index += 1

    if prose_lines:
        prose = "\n".join(prose_lines).strip()
        if prose:
            out.append(AssistantSegment(kind="prose", text=prose))
    return out


def _looks_like_shell_command(line: str) -> bool:
    stripped = line.strip()
    return any(stripped.startswith(prefix) for prefix in COMMAND_PREFIXES)


def _looks_like_shell_block(text: str) -> bool:
    lines = [line for line in text.splitlines() if line.strip()]
    return bool(lines) and all(_looks_like_shell_command(line) for line in lines[: min(3, len(lines))])


async def send_code_block(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    header: str,
    code: str,
    *,
    language: Optional[str] = None,
) -> None:
    if update.effective_chat is None:
        return
    escaped_code = html.escape(code)
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=html.escape(header),
        parse_mode=ParseMode.HTML,
    )
    if language:
        text = f"<pre><code class=\"language-{html.escape(language)}\">{escaped_code}</code></pre>"
    else:
        text = f"<pre><code>{escaped_code}</code></pre>"
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=text,
        parse_mode=ParseMode.HTML,
    )
