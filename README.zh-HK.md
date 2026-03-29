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
  <p><strong>輕量、多 Bot、多工作階段、多工、24/7 AI Coding Agent</strong></p>
  <p>透過 Telegram 隨時隨地控制你本機的 AI Coding Agent。</p>
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

   ## ✨ 為什麼使用它
  - ✅ 輕量：沒有重型框架，行為清晰透明
  - ✅ 多 Bot：支援多個聊天、多個工作階段
  - ✅ 使用 Telegram 控制 Codex / Copilot CLI
  - ✅ 可在 code block 中輕鬆查看 agent 回覆及改動檔案
  - ✅ agent 執行中仍可把後續問題排入佇列
  - ✅ 支援文字與圖片輸入

   ## 🔁 裝置與工作階段無縫切換

  你可以先在 Telegram 開始一個工作階段，之後再在電腦上繼續同一個 Codex/Copilot CLI 工作階段，過程自然順暢。使用 `/switch` 亦可在 Telegram 與 command line 之間輕鬆切換。
  
  - 使用 `/switch` 繼續本機工作階段
  - 亦支援歷史工作階段

   ## 🛠️ 典型本機流程
   ```bash
   coding-agent-telegram # or run ./startup.sh
   ```

   ##### 在 Telegram：

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

→ 一行指令安裝： 
```
curl -fsSL https://raw.githubusercontent.com/daocha/coding-agent-telegram/main/install.sh | bash
```

<table>
   <tr>
   <td width="50%" valign="top">

   ## 🔐 安全性

- 透過 `ALLOWED_CHAT_IDS` 對私人聊天做 allowlist 控制
- 每個 project 同一時間只允許一個活躍 agent，以減少衝突寫入
- 敏感檔案 diff 會被隱藏
- API keys、tokens、`.env` 值、certificates、SSH keys 及類似敏感輸出在送回 Telegram 前會被遮罩
- 執行期 app 資料保存在 `~/.coding-agent-telegram` 下
- 現有資料夾在執行會修改內容的 Git operation 前，可能需要先確認 trust
- 沒有隱藏的外部呼叫，一切都由你掌控
   </td>
   <td width="50%" valign="top">

   ## ✅ 需求

在啟動 server 之前，請先準備：

- Python 3.9 或以上
- 由 _@BotFather_ 建立的 Telegram bot token
- 你的 Telegram chat ID
- 已在本機安裝 Codex CLI 及/或 Copilot CLI
- [安裝 Codex CLI](https://developers.openai.com/codex/cli)
- [安裝 Copilot CLI](https://github.com/features/copilot/cli)
   </td>
   </tr>
</table>

## 🚀 快速開始

### Option A：一行 bootstrap script
```bash
curl -fsSL https://raw.githubusercontent.com/daocha/coding-agent-telegram/main/install.sh | bash
```

### Option B：使用 `pip` 從 PyPI 安裝
```bash
pip install coding-agent-telegram
coding-agent-telegram
```

### Option C：從 clone 下來的 repository 執行
```bash
git clone https://github.com/daocha/coding-agent-telegram
cd coding-agent-telegram
./startup.sh
```

### 啟動 Bot Server
##### 第一次執行時，app 會建立 env 檔案，並告訴你需要填寫哪些欄位。
##### 更新 env 檔案後，再次執行：
```bash
# if you follow Option A or Option B, then run
coding-agent-telegram

# if you follow Option C, then run this again
./startup.sh
```

## 🔑 Telegram 設定

### 取得 Bot Token

1. 開啟 Telegram，並與 `@BotFather` 開始聊天。
2. 傳送 `/newbot`。
3. 按提示設定：
   - 顯示名稱
   - 以 `bot` 結尾的 bot 使用者名稱
4. BotFather 會回傳 HTTP API token。
5. 把這個 token 填入 `~/.coding-agent-telegram/.env_coding_agent_telegram` 內的 `TELEGRAM_BOT_TOKENS`。

### 取得 Chat ID

最可靠的方法是使用你自己的 bot token 呼叫 Telegram 的 `getUpdates` API。

1. 與你的 bot 開始聊天，並傳送一條訊息，例如 `/start`。
2. 在瀏覽器開啟以下 URL，並將 `<BOT_TOKEN>` 替換掉：

```text
https://api.telegram.org/bot<BOT_TOKEN>/getUpdates
```

3. 在 JSON 回應中找出 `chat` 物件。
4. 複製其中數值型的 `id` 欄位。
5. 把該值填入 `~/.coding-agent-telegram/.env_coding_agent_telegram` 內的 `ALLOWED_CHAT_IDS`。

說明：

- 私人聊天的 chat ID 通常是正整數。
- 如果 `getUpdates` 回傳空結果，請先再傳一條訊息給 bot，然後重試。

## 📨 支援的訊息類型

## 🤖 Telegram 指令

<table>
  <tr>
    <td width="250"><code>/provider</code></td>
    <td>為新 session 選擇 provider。這個選擇會按 bot 與 chat 儲存，直到你手動修改。</td>
  </tr>
  <tr>
    <td width="250"><code>/project &lt;project_folder&gt;</code></td>
    <td>設定目前的 project 資料夾。如果資料夾不存在，app 會建立並標記為 trusted；如果已存在但仍是 untrusted，app 會明確要求確認 trust。</td>
  </tr>
  <tr>
    <td width="250"><code>/branch &lt;new_branch&gt;</code></td>
    <td>為目前的 project 準備或切換 branch。如果 branch 已存在，bot 會把它當作 source candidate；否則會使用 repository 的 default branch 作為 source candidate。</td>
  </tr>
  <tr>
    <td width="250"><code>/branch &lt;origin_branch&gt; &lt;new_branch&gt;</code></td>
    <td>使用 `<origin_branch>` 作為 source candidate 來準備或切換 branch。無論哪種形式，bot 之後只會提供實際存在的 source choices：`local/<branch>` 和 `origin/<branch>`。若只存在其中一個，就只顯示那個；若兩個都不存在，bot 會提示缺少 branch source。</td>
  </tr>
  <tr>
    <td width="250"><code>/current</code></td>
    <td>顯示目前 bot 與 chat 的 active session。</td>
  </tr>
  <tr>
    <td width="250"><code>/new [session_name]</code></td>
    <td>為目前的 project 建立新 session。如果省略名稱，bot 會使用真實 session ID。若缺少 provider、project 或 branch，bot 會引導你完成缺少的步驟。</td>
  </tr>
  <tr>
    <td width="250"><code>/switch</code></td>
    <td>顯示最新的 session，按由新到舊排序。列表同時包含 bot-managed sessions 以及目前 project 的本機 Codex/Copilot CLI sessions。</td>
  </tr>
  <tr>
    <td width="250"><code>/switch page &lt;number&gt;</code></td>
    <td>顯示已儲存 sessions 的其他頁面。</td>
  </tr>
  <tr>
    <td width="250"><code>/switch &lt;session_id&gt;</code></td>
    <td>透過 ID 切換到指定 session。如果你選擇本機 CLI session，bot 會把它匯入 state 並從那裡繼續。</td>
  </tr>
  <tr>
    <td width="250"><code>/compact</code></td>
    <td>從目前使用中的 session 建立新的壓縮 session，並切換到該 session。</td>
  </tr>
  <tr>
    <td width="250"><code>/commit &lt;git commands&gt;</code></td>
    <td>在 active session 的 project 內執行已驗證的 `git commit` 相關指令。只在 `ENABLE_COMMIT_COMMAND=true` 時可用。會修改內容的 Git 指令要求 project 已 trusted。</td>
  </tr>
  <tr>
    <td width="250"><code>/push</code></td>
    <td>為目前 active session 執行 `origin <branch>` push。push 前 bot 會要求確認。</td>
  </tr>
  <tr>
    <td width="250"><code>/abort</code></td>
    <td>中止目前 project 的 agent run。如果還有 queued questions 等候，bot 會詢問是否繼續處理。</td>
  </tr>
</table>

<h2>⚙️ 環境變數</h2>

<h3>主要 env 檔案路徑：</h3>

<table>
  <tr>
    <td><code>CODING_AGENT_TELEGRAM_ENV_FILE</code></td>
    <td>如果你想讓 app 使用指定的 env 檔案，可設定此項。</td>
  </tr>
  <tr>
    <td><code>~/.coding-agent-telegram/.env_coding_agent_telegram</code></td>
    <td>預設的 env 檔案位置。</td>
  </tr>
  <tr>
    <td><code>./.env_coding_agent_telegram</code></td>
    <td>只有當這個本機檔案已經存在時才會使用。</td>
  </tr>
</table>

<h3>必要</h3>

<table>
  <tr>
    <td width="250"><code>WORKSPACE_ROOT</code></td>
    <td>包含你各個 project 目錄的父資料夾。</td>
  </tr>
  <tr>
    <td width="250"><code>TELEGRAM_BOT_TOKENS</code></td>
    <td>以逗號分隔的 Telegram bot token。</td>
  </tr>
  <tr>
    <td width="250"><code>ALLOWED_CHAT_IDS</code></td>
    <td>允許使用此 bot 的 Telegram 私人 chat ID，使用逗號分隔。</td>
  </tr>
</table>

<h3>常用設定</h3>

<table>
  <tr>
    <td width="250"><code>APP_LOCALE</code></td>
    <td>共用 bot 訊息與指令說明所使用的 UI 語言。支援值：<code>en</code>、<code>de</code>、<code>fr</code>、<code>ja</code>、<code>ko</code>、<code>nl</code>、<code>th</code>、<code>vi</code>、<code>zh-CN</code>、<code>zh-HK</code>、<code>zh-TW</code>。</td>
  </tr>
  <tr>
    <td width="250"><code>CODEX_BIN</code></td>
    <td>用來啟動 Codex CLI 的指令。預設：<code>codex</code>。</td>
  </tr>
  <tr>
    <td width="250"><code>COPILOT_BIN</code></td>
    <td>用來啟動 Copilot CLI 的指令。預設：<code>copilot</code>。</td>
  </tr>
  <tr>
    <td width="250"><code>CODEX_MODEL</code></td>
    <td>可選的 Codex model override。留空則使用 Codex CLI 預設 model。例子：<code>gpt-5.4</code> <a href="https://developers.openai.com/codex/models" target="_blank">OpenAI Codex/OpenAI models</a></td>
  </tr>
  <tr>
    <td width="250"><code>COPILOT_MODEL</code></td>
    <td>可選的 Copilot model override。留空則使用 Copilot CLI 預設 model。例子：<code>gpt-5.4</code>、<code>claude-sonnet-4.6</code> <a href="https://docs.github.com/en/copilot/reference/ai-models/supported-models" target="_blank">GitHub Copilot supported models</a></td>
  </tr>
  <tr>
    <td width="250"><code>CODEX_APPROVAL_POLICY</code></td>
    <td>傳遞給 Codex 的 approval mode。預設：<code>never</code>。</td>
  </tr>
  <tr>
    <td width="250"><code>CODEX_SANDBOX_MODE</code></td>
    <td>傳遞給 Codex 的 sandbox mode。預設：<code>workspace-write</code>。</td>
  </tr>
  <tr>
    <td width="250"><code>CODEX_SKIP_GIT_REPO_CHECK</code></td>
    <td>如果啟用，會一直略過 Codex 的 trusted-repo 檢查。</td>
  </tr>
  <tr>
    <td width="250"><code>ENABLE_COMMIT_COMMAND</code></td>
    <td>啟用 Telegram 的 <code>/commit</code> 指令。預設：<code>false</code>。</td>
  </tr>
  <tr>
    <td width="250"><code>AGENT_HARD_TIMEOUT_SECONDS</code></td>
    <td>單次 agent run 的硬性 timeout。預設：<code>0</code>（停用）。</td>
  </tr>
  <tr>
    <td width="250"><code>SNAPSHOT_TEXT_FILE_MAX_BYTES</code></td>
    <td>建立每次執行的前後 snapshot diff 時，bot 會以文字讀取的最大檔案大小。預設：<code>200000</code>。</td>
  </tr>
  <tr>
    <td width="250"><code>MAX_TELEGRAM_MESSAGE_LENGTH</code></td>
    <td>app 分割回覆前使用的最大訊息長度。預設：<code>3000</code>。</td>
  </tr>
  <tr>
    <td width="250"><code>ENABLE_SENSITIVE_DIFF_FILTER</code></td>
    <td>隱藏敏感檔案的 diff。預設：<code>true</code>。</td>
  </tr>
  <tr>
    <td width="250"><code>ENABLE_SECRET_SCRUB_FILTER</code></td>
    <td>在送往 Telegram 之前，對 tokens、keys、<code>.env</code> 值、certificates 及類似秘密輸出做遮罩。預設：<code>true</code>（強烈建議啟用）。</td>
  </tr>
  <tr>
    <td width="250"><code>SNAPSHOT_INCLUDE_PATH_GLOBS</code></td>
    <td>強制把符合條件的 path 納入 diff。例子：<code>.github/*,.profile.test,.profile.prod</code></td>
  </tr>
  <tr>
    <td width="250"><code>SNAPSHOT_EXCLUDE_PATH_GLOBS</code></td>
    <td>在套件預設值之外額外加入 diff 排除規則。例子：<code>.*,personal/*,sensitive*.txt</code> 說明：<code>.*</code> 會比對隱藏 path，包括隱藏資料夾內的檔案。</td>
  </tr>
</table>

<h3>State 與 Logs</h3>

<table>
  <tr>
    <td><code>~/.coding-agent-telegram/state.json</code></td>
    <td>Hauptdatei für den Session-Status.</td>
  </tr>
  <tr>
    <td><code>~/.coding-agent-telegram/state.json.bak</code></td>
    <td>Backup-Datei für den Status.</td>
  </tr>
  <tr>
    <td><code>~/.coding-agent-telegram/logs</code></td>
    <td>Log-Verzeichnis.</td>
  </tr>
</table>

範例：

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

## 🧠 Session 管理

Session 會按以下範圍分開：

- Telegram bot
- Telegram chat

這表示同一個 Telegram 帳號可以同時使用多個 bot，而不會把 session 混在一起。

例子：

- Bot A + 你的 chat -> backend 工作
- Bot B + 你的 chat -> frontend 工作
- Bot C + 你的 chat -> infra 工作

active session 亦會綁定到：

- project folder
- provider
- 如有的話，branch 名稱

<details>
<summary><b>每個 session 會儲存：</b></summary>

- session 名稱
- project folder
- branch 名稱
- provider
- timestamps
- 該 bot/chat 範圍下的 active session 選擇
</details>

### 🔓 Workspace concurrency lock

同一時間，每個 **project folder** 只能有一個 agent run 在執行，不論它是由哪個 chat 或 Telegram bot 觸發。

- **project is busy**：該 workspace 裡已經有一個 agent run 在運行
- **agent is busy**：那個 run 仍在處理目前的請求

bot 會強制這個限制，避免兩個 agent 同時寫入同一個 workspace，從而減少衝突修改和資料損壞風險。

如果同一個 project 已經有 agent 在運行，又收到新訊息，bot 會立即回覆：

> ⏳ 這個 project 上已經有 agent 在運行。請等待它完成。

這個 lock 只保存在記憶體中，不會寫入磁碟，所以當 agent 完成、失敗或 server 重新啟動時會自動釋放。

### 💬 排隊問題

如果目前的 project 已經有一個 agent run 在執行，之後的文字訊息不會被拒絕，而是會進入佇列。

- 新問題會追加到磁碟上的 queued-questions file
- 目前的 agent 會繼續處理先前的請求
- 當該 run 正常結束後，bot 會自動開始處理佇列中的問題

如果目前的 run 被 abort，而仍有 queued questions 在等待，bot 不會自動繼續。它會詢問你是否要繼續處理剩餘問題，以及要分批還是逐個處理。

## ⚠️ Diff（檔案變更）

_在每次 agent run 期間，bot 也會為 project 產生輕量的 before/after snapshot，用來總結已變更檔案並把 diff 傳回 Telegram。這個 snapshot 是由 bot app 自己建立，不是由 Codex 或 Copilot 建立。_

**Snapshot 說明：**

- app 會在 run 前後掃描 project directory
- 對一般文字檔，app 會優先使用本次 run 的 snapshot diff，而不是 git head diff
- 常見的 dependency、cache 和 runtime directory 也會被略過
- binary file 以及大於 `SNAPSHOT_TEXT_FILE_MAX_BYTES` 的 file 不會以文字方式讀取
- 對非常大的 project，這次額外掃描可能增加明顯的 I/O 和記憶體負擔
- 如果 snapshot 無法把 file 表示為文字，app 會在可行時 fallback 到 `git diff`
- 對大檔案或非文字檔，diff 仍可能被省略，並以簡短訊息代替

Snapshot 排除規則位於 package resources：

- `src/coding_agent_telegram/resources/snapshot_excluded_dir_names.txt`
- `src/coding_agent_telegram/resources/snapshot_excluded_dir_globs.txt`
- `src/coding_agent_telegram/resources/snapshot_excluded_file_globs.txt`

你可以在 env file 中覆蓋這些預設值，而不用修改已安裝的 package：

- `SNAPSHOT_INCLUDE_PATH_GLOBS`
  強制把符合的 path 納入 diff。
  例子：`.github/*,.profile.test,.profile.prod`

- `SNAPSHOT_EXCLUDE_PATH_GLOBS`
  在 package 預設值之外加入額外的 diff 排除規則。
  例子：`.*,personal/*,sensitive*.txt`
  說明：`.*` 會比對 hidden path，包括 hidden directory 內的 file。

如果 include 和 exclude 同時命中，include 會優先。

## 🌿 Branch 行為

bot 會把 project 和 branch 當成一組來處理。

- 選擇 project 時不會靜默切到無關 branch
- 如果需要 branch 輸入，bot 會要求你選擇
- 在 session 相關訊息中顯示 branch 資訊時，project 和 branch 會一起顯示

當你建立或切換 branch 時，bot 會明確引導你選擇 source：

- `local/<branch>`：使用本地 branch 作為 source
- `origin/<branch>`：先從遠端 branch 更新，再切換

如果 bot 發現 session 中儲存的 branch 與目前 repository branch 不一致，它不會盲目繼續，而會詢問你想使用哪個 branch：

- 保留 session 中儲存的 branch
- 保留目前 repository branch

如果你偏好的 source branch 已不存在，bot 會根據 default branch 和 current branch 提供 fallback source，而不是直接丟出原始 Git error。

## 🔐 Git trust 行為

- 已存在的 folder 會遵循 `CODEX_SKIP_GIT_REPO_CHECK`
- 透過 `/project <name>` 建立的 folder 會被這個 app 標記為 trusted
- 透過 `/project <name>` 選取的既有 folder，在你於 Telegram 確認 trust 前仍然保持 untrusted
- 因此，新建立的 project folder 可以立即使用
- 可以用 `ENABLE_COMMIT_COMMAND` 完全停用 `/commit`
- 會修改內容的 `/commit` 操作只允許在 trusted project 上執行

## 🪵 Logs

log 會**同時寫入 stdout 和輪轉 log file**，路徑如下：

- `~/.coding-agent-telegram/logs`（10 MB 輪轉，保留 3 份備份）

> **注意：**如果你同時看 terminal 又去 tail log file，每條訊息都會出現兩次。這是正常行為。請只看其中一邊，不要同時看兩邊。

<details>
<summary><b>常見記錄事件</b></summary>

- bot 啟動與 polling 開始
- project 選擇
- session 建立
- session 切換
- active session 報告
- 正常 run 執行（包含被截短的 prompt audit log 行）
- resume 失敗後的 session 替換
- warnings 與 runtime errors
</details>

## 🗂️ 專案結構

- `src/coding_agent_telegram/`
  app 主程式碼

- `tests/`
  測試套件

- `startup.sh`
  本地 bootstrap 與 startup 入口

- `src/coding_agent_telegram/resources/.env.example`
  標準環境範本，同時用於 repo 啟動與 package 安裝

- `pyproject.toml`
  packaging 與 dependency 設定

## 📦 Release 版本規則

package 版本由 Git tags 推導而來。

- TestPyPI/testing: `v2026.3.26.dev1`
- PyPI prerelease: `v2026.3.26rc1`
- PyPI stable: `v2026.3.26`

## 📌 備註

- 本專案面向在自己機器上本地執行 agent 的使用者。
- Telegram bot 是控制介面，不是實際執行環境。
- 如果你運行多個 bot，也可以由同一個 server process 統一管理。
