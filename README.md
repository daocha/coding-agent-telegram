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

- creates `~/.coding-agent-telegram/.env_coding_agent_telegram` from `src/coding_agent_telegram/resources/.env.example` if neither that file nor `./.env_coding_agent_telegram` exists
- creates the state files if missing
- creates `.venv` if missing
- installs the package into the virtual environment
- starts the Telegram bot server

#### 3. Update The Env File

On first run, update the required fields in the env file the app is using:

- `CODING_AGENT_TELEGRAM_ENV_FILE` if you explicitly set it
- `~/.coding-agent-telegram/.env_coding_agent_telegram` by default
- or `./.env_coding_agent_telegram` if that local file already exists

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

- the command creates `~/.coding-agent-telegram/.env_coding_agent_telegram` if neither that file nor `./.env_coding_agent_telegram` exists
- it tells you which required fields to update
- after updating the env file, run `coding-agent-telegram` again

Recommended flow:

```bash
mkdir -p ~/my-coding-agent-bot
cd ~/my-coding-agent-bot
pip install coding-agent-telegram
coding-agent-telegram
```

Then update the env file the app created or selected and run:

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

These are the main fields in the env file the app uses:

- `CODING_AGENT_TELEGRAM_ENV_FILE` if you explicitly set it
- `~/.coding-agent-telegram/.env_coding_agent_telegram` by default
- or `./.env_coding_agent_telegram` if that local file already exists

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

- Session state files are stored at:
  - `~/.coding-agent-telegram/state.json`
  - `~/.coding-agent-telegram/state.json.bak`
  Backward compatibility: if `./state.json` or `./state.json.bak` already exists and the home file does not, the app keeps using the local file.

- `LOG_LEVEL`
  Python app log level.
  Default: `INFO`

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

- `ENABLE_COMMIT_COMMAND`
  If `true`, enable the `/commit` Telegram command.
  Default: `false`

- `AGENT_HARD_TIMEOUT_SECONDS`
  Hard time limit in seconds for a single agent run.
  When the agent subprocess is still running after this many seconds, the bot sends a timeout message and terminates the process.
  Set to `0` (the default) to disable the limit entirely.
  Disabling is recommended for Copilot, which can legitimately take over an hour on complex tasks.
  Set a value (e.g. `600`) only when you want a hard cap — typically for shorter, bounded Codex jobs.
  Default: `0` (disabled)

### Telegram Behavior

- `SNAPSHOT_TEXT_FILE_MAX_BYTES`
  Maximum file size the bot will read as text when building the before/after snapshot for per-run diffs.
  Default: `200000` bytes, about 200 KB

- `MAX_TELEGRAM_MESSAGE_LENGTH`
  Max message size used before the app splits responses.

- `ENABLE_SENSITIVE_DIFF_FILTER`
  Hide diffs for sensitive paths.

### Example Env Snippet

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

ENABLE_COMMIT_COMMAND=false

SNAPSHOT_TEXT_FILE_MAX_BYTES=200000
LOG_LEVEL=INFO
```

## 🤖 Telegram Commands

- `/project <project_folder>`
  Set the current project folder. If the folder does not exist, the app creates it and marks it trusted. If the folder already exists and is still untrusted, the app reminds you to trust it explicitly.

- `/provider`
  Choose the provider for new sessions. Provider selection is stored per bot/chat and reused until you change it.

- `/new [session_name]`
  Create a new session for the current project. If you omit the name, the bot uses the real session ID as the session name.
  If provider, project, or branch is still missing, the bot prompts you for the missing prerequisite instead of failing immediately.

- `/branch <new_branch>`
  Prepare or switch a branch for the current project. The bot asks you to choose the source explicitly:
  - if `<new_branch>` already exists locally or on origin, the bot treats that same branch as the source candidate
  - otherwise the bot uses the repository default branch as the source candidate

- `/branch <origin_branch> <new_branch>`
  Prepare or switch a branch using `<origin_branch>` as the source candidate.

For both forms, the bot then offers the source choices that actually exist:

- `local/<branch>`
- `origin/<branch>`

If only one of those exists, only that option is shown. If neither exists, the bot tells you the branch source is missing.

- `/switch`
  Show the latest sessions, newest first. The list mixes bot-managed sessions and native Codex/Copilot CLI sessions for the current project.

- `/switch page <number>`
  Show another page of stored sessions.

- `/switch <session_id>`
  Switch to a specific session by ID. If you select a native CLI session, the bot imports it into its own state and continues from there.

- `/current`
  Show the active session for the current bot and chat.

- `/abort`
  Abort the current agent run for the current project. If that run was processing while other queued questions were waiting, the bot asks whether to continue with the remaining queued questions.

- `/commit <git commands>`
  Run validated git commit-related commands inside the active session project. This command is available only when `ENABLE_COMMIT_COMMAND=true`. The app splits chained input such as `git add ... && git commit ...`, executes only allowed `git` commands, and ignores non-git segments instead of shelling the raw message. Mutating git commands such as `add`, `restore`, and `rm` require the project to be trusted.

- `/push`
  Push `origin <branch>` for the current active session. The bot asks for confirmation before actually pushing. The branch comes from the active session record, or from the current repository branch if the session does not have one stored.

## 🧠 Session Management

Sessions are scoped by:

- Telegram bot
- Telegram chat

That means the same Telegram account can use multiple bots without mixing sessions.

Example:

- Bot A + your chat -> backend work
- Bot B + your chat -> frontend work
- Bot C + your chat -> infra work

The active session is also tied to:

- project folder
- provider
- branch name when available

Each session stores:

- session name
- project folder
- branch name
- provider
- timestamps
- active session selection for that bot/chat scope

### Switching between Telegram and native CLI

`/switch` is designed to let you move between:

- sessions created from Telegram
- sessions created directly in Codex CLI or Copilot CLI

For the current project, the bot lists both kinds together, sorts them by newest activity first, and marks the source with a small icon:

- `🤖` Bot managed session
- `💻` native CLI session

If you select a native CLI session, the bot imports it into `state.json` and then resumes it like a normal Telegram-managed session. This is what makes cross-device or cross-entry-point continuation possible.

### Workspace concurrency lock

Only one agent run can be active per **project folder** at a time — regardless of which chat ID or Telegram bot triggers it.

This is different from “an agent is still processing the current question”:

- **project is busy** means the workspace already has one live agent run
- **agent is busy** means that one live run is still working on the current request

The bot enforces one active run per project on purpose so two agents do not write to the same workspace at the same time. That avoids conflicting edits and reduces the chance of data corruption.

If a message arrives while an agent is already running on the same project, the bot immediately replies:

> ⏳ An agent is already running on project '…'. Please wait for it to finish.

The lock is held in memory (not on disk), so it is automatically released when the agent finishes, errors out, or if the server restarts. There are no stale lock files to clean up after a crash.

### Queued questions

If the current project already has one live agent run, later text messages are not rejected. They are queued instead:

- the new question is appended to a queued-questions file on disk
- the current agent keeps working on the earlier request
- when that run finishes normally, the bot automatically starts processing the queued questions next

If the current run is aborted and there are queued questions waiting, the bot does **not** auto-continue. It asks whether you want to continue processing the remaining queued questions.

## ⚠  Diff (file changes)

_During each agent run, the bot also takes a lightweight before/after project snapshot so it can summarize changed files and send diffs back to Telegram. This snapshot is taken by the bot app itself, not by Codex or Copilot._

**Snapshot notes:**

- the app walks the project directory before and after the run
- for normal text files, the app prefers the per-run snapshot diff rather than a git-head diff
- common dependency, cache, and runtime directories are also skipped
- binary files and files larger than `SNAPSHOT_TEXT_FILE_MAX_BYTES` are not loaded as text
- for huge projects, this extra scan can add noticeable I/O and memory overhead
- if the snapshot cannot represent a file as text, the app falls back to git diff when possible
- for large or non-text files, the diff may still be omitted and replaced with a short unavailable message

Snapshot exclusion rules live in package resource files:

- `src/coding_agent_telegram/resources/snapshot_excluded_dir_names.txt`
- `src/coding_agent_telegram/resources/snapshot_excluded_dir_globs.txt`
- `src/coding_agent_telegram/resources/snapshot_excluded_file_globs.txt`

You can override those defaults in the env file without editing the installed package:

- `SNAPSHOT_INCLUDE_PATH_GLOBS`
  Force-include matching paths in diffs.
  Example: `.github/*,.profile.test,.profile.prod`

- `SNAPSHOT_EXCLUDE_PATH_GLOBS`
  Add extra diff exclusions on top of the packaged defaults.
  Example: `.*,personal/*,sensitive*.txt`
  Note: `.*` matches hidden paths, including files inside hidden directories.

If both include and exclude rules match, the include rule wins.

## 🌿 Branch Behavior

The bot treats project and branch as a bundle.

- choosing a project does not silently choose an unrelated branch
- if branch input is needed, the bot asks you to pick it
- when branch information is printed in session-related messages, project and branch are shown together

When you create or change a branch, the bot guides you through the source explicitly:

- `local/<branch>` means use the local branch as the source
- `origin/<branch>` means update from the remote branch first and then switch

If the bot sees that the stored session branch and the repository's current branch do not match, it does not blindly continue. It asks which branch you want to use:

- keep the stored session branch
- keep the current repository branch

If your preferred source branch is missing, the bot offers fallback source choices based on the default branch and current branch instead of leaving you at a raw git error.

## 🔐 Git Trust Behavior

- Existing folders follow `CODEX_SKIP_GIT_REPO_CHECK`
- Folders created through `/project <name>` are marked as trusted by this app
- Existing folders selected through `/project <name>` remain untrusted until you confirm trust in the Telegram prompt
- That means newly created project folders can be used immediately
- `/commit` can be disabled entirely with `ENABLE_COMMIT_COMMAND`
- Mutating `/commit` operations are allowed only for trusted projects

## 🪵 Logs

Logs are written to **both stdout and a rotating log file** under:

- `~/.coding-agent-telegram/logs`

Main log file:

- `coding-agent-telegram.log` (rotated at 10 MB, 3 backups kept)

> **Note:** Because messages go to both stdout and the log file, watching the terminal
> **and** tailing the log file at the same time (e.g. `tail -f logs/coding-agent-telegram.log`)
> will make each message appear twice — once from each sink. This is expected behavior.
> View one or the other, not both simultaneously.

Typical logged events:

- bot startup and polling start
- project selection
- session creation
- session switching
- active session reporting
- normal run execution (includes an audit log line with the truncated prompt)
- session replacement after resume failure
- warnings and runtime errors

## 🗂️ Project Structure

- `src/coding_agent_telegram/`
  Main application code

- `tests/`
  Test suite

- `startup.sh`
  Local bootstrap and startup entrypoint

- `src/coding_agent_telegram/resources/.env.example`
  Canonical environment template used by both repo startup and packaged installs

- `pyproject.toml`
  Packaging and dependency configuration

## 📦 Release Versioning

Package versions are derived from Git tags.

- TestPyPI/testing: `v2026.3.26.dev1`
- PyPI prerelease: `v2026.3.26rc1`
- PyPI stable: `v2026.3.26`

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
