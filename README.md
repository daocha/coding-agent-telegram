# coding-agent-telegram

A Telegram bot bridge for local coding agents such as Codex CLI and Copilot CLI. It lets you manage multiple project sessions from Telegram while keeping execution on your own machine.

## ✨ What It Does

- Connect one Telegram account to multiple Telegram bots.
- Keep sessions isolated per bot and per chat.
- Bind each session to one project folder and one provider.
- Run local coding agents inside your workspace.
- Show Codex output and file changes back in Telegram.
- Auto-create missing project folders with `/project <folder>`.

## ✅ Requirements

Before starting the server, make sure you have:

- Python 3.9 or newer
- A Telegram bot token from BotFather
- Your Telegram chat ID
- Codex CLI and/or Copilot CLI installed locally
- A workspace directory that contains your projects

## 🚀 Quick Start

### 1. Clone the repository

```bash
git clone <your-repo-url>
cd coding-agent-telegram
```

### 2. Start with the bootstrap script

```bash
./startup.sh
```

What `startup.sh` does:

- creates `.env` from `.env.example` if missing
- creates the state files if missing
- creates `.venv` if missing
- installs the package into the virtual environment
- starts the Telegram bot server

### 3. Update `.env`

On first run, update the required fields in `.env`:

- `WORKSPACE_ROOT`
- `TELEGRAM_BOT_TOKENS`
- `ALLOWED_CHAT_IDS`

Then run again:

```bash
./startup.sh
```

## ⚙️ Environment Variables

These are the main fields in `.env`.

### Required

- `WORKSPACE_ROOT`
  Parent folder that contains your project directories.
  Example: `WORKSPACE_ROOT=~/git`

- `TELEGRAM_BOT_TOKENS`
  Comma-separated Telegram bot tokens.
  Example: `TELEGRAM_BOT_TOKENS=token_one,token_two`

- `ALLOWED_CHAT_IDS`
  Comma-separated Telegram chat IDs allowed to use the bot.
  Example: `ALLOWED_CHAT_IDS=123456789,987654321`

### State and Logging

- `STATE_FILE`
  JSON file used to store session state.
  Default: `./state.json`

- `STATE_BACKUP_FILE`
  Backup copy of the state file.
  Default: `./state.json.bak`

- `LOG_LEVEL`
  Python app log level.
  Default: `INFO`

- `LOG_DIR`
  Directory for application logs.
  Default: `./logs`

### Agent Configuration

- `DEFAULT_AGENT_PROVIDER`
  Default provider for `/new` when none is specified.
  Supported values: `codex`, `copilot`

- `CODEX_BIN`
  Command used to launch Codex CLI.
  Default: `codex`

- `COPILOT_BIN`
  Command used to launch Copilot CLI.
  Default: `copilot`

- `CODEX_MODEL`
  Optional Codex model override.
  Leave empty to use the Codex CLI default model.
  Example: `CODEX_MODEL=gpt-5.4`

- `COPILOT_MODEL`
  Optional Copilot model override.
  Leave empty to use the Copilot CLI default model.
  Examples: `COPILOT_MODEL=gpt-5.4`, `COPILOT_MODEL=claude-sonnet-4.6`

Use the official model references before setting these values:

- OpenAI Codex/OpenAI models: `https://developers.openai.com/codex/models`
- GitHub Copilot supported models: `https://docs.github.com/en/copilot/reference/ai-models/supported-models`

- `CODEX_APPROVAL_POLICY`
  Approval mode passed to Codex.
  Default: `never`

- `CODEX_SANDBOX_MODE`
  Sandbox mode passed to Codex.
  Default: `workspace-write`

- `CODEX_SKIP_GIT_REPO_CHECK`
  If `true`, always bypass Codex's trusted-repo check.
  If `false`, existing third-party folders stay protected unless trusted by this app.

### Telegram Behavior

- `MAX_TELEGRAM_MESSAGE_LENGTH`
  Max message size used before the app splits responses.

- `ENABLE_GROUP_CHATS`
  Allow or block use in group chats.

- `ENABLE_SENSITIVE_DIFF_FILTER`
  Hide diffs for sensitive paths.

### Example `.env` Snippet

```env
WORKSPACE_ROOT=~/git
TELEGRAM_BOT_TOKENS=bot_token_one,bot_token_two
ALLOWED_CHAT_IDS=123456789

CODEX_BIN=codex
COPILOT_BIN=copilot

CODEX_MODEL=gpt-5.4
COPILOT_MODEL=claude-sonnet-4.6

CODEX_APPROVAL_POLICY=never
CODEX_SANDBOX_MODE=workspace-write
CODEX_SKIP_GIT_REPO_CHECK=false

LOG_LEVEL=INFO
LOG_DIR=./logs
```

## 🤖 Telegram Commands

- `/project <project_folder>`
  Set the current project folder. If the folder does not exist, the app creates it.

- `/new <session_name> [provider]`
  Create a new session for the current project.

- `/switch`
  Show the latest 10 sessions, newest first.

- `/switch page <number>`
  Show another page of stored sessions.

- `/switch <session_id>`
  Switch to a specific session by ID.

- `/current`
  Show the active session for the current bot and chat.

## 🧠 Session Model

Sessions are scoped by:

- Telegram bot
- Telegram chat

That means the same Telegram account can use multiple bots without mixing sessions.

Example:

- Bot A + your chat -> backend work
- Bot B + your chat -> frontend work
- Bot C + your chat -> infra work

Each session stores:

- session name
- project folder
- provider
- timestamps
- active session selection for that bot/chat scope

## 🔐 Git Trust Behavior

- Existing folders follow `CODEX_SKIP_GIT_REPO_CHECK`
- Folders created through `/project <name>` are marked as trusted by this app
- That means newly created project folders can be used immediately

## 🪵 Logs

Logs are written under `LOG_DIR`.

Main log file:

- `coding-agent-telegram.log`

Typical logged events:

- bot startup and polling start
- project selection
- session creation
- session switching
- active session reporting
- normal run execution
- session replacement after resume failure
- warnings and runtime errors

## 🗂️ Project Structure

- `src/coding_agent_telegram/`
  Main application code

- `tests/`
  Test suite

- `startup.sh`
  Local bootstrap and startup entrypoint

- `.env.example`
  Environment template for repo users

- `pyproject.toml`
  Packaging and dependency configuration

## 🛠️ Typical Local Flow

```bash
./startup.sh
```

Then in Telegram:

```text
/project my-project
/new my-session
Fix the failing API test in the current project
```

## 📌 Notes

- This project is designed for users running the agents locally on their own machine.
- The Telegram bot is a control surface, not the execution environment itself.
- If you run multiple bots, all of them can be managed by one server process.
