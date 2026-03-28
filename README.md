# Coding Agent Telegram 🚀

Control your local AI coding agent from anywhere with Telegram.

- No terminal needed
- No heavy frameworks
- Works with locally installed Codex/Copilot CLI agents

→ Setup with one-liner: 
```
curl -fsSL https://raw.githubusercontent.com/daocha/coding-agent-telegram/main/install.sh | bash
```

## ✨ Why Use It

- Control local Codex CLI and Copilot CLI from Telegram
- Continue the same session between terminal and Telegram with `/switch`
- Review agent answers and changed files in Telegram
- Queue follow-up questions while the agent is still working
- Support multiple telegram bots
- Accept Text and Image input

## Seamless Device/Session Switching

Start a session on Telegram, later on you can still continue the session Codex/Copilot CLI session on your computer, and switch back again without hassle.

- Use `/switch` in Telegram to continue a local Codex/Copilot CLI session
- Support historical sessions

## 🛠️ Typical Local Flow
Run
```bash
coding-agent-telegram #or run ./startup.sh
```

Then in Telegram:

```text
/project my-project
/new
Fix the failing API test in the current project
```

## 🔐 Security

- Private chat allowlist with `ALLOWED_CHAT_IDS`
- One active agent per project to reduce conflicting writes
- Sensitive file diffs are hidden
- API keys, tokens, `.env` values, certificates, SSH keys, and similar secret-like output are redacted before sending back to Telegram
- Runtime app data stays under `~/.coding-agent-telegram`
- Existing folders can require trust before mutating git operations
- Server makes `NO hidden external call`. Everything is under your control.

## ✅ Requirements

Before starting the server, make sure you have:

- Python 3.9 or newer
- Telegram bot token created from _@BotFather_
- Your Telegram chat ID
- Codex CLI and/or Copilot CLI installed locally
- [Codex CLI install](https://developers.openai.com/codex/cli) / [Copilot CLI install](https://github.com/features/copilot/cli)

## 🚀 Quick Start

### Option A: Start with a one-line bootstrap script

```bash
curl -fsSL https://raw.githubusercontent.com/daocha/coding-agent-telegram/main/install.sh | bash
```

### Option B: Install from PyPI with `pip`

```bash
pip install coding-agent-telegram
coding-agent-telegram
```

### Option C: Run from a cloned repository

```bash
git clone https://github.com/daocha/coding-agent-telegram
cd coding-agent-telegram
./startup.sh
```

### Start Bot Server
##### On first run, the app creates the env file, tells you what to fill in.
##### After updating the environment file then run:

```bash
# if you follow Option A or Option B, then run
coding-agent-telegram

# if you follow Option C, then run this again
./startup.sh
```

## 🔑 Telegram Setup

### Get a Bot Token

1. Open Telegram and start a chat with `@BotFather`.
2. Send `/newbot`.
3. Follow the prompts to choose:
   - a display name
   - a bot username ending in `bot`
4. BotFather will return an HTTP API token.
5. Put that token into `TELEGRAM_BOT_TOKENS` in your `~/.coding-agent-telegram/.env_coding_agent_telegram`.

### Get Your Chat ID

The most reliable way is to use Telegram's `getUpdates` API with your own bot token.

1. Start a chat with your bot and send it a message such as `/start`.
2. Open this URL in your browser, replacing `<BOT_TOKEN>`:

```text
https://api.telegram.org/bot<BOT_TOKEN>/getUpdates
```

3. Find the `chat` object in the JSON response.
4. Copy the numeric `id` field from that object.
5. Put that value into `ALLOWED_CHAT_IDS` in your `~/.coding-agent-telegram/.env_coding_agent_telegram`

Notes:

- For private chats, the chat ID is usually a positive integer.
- If `getUpdates` returns an empty result, send another message to the bot and try again.

## 📨 Supported Message Types

The bot currently accepts:

- Text messages
- photos
- Codex and Copilot currently supports text and image only, video is not supported.

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

## ⚙️ Environment Variables

Main env file path:

- `CODING_AGENT_TELEGRAM_ENV_FILE` if you explicitly set it
- otherwise `~/.coding-agent-telegram/.env_coding_agent_telegram`
- or `./.env_coding_agent_telegram` if that local file already exists

Required:

- `WORKSPACE_ROOT`
- `TELEGRAM_BOT_TOKENS`
- `ALLOWED_CHAT_IDS`

Common settings:

- `APP_LOCALE`
  Default: `en`
  Supported: `en`, `de`, `fr`, `ja`, `ko`, `nl`, `th`, `vi`, `zh-CN`, `zh-HK`, `zh-TW`

- `DEFAULT_AGENT_PROVIDER`
  `codex` or `copilot`

- `CODEX_BIN`
  Default: `codex`

- `COPILOT_BIN`
  Default: `copilot`

- `CODEX_MODEL`
- `COPILOT_MODEL`

- `CODEX_APPROVAL_POLICY`
  Default: `never`

- `CODEX_SANDBOX_MODE`
  Default: `workspace-write`

- `CODEX_SKIP_GIT_REPO_CHECK`

- `ENABLE_COMMIT_COMMAND`
  Default: `false`

- `AGENT_HARD_TIMEOUT_SECONDS`
  Default: `0`

- `SNAPSHOT_TEXT_FILE_MAX_BYTES`
  Default: `200000`

- `ENABLE_SENSITIVE_DIFF_FILTER`
- `ENABLE_SECRET_SCRUB_FILTER`

State and logs:

- `~/.coding-agent-telegram/state.json`
- `~/.coding-agent-telegram/state.json.bak`
- `~/.coding-agent-telegram/logs`

Model references:

- OpenAI Codex models: `https://developers.openai.com/codex/models`
- GitHub Copilot supported models: `https://docs.github.com/en/copilot/reference/ai-models/supported-models`

Example:

```env
APP_LOCALE=en
WORKSPACE_ROOT=~/git
TELEGRAM_BOT_TOKENS=bot_token_one
ALLOWED_CHAT_IDS=123456789
DEFAULT_AGENT_PROVIDER=codex
CODEX_BIN=codex
COPILOT_BIN=copilot
CODEX_APPROVAL_POLICY=never
CODEX_SANDBOX_MODE=workspace-write
ENABLE_SENSITIVE_DIFF_FILTER=true
ENABLE_SECRET_SCRUB_FILTER=true
```

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

## 📌 Notes

- This project is designed for users running the agents locally on their own machine.
- The Telegram bot is a control surface, not the execution environment itself.
- If you run multiple bots, all of them can be managed by one server process.
