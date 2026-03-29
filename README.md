<div align="center">
  <img width="600" alt="Coding Agent Telegram" src="https://github.com/user-attachments/assets/aca106f8-0d64-40e9-94d9-2542da5dfde9" />
  <h1>Coding Agent Telegram 🚀</h1>
  <p>
    <a href="https://github.com/daocha/coding-agent-telegram/blob/main/README.md">English</a> |
    <a href="https://github.com/daocha/coding-agent-telegram/blob/main/README.de.md">Deutsch</a> |
    <a href="https://github.com/daocha/coding-agent-telegram/blob/main/README.fr.md">Français</a> |
    <a href="https://github.com/daocha/coding-agent-telegram/blob/main/README.ja.md">日本語</a> |
    <a href="https://github.com/daocha/coding-agent-telegram/blob/main/README.ko.md">한국어</a> |
    <a href="https://github.com/daocha/coding-agent-telegram/blob/main/README.nl.md">Nederlands</a> |
    <a href="https://github.com/daocha/coding-agent-telegram/blob/main/README.th.md">ไทย</a> |
    <a href="https://github.com/daocha/coding-agent-telegram/blob/main/README.vi.md">Tiếng Việt</a> |
    <a href="https://github.com/daocha/coding-agent-telegram/blob/main/README.zh-CN.md">简体中文</a> |
    <a href="https://github.com/daocha/coding-agent-telegram/blob/main/README.zh-HK.md">繁體中文（香港）</a> |
    <a href="https://github.com/daocha/coding-agent-telegram/blob/main/README.zh-TW.md">繁體中文（台灣）</a>
  </p>
  <p><strong>Lightweight, Multi Bots, Multi sessions, Multi-tasking, 24/7 AI Coding Agent</strong></p>
  <p>Control your local AI coding agent from anywhere with Telegram.</p>
  <p>
    <img src="https://img.shields.io/badge/stability-experimental-orange.svg" alt="Experimental" />
    <a href="https://opensource.org/licenses/MIT">
      <img src="https://img.shields.io/badge/License-MIT-blue.svg" alt="MIT License" />
    </a>
    <a href="http://github.com/daocha/coding-agent-telegram/releases/latest">
      <img src="https://img.shields.io/github/v/release/daocha/coding-agent-telegram?label=Latest&color=green" alt="Latest Release" />
    </a>
    <img src="https://img.shields.io/badge/python-3.9+-blue" alt="Python 3.9+" />
  </p>
</div>

<table border="0">
   <tr>
   <td border="0">
   
   ## ✨ Why Use It
   - ✅ Lightweight: no heavy frameworks, full transparency
   - ✅ Multi-bot: multiple chats, multiple sessions
   - ✅ Use Telegram to control Codex / Copilot CLI
   - ✅ Easily review files changed by agent in code block
   - ✅ Queue follow-up messages while the agent is working
   - ✅ Accept Text and Image input

   ## 🔁 Seamless Device/Session Switching
   
   Start a session on Telegram, later on you can still continue the same Codex/Copilot CLI session on your computer, and switch back again without hassle.
   
   - Use `/switch` in Telegram to continue a local session
   - Support historical sessions

   ## 🛠️ Typical Local Flow
   ```bash
   coding-agent-telegram # or run ./startup.sh
   ```
   
   ##### In Telegram:
   
   ```text
   /project my-project
   /new
   Fix the failing API test in the current project
   ```
   
   </td>
   <td width="350" border="0">
   <img src="https://github.com/user-attachments/assets/cecb6de6-ecf0-4bf4-af70-b98071c68885" />
   </td>
   </tr>
</table>

→ Setup with one-liner: 
```
curl -fsSL https://raw.githubusercontent.com/daocha/coding-agent-telegram/main/install.sh | bash
```

<table>
   <tr>
   <td width="50%" valign="top">
      
   ## 🔐 Security
      
   - Private chat allowlist with `ALLOWED_CHAT_IDS`
   - One active agent per project to reduce conflicting writes
   - Sensitive file diffs are hidden
   - API keys, tokens, `.env` values, certificates, SSH keys, and similar secret-like output are redacted before sending back to Telegram
   - Runtime app data stays under `~/.coding-agent-telegram`
   - Existing folders can require trust before mutating git operations
   - Server makes `NO hidden external call`. Everything is under your control.      
   </td>
   <td width="50%" valign="top">
      
   ## ✅ Requirements

   Before starting the server, make sure you have:
   
   - Python 3.9 or newer
   - Telegram bot token created from _@BotFather_
   - Your Telegram chat ID
   - Codex CLI and/or Copilot CLI installed locally
   - [Codex CLI install](https://developers.openai.com/codex/cli)
   - [Copilot CLI install](https://github.com/features/copilot/cli)
   </td>
   </tr>
</table>

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

<table>
  <tr>
    <td width="250"><code>/provider</code></td>
    <td>Choose the provider for new sessions. The selection is stored per bot and chat until you change it.</td>
  </tr>
  <tr>
    <td width="250"><code>/project &lt;project_folder&gt;</code></td>
    <td>Set the current project folder. If the folder does not exist, the app creates it and marks it trusted. If it already exists and is still untrusted, the app asks you to trust it explicitly.</td>
  </tr>
  <tr>
    <td width="250"><code>/branch &lt;new_branch&gt;</code></td>
    <td>Prepare or switch a branch for the current project. If the branch already exists, the bot treats that branch as the source candidate. Otherwise it uses the repository default branch as the source candidate.</td>
  </tr>
  <tr>
    <td width="250"><code>/branch &lt;origin_branch&gt; &lt;new_branch&gt;</code></td>
    <td>Prepare or switch a branch using <code>&lt;origin_branch&gt;</code> as the source candidate. <br /> For both forms, the bot then offers the source choices that actually exist: <code>local/&lt;branch&gt;</code> <code>origin/&lt;branch&gt;</code> <br />If only one of those exists, only that option is shown. If neither exists, the bot tells you the branch source is missing.</td>
  </tr>
  <tr>
    <td width="250"><code>/current</code></td>
    <td>Show the active session for the current bot and chat.</td>
  </tr>
  <tr>
    <td width="250"><code>/new [session_name]</code></td>
    <td>Create a new session for the current project. If you omit the name, the bot uses the real session ID. If provider, project, or branch is missing, the bot guides you through the missing step.</td>
  </tr>
  <tr>
    <td width="250"><code>/switch</code></td>
    <td>Show the latest sessions, newest first. The list includes both bot-managed sessions and local Codex/Copilot CLI sessions for the current project.</td>
  </tr>
  <tr>
    <td width="250"><code>/switch page &lt;number&gt;</code></td>
    <td>Show another page of stored sessions.</td>
  </tr>
  <tr>
    <td width="250"><code>/switch &lt;session_id&gt;</code></td>
    <td>Switch to a specific session by ID. If you choose a local CLI session, the bot imports it and continues from there.</td>
  </tr>
  <tr>
    <td width="250"><code>/compact</code></td>
    <td>Create a fresh compacted session from the active session and switch to it.</td>
  </tr>
  <tr>
    <td width="250"><code>/commit &lt;git commands&gt;</code></td>
    <td>Run validated git commit-related commands inside the active session project. Available only when <code>ENABLE_COMMIT_COMMAND=true</code>. Mutating git commands require a trusted project.</td>
  </tr>
  <tr>
    <td width="250"><code>/push</code></td>
    <td>Push <code>origin &lt;branch&gt;</code> for the current active session. The bot asks for confirmation before pushing.</td>
  </tr>
  <tr>
    <td width="250"><code>/abort</code></td>
    <td>Abort the current agent run for the current project. If queued questions are waiting, the bot asks whether to continue them.</td>
  </tr>
</table>
<h2>⚙️ Environment Variables</h2>

<h3>Main env file path:</h3>

<table>
  <tr>
    <td><code>CODING_AGENT_TELEGRAM_ENV_FILE</code></td>
    <td>Use this if you want to point the app to a specific env file.</td>
  </tr>
  <tr>
    <td><code>~/.coding-agent-telegram/.env_coding_agent_telegram</code></td>
    <td>Default env file location.</td>
  </tr>
  <tr>
    <td><code>./.env_coding_agent_telegram</code></td>
    <td>Used only if this local file already exists.</td>
  </tr>
</table>

<h3>Required</h3>

<table>
  <tr>
    <td width="250"><code>WORKSPACE_ROOT</code></td>
    <td>Parent folder that contains your project directories.</td>
  </tr>
  <tr>
    <td><code>TELEGRAM_BOT_TOKENS</code></td>
    <td>Comma-separated Telegram bot tokens.</td>
  </tr>
  <tr>
    <td><code>ALLOWED_CHAT_IDS</code></td>
    <td>Comma-separated Telegram private chat IDs allowed to use the bot.</td>
  </tr>
</table>

<h3>Common Settings</h3>

<table>
  <tr>
    <td width="250"><code>APP_LOCALE</code></td>
    <td>UI locale for shared bot messages and command descriptions. Supported values: <code>en</code>, <code>de</code>, <code>fr</code>, <code>ja</code>, <code>ko</code>, <code>nl</code>, <code>th</code>, <code>vi</code>, <code>zh-CN</code>, <code>zh-HK</code>, <code>zh-TW</code>.</td>
  </tr>
  <tr>
    <td><code>CODEX_BIN</code></td>
    <td>Command used to launch Codex CLI. Default: <code>codex</code>.</td>
  </tr>
  <tr>
    <td><code>COPILOT_BIN</code></td>
    <td>Command used to launch Copilot CLI. Default: <code>copilot</code>.</td>
  </tr>
  <tr>
    <td><code>CODEX_MODEL</code></td>
    <td>Optional Codex model override.
    Leave empty to use the Codex CLI default model.
    Example: <code>gpt-5.4</code>
    <a href="https://developers.openai.com/codex/models" target="_blank">OpenAI Codex/OpenAI models</a>
    </td>
  </tr>
  <tr>
    <td><code>COPILOT_MODEL</code></td>
    <td>Optional Copilot model override.
    Leave empty to use the Copilot CLI default model.
    Examples: <code>gpt-5.4</code>, <code>claude-sonnet-4.6</code>
    <a href="https://docs.github.com/en/copilot/reference/ai-models/supported-models" target="_blank">GitHub Copilot supported models</a>
    </td>
  </tr>
  <tr>
    <td><code>CODEX_APPROVAL_POLICY</code></td>
    <td>Approval mode passed to Codex. Default: <code>never</code>.</td>
  </tr>
  <tr>
    <td><code>CODEX_SANDBOX_MODE</code></td>
    <td>Sandbox mode passed to Codex. Default: <code>workspace-write</code>.</td>
  </tr>
  <tr>
    <td><code>CODEX_SKIP_GIT_REPO_CHECK</code></td>
    <td>If enabled, always bypass Codex trusted-repo checks.</td>
  </tr>
  <tr>
    <td><code>ENABLE_COMMIT_COMMAND</code></td>
    <td>Enable the <code>/commit</code> Telegram command. Default: <code>false</code>.</td>
  </tr>
  <tr>
    <td><code>AGENT_HARD_TIMEOUT_SECONDS</code></td>
    <td>Hard timeout for a single agent run. Default: <code>0</code> (disabled).</td>
  </tr>
  <tr>
    <td><code>SNAPSHOT_TEXT_FILE_MAX_BYTES</code></td>
    <td>Maximum file size the bot will read as text when building the before/after snapshot for per-run diffs. Default: <code>200000</code>.</td>
  </tr>
  <tr>
    <td><code>MAX_TELEGRAM_MESSAGE_LENGTH</code></td>
    <td>Max message size used before the app splits responses. Default: <code>3000</code></td>
  </tr>
  <tr>
    <td><code>ENABLE_SENSITIVE_DIFF_FILTER</code></td>
    <td>Hide diffs for sensitive files. Default: <code>true></code></td>
  </tr>
  <tr>
    <td><code>ENABLE_SECRET_SCRUB_FILTER</code></td>
    <td>Redact tokens, keys, <code>.env</code> values, certificates, and similar secret-like output before sending it to Telegram. Default <code>true</code> (Strongly recommended)</td>
  </tr>
  <tr>
    <td><code>SNAPSHOT_INCLUDE_PATH_GLOBS</code></td>
    <td>Force-include matching paths in diffs. Example: <code>.github/*,.profile.test,.profile.prod</code></td>
  </tr>
  <tr>
    <td><code>SNAPSHOT_EXCLUDE_PATH_GLOBS</code></td>
    <td>Add extra diff exclusions on top of the packaged defaults.
  Example: <code>.*,personal/*,sensitive*.txt</code>
  Note: <code>.*</code> matches hidden paths, including files inside hidden directories.</td>
  </tr>
</table>

<h3>State and Logs</h3>

<table>
  <tr>
    <td><code>~/.coding-agent-telegram/state.json</code></td>
    <td>Main session state file.</td>
  </tr>
  <tr>
    <td><code>~/.coding-agent-telegram/state.json.bak</code></td>
    <td>Backup state file.</td>
  </tr>
  <tr>
    <td><code>~/.coding-agent-telegram/logs</code></td>
    <td>Log directory.</td>
  </tr>
</table>

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

<details>
<summary><b>Each session stores:</b></summary>

- session name
- project folder
- branch name
- provider
- timestamps
- active session selection for that bot/chat scope
</details>

### 🔓 Workspace concurrency lock

Only one agent run can be active per **project folder** at a time — regardless of which chat ID or Telegram bot triggers it.

This is different from “an agent is still processing the current question”:

- **project is busy** means the workspace already has one live agent run
- **agent is busy** means that one live run is still working on the current request

The bot enforces one active run per project on purpose so two agents do not write to the same workspace at the same time. That avoids conflicting edits and reduces the chance of data corruption.

If a message arrives while an agent is already running on the same project, the bot immediately replies:

> ⏳ An agent is already running on project '…'. Please wait for it to finish.

The lock is held in memory (not on disk), so it is automatically released when the agent finishes, errors out, or if the server restarts. There are no stale lock files to clean up after a crash.

### 💬 Queued questions

If the current project already has one live agent run, later text messages are not rejected. They are queued instead:

- the new question is appended to a queued-questions file on disk
- the current agent keeps working on the earlier request
- when that run finishes normally, the bot automatically starts processing the queued questions next

If the current run is aborted and there are queued questions waiting, the bot does **not** auto-continue. It asks whether you want to continue processing the remaining queued questions. You can choose to batch process or one-by-one.

## ⚠️ Diff (file changes)

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

- `~/.coding-agent-telegram/logs` (rotated at 10 MB, 3 backups kept)

> **Note:** Because messages go to both stdout and the log file, watching the terminal
> **and** tailing the log file at the same time (e.g. `tail -f ~/.coding-agent-telegram/logs/coding-agent-telegram.log`)
> will make each message appear twice — once from each sink. This is expected behavior.
> View one or the other, not both simultaneously.

<details>
<summary><b>Typical logged events</b></summary>

- bot startup and polling start
- project selection
- session creation
- session switching
- active session reporting
- normal run execution (includes an audit log line with the truncated prompt)
- session replacement after resume failure
- warnings and runtime errors
</details>

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
