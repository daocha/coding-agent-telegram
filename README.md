# coding-agent-telegram

A Telegram bot bridge for local coding agents such as Codex CLI and Copilot CLI. It lets you manage multiple project sessions from Telegram while keeping execution on your own machine.

The bot accepts private chats only.

## ✨ What It Does

- Connect one Telegram account to multiple Telegram bots.
- Keep sessions isolated per bot and per chat.
- Bind each session to one project folder and one provider.
- Run local coding agents inside your workspace.
- Show Codex output and file changes back in Telegram.
- Accept text messages and photos as task input.
- Auto-create missing project folders with `/project <folder>`.

## ✅ Requirements

Before starting the server, make sure you have:

- Python 3.9 or newer
- A Telegram bot token from BotFather
- Your Telegram chat ID
- Codex CLI and/or Copilot CLI installed locally
- A workspace directory that contains your projects

## 🔑 Telegram Setup

### Get a Bot Token

1. Open Telegram and start a chat with `@BotFather`.
2. Send `/newbot`.
3. Follow the prompts to choose:
   - a display name
   - a bot username ending in `bot`
4. BotFather will return an HTTP API token.
5. Put that token into `TELEGRAM_BOT_TOKENS` in your `.env`.

### Get Your Chat ID

The most reliable way is to use Telegram's `getUpdates` API with your own bot token.

1. Start a chat with your bot and send it a message such as `/start`.
2. Open this URL in your browser, replacing `<BOT_TOKEN>`:

```text
https://api.telegram.org/bot<BOT_TOKEN>/getUpdates
```

3. Find the `chat` object in the JSON response.
4. Copy the numeric `id` field from that object.
5. Put that value into `ALLOWED_CHAT_IDS` in your `.env`.

Notes:

- For private chats, the chat ID is usually a positive integer.
- If `getUpdates` returns an empty result, send another message to the bot and try again.

## 🚀 Quick Start

### Option A: Run from a cloned repository

#### 1. Clone the repository

```bash
git clone https://github.com/daocha/coding-agent-telegram
cd coding-agent-telegram
```

#### 2. Start with the bootstrap script

```bash
./startup.sh
```

What `startup.sh` does:

- creates `.env` from `.env.example` if missing
- creates the state files if missing
- creates `.venv` if missing
- installs the package into the virtual environment
- starts the Telegram bot server

#### 3. Update `.env`

On first run, update the required fields in `.env`:

- `WORKSPACE_ROOT`
- `TELEGRAM_BOT_TOKENS`
- `ALLOWED_CHAT_IDS`

Then run again:

```bash
./startup.sh
```

### Option B: Install from PyPI with `pip`

```bash
pip install coding-agent-telegram
coding-agent-telegram
```

What happens on first run:

- the command creates `.env` in your current working directory if missing
- it tells you which required fields to update
- after updating `.env`, run `coding-agent-telegram` again

Recommended flow:

```bash
mkdir -p ~/my-coding-agent-bot
cd ~/my-coding-agent-bot
pip install coding-agent-telegram
coding-agent-telegram
```

Then update `.env` and run:

```bash
coding-agent-telegram
```

## 📨 Supported Message Types

The bot currently accepts:

- plain text messages
- photos

Current media behavior:

- photos are supported for Codex sessions
- videos are not supported
- video notes are not supported
- animations are not supported
- audio and voice messages are not supported
- documents and stickers are not supported

If an unsupported message type is sent, the bot replies with a short error instead of silently ignoring it.

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
  Comma-separated Telegram private chat IDs allowed to use the bot.
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

- `COPILOT_AUTOPILOT`
  Default: `true`
  Runs Copilot CLI in autopilot mode by default.

- `COPILOT_NO_ASK_USER`
  Default: `true`
  Tells Copilot CLI not to stop and ask the user interactive follow-up questions.

- `COPILOT_ALLOW_ALL`
  Default: `true`
  Passes `--allow-all`, which enables tools, paths, and URLs without confirmation.
  This is the default here so Copilot CLI can continue non-interactively inside the Telegram bot flow.

- `COPILOT_ALLOW_ALL_TOOLS`
  If `true`, pass `--allow-all-tools` to Copilot CLI.
  Use this only if you are comfortable letting Copilot run tools without approval prompts.

- `COPILOT_ALLOW_TOOLS`
  Comma-separated list of tools to allow without prompting.
  Example: `COPILOT_ALLOW_TOOLS=shell(git),shell(npm)`

- `COPILOT_DENY_TOOLS`
  Comma-separated list of tools to explicitly deny.
  Example: `COPILOT_DENY_TOOLS=shell(rm),shell(chmod)`

- `COPILOT_AVAILABLE_TOOLS`
  Optional comma-separated allowlist of tools Copilot may use at all.
  Example: `COPILOT_AVAILABLE_TOOLS=shell,apply_patch`

GitHub documents these Copilot CLI approval controls here:

- `https://docs.github.com/en/copilot/concepts/about-github-copilot-cli`
- `https://docs.github.com/en/copilot/reference/copilot-cli-reference/cli-command-reference`

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
COPILOT_AUTOPILOT=true
COPILOT_NO_ASK_USER=true
COPILOT_ALLOW_ALL=true
COPILOT_ALLOW_ALL_TOOLS=false
COPILOT_ALLOW_TOOLS=shell(git),shell(npm)
COPILOT_DENY_TOOLS=shell(rm)
COPILOT_AVAILABLE_TOOLS=shell,apply_patch

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

- `/branch <new_branch>`
  Create a new branch from the repository default branch, after fetching and pulling first.

- `/branch <origin_branch> <new_branch>`
  Create a new branch from a specific base branch, after fetching and pulling first.

- `/switch`
  Show the latest 10 sessions, newest first.

- `/switch page <number>`
  Show another page of stored sessions.

- `/switch <session_id>`
  Switch to a specific session by ID.

- `/current`
  Show the active session for the current bot and chat.

- `/commit <git commands>`
  Run validated git commit-related commands inside the active session project. The app splits chained input such as `git add ... && git commit ...`, executes only allowed `git` commands, and ignores non-git segments instead of shelling the raw message.

- `/push`
  Push `origin <branch>` for the current active session. The branch comes from the active session record, or from the current repository branch if the session does not have one stored.

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
- branch name
- provider
- timestamps
- active session selection for that bot/chat scope

## 🌿 Branch Workflow

If the selected project is a Git repository, `/project` reports the current branch and reminds you that:

- you can keep working on the current branch
- or create a dedicated work branch with `/branch`

When you run `/branch`, the app:

- requires `/project` to be set first
- detects the default branch if you do not specify one
- runs `git fetch origin`
- checks out the base branch
- runs `git pull --ff-only origin <base-branch>`
- creates and switches to the new branch

The chosen branch is stored with the session, so switching sessions restores the expected branch before the agent continues work.

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
