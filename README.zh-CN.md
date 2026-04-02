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
  <p><strong>轻量、多 Bot、多会话、多任务、7x24 AI Coding Agent</strong></p>
  <p>通过 Telegram 随时随地控制你本机上的 AI Coding Agent。</p>
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

   ## ✨ 为什么使用它
  - ✅ 轻量：没有重型框架，行为清晰可见
  - ✅ 多 Bot：支持多个聊天、多个会话
  - ✅ 使用 Telegram 控制 Codex / Copilot CLI
  - ✅ 可以在代码块中轻松查看 agent 回复和改动文件
  - ✅ agent 工作时也能继续排队后续问题
  - ✅ 支持 ✏️ 文本、🌄 图片和 🎙️ 语音消息

   ## 🔁 设备与会话无缝切换

  你可以先在 Telegram 中开启一个会话，之后在电脑上继续同一个 Codex/Copilot CLI 会话，不需要折腾。使用 `/switch` 也可以在 Telegram 和命令行之间无缝切换。
  
  - 使用 `/switch` 继续本地会话
  - 也支持历史会话

   ## 🛠️ 典型本地流程
   ```bash
   coding-agent-telegram # 或运行 ./startup.sh
   ```

   ##### 在 Telegram 中：

   ```text
   /project my-project
   /new
   Fix the failing API test in the current project
   ```

   </td>
   <td width="350" border="0">
   <img src="https://github.com/user-attachments/assets/54e8745b-a0d4-48ff-b0d8-178198d00a3d" />
   </td>
   </tr>
</table>

→ 一行命令安装： 
```
curl -fsSL https://raw.githubusercontent.com/daocha/coding-agent-telegram/main/install.sh | bash
```

<table>
   <tr>
   <td width="65%" valign="top">

   ## 🔐 安全性

- 通过 `ALLOWED_CHAT_IDS` 对私聊进行白名单控制
- 每个项目同一时间只允许一个活动 agent，减少冲突写入
- 敏感文件的 diff 会被隐藏
- API keys、tokens、`.env` 值、证书、SSH keys 以及类似秘密输出在发回 Telegram 前会被脱敏
- 运行时应用数据保存在 `~/.coding-agent-telegram` 下
- 现有文件夹在执行会修改内容的 Git 操作前，可能需要先确认 trust
- 服务器不会发出隐藏的外部请求，一切都由你掌控。
- 与 Codex Sandbox mode 配合良好，你不需要授予 `danger-full-access`
   </td>
   <td width="35%" valign="top">

   ## ✅ 运行要求

启动服务器前，请确保你已准备好：

- Python 3.9 或更高版本
- 通过 _@BotFather_ 创建的 Telegram bot token
- 你的 Telegram chat ID
- 已在本地安装 Codex CLI 和/或 Copilot CLI
- [安装 Codex CLI](https://developers.openai.com/codex/cli)
- [安装 Copilot CLI](https://github.com/features/copilot/cli)
- [可选] Whisper、ffmpeg
   </td>
   </tr>
</table>

## 🦞 如果我已经有 Openclaw，为什么还需要它？
Openclaw 功能非常完整，也内置了名为 Pi-Agent 的 agent loop，适合更丰富、更广泛的使用场景。我自己也很喜欢 Openclaw，以前也用它来写代码。不过对纯 coding 来说，它并不总是最佳选择，因为内置的大型 system prompt 和额外 context 有时会让模型更容易分心。Claude Code / Codex / Copilot 在 coding 场景下通常仍然更高效、更准确、更不容易跑偏，也更直接。这个项目刻意保持简单，只集成 Codex / Copilot CLI，所以你是在直接把任务交给 Codex / Copilot。

## 🚀 快速开始

### 方案 A：一行启动脚本
```bash
curl -fsSL https://raw.githubusercontent.com/daocha/coding-agent-telegram/main/install.sh | bash
```

### 方案 B：通过 `pip` 从 PyPI 安装
```bash
pip install coding-agent-telegram
coding-agent-telegram
```

### 方案 C：从克隆的仓库运行
```bash
git clone https://github.com/daocha/coding-agent-telegram
cd coding-agent-telegram
./startup.sh
```

### 🌐 启动 Bot Server
##### 首次运行时，应用会创建 env 文件，并告诉你需要填写哪些字段。
##### 更新 env 文件后，再次运行：
```bash
# 如果你使用方案 A 或方案 B，则运行
coding-agent-telegram

# 如果你使用方案 C，则再次运行此命令
./startup.sh
```

## 🎙️ [可选] 语音转文字功能：准备本地 OpenAI-Whisper 依赖

这部分用于可选启用 Telegram 语音消息的本地 Whisper 语音转文字功能。音频文件最大限制为 `20 MB`。

```bash
# 如果你是通过 pip 安装
coding-agent-telegram-stt-install

# 如果你是从克隆的仓库运行
./install-stt.sh
```

推荐的 env 设置：

```text
ENABLE_OPENAI_WHISPER_SPEECH_TO_TEXT=true
OPENAI_WHISPER_MODEL=base
OPENAI_WHISPER_TIMEOUT_SECONDS=120
```

说明：

- Whisper 会在首次使用时自动把所选模型下载到 `~/.cache/whisper`。
- 如果你选择 `OPENAI_WHISPER_MODEL=turbo`，第一次语音转写更容易在 `large-v3-turbo.pt` 仍在下载时触发超时。
- 语音消息转写完成后，bot 会先把识别出的文本回传到 Telegram，再把它交给 agent。这样更方便排查识别错误。

## 🔑 Telegram 设置

### 获取 Bot Token

1. 打开 Telegram，并与 `@BotFather` 开始聊天。
2. 发送 `/newbot`。
3. 按提示设置：
   - 显示名称
   - 以 `bot` 结尾的 bot 用户名
4. BotFather 会返回一个 HTTP API token。
5. 把这个 token 填入 `~/.coding-agent-telegram/.env_coding_agent_telegram` 里的 `TELEGRAM_BOT_TOKENS`。

### 获取 Chat ID

最可靠的方法是使用你自己的 bot token 调用 Telegram 的 `getUpdates` API。

1. 与你的 bot 开始聊天，并发送一条消息，例如 `/start`。
2. 在浏览器中打开以下 URL，并替换 `<BOT_TOKEN>`：

```text
https://api.telegram.org/bot<BOT_TOKEN>/getUpdates
```

3. 在 JSON 响应中找到 `chat` 对象。
4. 复制其中数值型的 `id` 字段。
5. 将该值填入 `~/.coding-agent-telegram/.env_coding_agent_telegram` 中的 `ALLOWED_CHAT_IDS`。

说明：

- 私聊的 chat ID 通常是正整数。
- 如果 `getUpdates` 返回空结果，请先再给 bot 发一条消息，然后重试。

## 📨 支持的消息类型

bot 当前接受：

- 文本消息
- 图片
- 当 `ENABLE_OPENAI_WHISPER_SPEECH_TO_TEXT=true` 且已安装本地 Whisper 依赖时的语音消息和音频文件
- Codex 和 Copilot 当前只支持文本和图片，不支持视频

## 🤖 Telegram 命令

<table>
  <tr>
    <td width="332"><code>/provider</code></td>
    <td>为新会话选择提供方。该选择会按 bot 和 chat 保存，直到你手动修改。</td>
  </tr>
  <tr>
    <td width="332"><code>/project &lt;project_folder&gt;</code></td>
    <td>设置当前 project 文件夹。如果文件夹不存在，应用会创建并标记为 trusted；如果已存在但仍是 untrusted，应用会明确要求确认 trust。</td>
  </tr>
  <tr>
    <td width="332"><code>/branch &lt;new_branch&gt;</code></td>
    <td>为当前 project 准备或切换 branch。如果 branch 已存在，bot 会把它当作 source candidate；否则会使用 repository 的 default branch 作为 source candidate。</td>
  </tr>
  <tr>
    <td width="332"><code>/branch &lt;origin_branch&gt; &lt;new_branch&gt;</code></td>
    <td>使用 <code>&lt;origin_branch&gt;</code> 作为 source candidate 来准备或切换 branch。无论哪种形式，bot 之后只会提供实际存在的 source choices：<code>local/&lt;branch&gt;</code> 和 <code>origin/&lt;branch&gt;</code>。如果只存在其中一个，就只显示那个；如果两个都不存在，bot 会提示缺少 branch source。</td>
  </tr>
  <tr>
    <td width="332"><code>/current</code></td>
    <td>显示当前 bot 和 chat 的活动会话。</td>
  </tr>
  <tr>
    <td width="332"><code>/new [session_name]</code></td>
    <td>为当前项目创建新会话。如果省略名称，bot 会使用真实的会话 ID。若缺少提供方、项目或 branch，bot 会引导你完成缺失步骤。</td>
  </tr>
  <tr>
    <td width="332"><code>/switch</code></td>
    <td>显示最新的会话，按从新到旧排序。列表同时包含 bot 管理的会话和当前项目的本地 Codex/Copilot CLI 会话。</td>
  </tr>
  <tr>
    <td width="332"><code>/switch page &lt;number&gt;</code></td>
    <td>显示已保存会话的其他页。</td>
  </tr>
  <tr>
    <td width="332"><code>/switch &lt;session_id&gt;</code></td>
    <td>通过 ID 切换到指定会话。如果你选择本地 CLI 会话，bot 会把它导入状态并从那里继续。</td>
  </tr>
  <tr>
    <td width="332"><code>/compact</code></td>
    <td>从当前活动会话创建一个新的压缩会话，并切换到该会话。</td>
  </tr>
  <tr>
    <td width="332"><code>/commit &lt;git commands&gt;</code></td>
    <td>在活动会话的项目内执行已校验的 <code>git commit</code> 相关命令。仅当 <code>ENABLE_COMMIT_COMMAND=true</code> 时可用。会修改内容的 Git 命令要求项目已 trusted。</td>
  </tr>
  <tr>
    <td width="332"><code>/push</code></td>
    <td>为当前活动会话执行 <code>origin &lt;branch&gt;</code> push。push 前 bot 会要求确认。</td>
  </tr>
  <tr>
    <td width="332"><code>/abort</code></td>
    <td>中止当前 project 的 代理运行。如果还有 排队问题 在等待，bot 会询问是否继续处理。</td>
  </tr>
</table>

<h2>⚙️ 环境变量</h2>

<h3>主 env 文件路径：</h3>

<table>
  <tr>
    <td><code>CODING_AGENT_TELEGRAM_ENV_FILE</code></td>
    <td>如果你希望应用使用指定的 env 文件，请设置此项。</td>
  </tr>
  <tr>
    <td><code>~/.coding-agent-telegram/.env_coding_agent_telegram</code></td>
    <td>默认的 env 文件位置。</td>
  </tr>
  <tr>
    <td><code>./.env_coding_agent_telegram</code></td>
    <td>仅当这个本地文件已经存在时才会使用。</td>
  </tr>
</table>

<h3>必填</h3>

<table>
  <tr>
    <td width="332"><code>WORKSPACE_ROOT</code></td>
    <td>包含你的项目目录的父文件夹。</td>
  </tr>
  <tr>
    <td width="332"><code>TELEGRAM_BOT_TOKENS</code></td>
    <td>以逗号分隔的 Telegram bot token。</td>
  </tr>
  <tr>
    <td width="332"><code>ALLOWED_CHAT_IDS</code></td>
    <td>允许使用该 bot 的 Telegram 私聊 chat ID，使用逗号分隔。</td>
  </tr>
</table>

<h3>常用设置</h3>

<table>
  <tr>
    <td width="332"><code>APP_LOCALE</code></td>
    <td>共享 bot 消息和命令说明所使用的 UI 语言。支持值：<code>en</code>、<code>de</code>、<code>fr</code>、<code>ja</code>、<code>ko</code>、<code>nl</code>、<code>th</code>、<code>vi</code>、<code>zh-CN</code>、<code>zh-HK</code>、<code>zh-TW</code>。</td>
  </tr>
  <tr>
    <td width="332"><code>CODEX_BIN</code></td>
    <td>用于启动 Codex CLI 的命令。默认：<code>codex</code>。</td>
  </tr>
  <tr>
    <td width="332"><code>COPILOT_BIN</code></td>
    <td>用于启动 Copilot CLI 的命令。默认：<code>copilot</code>。</td>
  </tr>
  <tr>
    <td width="332"><code>CODEX_MODEL</code></td>
    <td>可选的 Codex model 覆盖。留空则使用 Codex CLI 默认 model。示例：<code>gpt-5.4</code> <a href="https://developers.openai.com/codex/models" target="_blank">OpenAI Codex/OpenAI models</a></td>
  </tr>
  <tr>
    <td width="332"><code>COPILOT_MODEL</code></td>
    <td>可选的 Copilot model 覆盖。留空则使用 Copilot CLI 默认 model。示例：<code>gpt-5.4</code>、<code>claude-sonnet-4.6</code> <a href="https://docs.github.com/en/copilot/reference/ai-models/supported-models" target="_blank">GitHub Copilot supported models</a></td>
  </tr>
  <tr>
    <td width="332"><code>CODEX_APPROVAL_POLICY</code></td>
    <td>传递给 Codex 的 approval mode。默认：<code>never</code>。</td>
  </tr>
  <tr>
    <td width="332"><code>CODEX_SANDBOX_MODE</code></td>
    <td>传递给 Codex 的 sandbox mode。默认：<code>workspace-write</code>。</td>
  </tr>
  <tr>
    <td width="332"><code>CODEX_SKIP_GIT_REPO_CHECK</code></td>
    <td>如果启用，将始终跳过 Codex 的 trusted-repo 检查。</td>
  </tr>
  <tr>
    <td width="332"><code>ENABLE_COMMIT_COMMAND</code></td>
    <td>启用 Telegram 的 <code>/commit</code> 命令。默认：<code>false</code>。</td>
  </tr>
  <tr>
    <td width="332"><code>AGENT_HARD_TIMEOUT_SECONDS</code></td>
    <td>单次 代理运行 的硬超时。默认：<code>0</code>（关闭）。</td>
  </tr>
  <tr>
    <td width="332"><code>SNAPSHOT_TEXT_FILE_MAX_BYTES</code></td>
    <td>构建每次运行的前后快照 diff 时，bot 会按文本读取的最大文件大小。默认：<code>200000</code>。</td>
  </tr>
  <tr>
    <td width="332"><code>MAX_TELEGRAM_MESSAGE_LENGTH</code></td>
    <td>应用拆分回复前使用的最大消息长度。默认：<code>3000</code>。</td>
  </tr>
  <tr>
    <td width="332"><code>ENABLE_SENSITIVE_DIFF_FILTER</code></td>
    <td>隐藏敏感文件的 diff。默认：<code>true</code>。</td>
  </tr>
  <tr>
    <td width="332"><code>ENABLE_SECRET_SCRUB_FILTER</code></td>
    <td>在发送到 Telegram 之前，对 tokens、keys、<code>.env</code> 值、certificates 以及类似秘密输出做脱敏。默认：<code>true</code>（强烈建议开启）。</td>
  </tr>
  <tr>
    <td width="332"><code>SNAPSHOT_INCLUDE_PATH_GLOBS</code></td>
    <td>强制把匹配的路径包含进 diff。示例：<code>.github/*,.profile.test,.profile.prod</code></td>
  </tr>
  <tr>
    <td width="332"><code>SNAPSHOT_EXCLUDE_PATH_GLOBS</code></td>
    <td>在打包默认值之外额外添加 diff 排除规则。示例：<code>.*,personal/*,sensitive*.txt</code> 说明：<code>.*</code> 会匹配隐藏路径，包括隐藏目录中的文件。</td>
  </tr>
</table>


<h3>语音转文字</h3>

<table>
  <tr>
    <td width="332"><code>ENABLE_OPENAI_WHISPER_SPEECH_TO_TEXT</code></td>
    <td>默认：<code>false</code>。如果为 <code>true</code>，则启用语音消息和音频文件识别。系统会检查所需的二进制或库依赖，缺失时提示用户安装。</td>
  </tr>
  <tr>
    <td><code>OPENAI_WHISPER_MODEL</code></td>
    <td>Whisper STT 使用的模型。默认：<code>base</code><br />可用模型：<code>tiny</code> 约 <code>72 MB</code>、<code>base</code> 约 <code>139 MB</code>、<code>large-v3-turbo</code> 约 <code>1.5 GB</code><br />模型会在你第一次发送语音消息时自动下载。一般使用推荐 <code>base</code>。如果你想要更好的准确率和质量，可以尝试 <code>turbo</code>。</td>
  </tr>
  <tr>
    <td><code>OPENAI_WHISPER_TIMEOUT_SECONDS</code></td>
    <td>默认：<code>120</code>。STT 进程的超时时间。通常处理速度已经足够快，但如果你选择 <code>turbo</code>，第一次语音消息可能会因为下载模型而根据网速超过超时限制。</td>
  </tr>
</table>

<h3>状态与日志</h3>

<table>
  <tr>
    <td><code>~/.coding-agent-telegram/state.json</code></td>
    <td>会话状态主文件。</td>
  </tr>
  <tr>
    <td><code>~/.coding-agent-telegram/state.json.bak</code></td>
    <td>状态备份文件。</td>
  </tr>
  <tr>
    <td><code>~/.coding-agent-telegram/logs</code></td>
    <td>日志目录。</td>
  </tr>
</table>

示例：

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

## 🧠 会话管理

会话按以下范围区分：

- Telegram bot
- Telegram chat

这意味着同一个 Telegram 账号可以同时使用多个 bot，而不会把会话混在一起。

示例：

- Bot A + 你的 chat -> backend 工作
- Bot B + 你的 chat -> frontend 工作
- Bot C + 你的 chat -> infra 工作

当前活动会话还会绑定到：

- 项目文件夹
- 提供方
- 如果有的话，branch 名称

<details>
<summary><b>每个会话会保存：</b></summary>

- 会话名称
- 项目文件夹
- branch 名称
- 提供方
- timestamps
- 该 bot/chat 范围下的活动会话选择
</details>

### 🔓 工作区并发锁

同一时间，每个**项目文件夹**只能有一个代理运行实例在执行，不管它是由哪个 chat 或 Telegram bot 触发的。

- **项目忙碌中**：该工作区里已经有一个代理运行实例在执行
- **代理忙碌中**：该运行实例仍在处理当前请求

bot 会强制这个限制，避免两个 agent 同时写入同一个 workspace，从而减少冲突修改和数据损坏的风险。

如果同一个 project 已经有 agent 在运行，又收到新的消息，bot 会立即回复：

> ⏳ 项目上已有代理正在运行。请等待其完成。

这个 lock 只保存在内存中，不写入磁盘，所以当 agent 完成、失败或 server 重启时会自动释放。

### 💬 排队问题

如果当前 project 已经有一个 代理运行 在执行，后续文本消息不会被拒绝，而是会进入队列。

- 新问题会追加到磁盘上的 queued-questions file
- 当前 agent 会继续处理之前的请求
- 当该 run 正常结束后，bot 会自动开始处理队列中的问题

如果当前 run 被 abort 且仍有 排队问题 在等待，bot 不会自动继续。它会询问你是否继续处理剩余问题，以及是打包处理还是逐个处理。

## ⚠️ Diff（文件变更）

_在每次 代理运行 期间，bot 也会为项目生成轻量的 前后快照，用来汇总改动文件并把 diff 发回 Telegram。这个 快照 由 bot 应用自己生成，而不是由 Codex 或 Copilot 生成。_

**快照说明：**

- app 会在 run 前后扫描 项目目录
- 对于普通文本文件，app 会优先使用本次 run 的 快照 diff，而不是 git head diff
- 常见的 依赖、缓存 和 运行时目录 也会被跳过
- 二进制文件 以及大于 `SNAPSHOT_TEXT_FILE_MAX_BYTES` 的 文件 不会按文本读取
- 对于很大的 project，这次额外扫描可能带来明显的 I/O 和内存开销
- 如果 快照 无法把某个 文件 表示成文本，app 会在可能时 fallback 到 `git diff`
- 对于大文件或非文本文件，diff 仍可能被省略，并替换为一条简短说明

快照排除规则位于套件资源中：

- `src/coding_agent_telegram/resources/snapshot_excluded_dir_names.txt`
- `src/coding_agent_telegram/resources/snapshot_excluded_dir_globs.txt`
- `src/coding_agent_telegram/resources/snapshot_excluded_file_globs.txt`

你可以在 环境文件 中覆盖这些默认值，而无需修改已安装的套件：

- `SNAPSHOT_INCLUDE_PATH_GLOBS`
  强制把匹配的 path 包含进 diff。
  示例：`.github/*,.profile.test,.profile.prod`

- `SNAPSHOT_EXCLUDE_PATH_GLOBS`
  在 套件 默认值之外增加额外的 diff 排除规则。
  示例：`.*,personal/*,sensitive*.txt`
  说明：`.*` 会匹配隐藏路径，包括隐藏目录中的文件。

如果 include 和 exclude 同时命中，则 include 优先。

## 🌿 Branch 行为

bot 会把 project 和 branch 当成一组信息来处理。

- 选择 project 时不会悄悄切到无关的 branch
- 如果需要 branch 输入，bot 会提示你选择
- 在会话相关消息里显示 branch 信息时，项目和 branch 会一起展示

当你创建或切换 branch 时，bot 会明确引导你选择 source：

- <code>local/&lt;branch&gt;</code> 表示使用本地 branch 作为 source
- <code>origin/&lt;branch&gt;</code> 表示先从远端 branch 更新，再切换

如果 bot 发现会话里保存的 branch 与当前仓库 branch 不一致，它不会盲目继续，而是会询问你要使用哪一个 branch：

- 保留会话中保存的 branch
- 保留当前 repository branch

如果你偏好的 source branch 已缺失，bot 会基于 default branch 和 current branch 提供 fallback source，而不是直接把你丢给原始 Git error。

## 🔐 Git trust 行为

- 已存在的 folder 遵循 `CODEX_SKIP_GIT_REPO_CHECK`
- 通过 `/project <name>` 创建的 folder 会被此 app 标记为 trusted
- 通过 `/project <name>` 选择的已有 folder，在你于 Telegram 中确认 trust 之前仍然保持 untrusted
- 因此，新建的项目文件夹可以直接使用
- 可以通过 `ENABLE_COMMIT_COMMAND` 完全禁用 `/commit`
- 会修改内容的 `/commit` 操作只允许在 trusted project 上执行

## 🪵 日志

log 会**同时写入 stdout 和轮转日志文件**，路径为：

- `~/.coding-agent-telegram/logs`（10 MB 轮转，保留 3 份备份）

> **注意：**如果你同时盯着 terminal 又去 tail 日志文件，每条消息都会出现两次。这是正常行为。请二选一查看，不要同时看两边。

<details>
<summary><b>常见记录事件</b></summary>

- bot 启动与 polling 启动
- project 选择
- 会话创建
- 会话切换
- 活动会话报告
- 正常 run 执行（包含截断后的 prompt 审计日志行）
- resume 失败后的会话替换
- warnings 与 runtime errors
</details>

## 🗂️ 项目结构

- `src/coding_agent_telegram/`
  应用主代码

- `tests/`
  测试套件

- `startup.sh`
  本地启动与运行入口

- `src/coding_agent_telegram/resources/.env.example`
  标准环境模板，同时用于仓库启动和套件安装

- `pyproject.toml`
  打包 与依赖配置

## 📦 发布版本规则

套件版本由 Git tags 推导而来。

- TestPyPI/testing: `v2026.3.26.dev1`
- PyPI prerelease: `v2026.3.26rc1`
- PyPI stable: `v2026.3.26`

## 📌 说明

- 本项目面向在自己机器上本地运行 agent 的用户。
- Telegram bot 是控制界面，不是实际执行环境。
- 如果你运行多个 bot，也可以由同一个 server process 统一管理。
