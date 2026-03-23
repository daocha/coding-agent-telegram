# coding-agent-telegram

A PyPI-ready Telegram bot bridge for local coding agents.

## Highlights

- Secure workspace-bound project execution.
- Per-chat session management.
- Session-level provider binding (`codex` or `copilot`).
- Git-based changed-file and diff reporting.
- Sensitive diff filtering and Telegram-safe chunk splitting.

## Session/provider model

Each Telegram chat can own multiple sessions. Every session is permanently bound to:

- one project folder
- one provider (`codex` or `copilot`)

Example use case:

- chat 1 -> codex session 1
- chat 2 -> codex session 2
- chat 3 -> copilot session 1

## Commands

- `/project <project_folder>`
- `/new <session_name> [provider]` (provider defaults to `codex`)
- `/switch` / `/switch <session_id>`
- `/current`

## Run

```bash
pip install .
coding-agent-telegram
```
