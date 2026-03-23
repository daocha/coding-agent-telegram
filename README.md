# coding-agent-telegram

A PyPI-ready Telegram bot bridge for local coding agents.

## Highlights

- Secure workspace-bound project execution.
- Per-bot, per-chat session management.
- Session-level provider binding (`codex` or `copilot`).
- Multi-bot polling from one process.
- Git-based changed-file and diff reporting.
- Sensitive diff filtering and Telegram-safe chunk splitting.

## Session/provider model

Each Telegram bot + Telegram chat pair can own multiple sessions. This lets one Telegram account talk to multiple bots while keeping each bot's session list separate. Every session is permanently bound to:

- one project folder
- one provider (`codex` or `copilot`)

Example use case:

- bot A + chat 1 -> backend session
- bot B + chat 1 -> frontend session
- bot C + chat 1 -> infra session

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

## Environment

- `TELEGRAM_BOT_TOKENS`: comma-separated bot tokens
- `ALLOWED_CHAT_IDS`: comma-separated Telegram chat IDs
- `CODEX_SKIP_GIT_REPO_CHECK`: `true` to always bypass Codex's trusted-repo check, `false` to enforce it for existing folders

## Git Trust

- Existing folders follow `CODEX_SKIP_GIT_REPO_CHECK`
- Folders created by `/project <name>` are recorded as trusted by this app and will bypass the Codex repo check afterward
