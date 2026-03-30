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
  <p><strong>Nhẹ, nhiều bot, nhiều phiên, đa nhiệm, AI Coding Agent chạy 24/7</strong></p>
  <p>Điều khiển AI Coding Agent cục bộ của bạn từ bất kỳ đâu bằng Telegram.</p>
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

   ## ✨ Vì sao nên dùng
  - ✅ Nhẹ: không cần framework nặng, minh bạch hoàn toàn
  - ✅ Nhiều bot: nhiều cuộc chat, nhiều phiên
  - ✅ Dùng Telegram để điều khiển Codex / Copilot CLI
  - ✅ Dễ xem câu trả lời và các file đã thay đổi trong code block
  - ✅ Có thể xếp hàng câu hỏi tiếp theo khi agent đang làm việc
  - ✅ Hỗ trợ đầu vào văn bản và hình ảnh

   ## 🔁 Chuyển thiết bị/phiên liền mạch

  Bắt đầu một phiên trên Telegram rồi tiếp tục đúng phiên Codex/Copilot CLI đó trên máy tính sau mà không cần thao tác rườm rà. Với `/switch`, bạn cũng có thể chuyển qua lại mượt mà giữa Telegram và command line.
  
  - Dùng `/switch` để tiếp tục một phiên cục bộ
  - Hỗ trợ cả các phiên lịch sử

   ## 🛠️ Luồng làm việc cục bộ điển hình
   ```bash
   coding-agent-telegram # or run ./startup.sh
   ```

   ##### Trong Telegram:

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

→ Cài đặt bằng một dòng lệnh: 
```
curl -fsSL https://raw.githubusercontent.com/daocha/coding-agent-telegram/main/install.sh | bash
```

<table>
   <tr>
   <td width="65%" valign="top">

   ## 🔐 Bảo mật

- Danh sách trắng cho chat riêng qua `ALLOWED_CHAT_IDS`
- Chỉ cho phép một agent hoạt động trên mỗi project để giảm xung đột ghi
- Ẩn diff của các file nhạy cảm
- API keys, tokens, giá trị `.env`, certificates, SSH keys và các đầu ra mang tính bí mật sẽ được che trước khi gửi lại Telegram
- Dữ liệu runtime của app nằm dưới `~/.coding-agent-telegram`
- Các thư mục có sẵn có thể yêu cầu xác nhận trust trước khi chạy Git operation có thay đổi
- Máy chủ không thực hiện các lời gọi ra ngoài một cách ẩn. Bạn giữ toàn quyền kiểm soát.
- Hoạt động tốt với Codex Sandbox mode, bạn không cần cấp `danger-full-access`
   </td>
   <td width="35%" valign="top">

   ## ✅ Yêu cầu

Trước khi khởi động server, hãy chuẩn bị:

- Python 3.9 trở lên
- Telegram bot token tạo từ _@BotFather_
- Telegram chat ID của bạn
- Codex CLI và/hoặc Copilot CLI đã được cài cục bộ
- [Cài Codex CLI](https://developers.openai.com/codex/cli)
- [Cài Copilot CLI](https://github.com/features/copilot/cli)
   </td>
   </tr>
</table>

## 🦞 Vì sao tôi cần cái này nếu đã có Openclaw?
Openclaw cung cấp bộ tính năng rất đầy đủ và đã có sẵn agent loop tích hợp tên là Pi-Agent. Nó khá toàn diện và phù hợp với nhiều use case đa dạng hơn. Tôi cũng là người thích Openclaw và từng code với Openclaw. Tuy vậy, riêng cho coding thì đây không phải lúc nào cũng là lựa chọn tốt nhất vì system prompt tích hợp khá lớn và context đi kèm nhiều hơn. Claude Code / Codex / Copilot vẫn thường hiệu quả hơn, chính xác hơn, ít bị phân tán hơn và trực tiếp hơn cho việc coding. Dự án này được giữ rất đơn giản, chỉ tích hợp Codex / Copilot CLI. Nghĩa là bạn giao việc trực tiếp cho Codex / Copilot.

## 🚀 Bắt đầu nhanh

### Option A: Script bootstrap một dòng
```bash
curl -fsSL https://raw.githubusercontent.com/daocha/coding-agent-telegram/main/install.sh | bash
```

### Option B: Cài từ PyPI bằng `pip`
```bash
pip install coding-agent-telegram
coding-agent-telegram
```

### Option C: Chạy từ repository đã clone
```bash
git clone https://github.com/daocha/coding-agent-telegram
cd coding-agent-telegram
./startup.sh
```

### Khởi động bot server
##### Ở lần chạy đầu, app sẽ tạo file env và cho bạn biết cần điền trường nào.
##### Sau khi cập nhật file env, hãy chạy lại:
```bash
# if you follow Option A or Option B, then run
coding-agent-telegram

# if you follow Option C, then run this again
./startup.sh
```

## 🔑 Thiết lập Telegram

### Lấy Bot Token

1. Mở Telegram và bắt đầu chat với `@BotFather`.
2. Gửi `/newbot`.
3. Làm theo hướng dẫn để chọn:
   - tên hiển thị
   - tên người dùng bot kết thúc bằng `bot`
4. BotFather sẽ trả về một HTTP API token.
5. Đặt token đó vào `TELEGRAM_BOT_TOKENS` trong `~/.coding-agent-telegram/.env_coding_agent_telegram`. 

### Lấy Chat ID

Cách đáng tin cậy nhất là dùng API `getUpdates` của Telegram với chính bot token của bạn.

1. Bắt đầu chat với bot của bạn và gửi một tin nhắn như `/start`.
2. Mở URL này trong trình duyệt và thay `<BOT_TOKEN>`:

```text
https://api.telegram.org/bot<BOT_TOKEN>/getUpdates
```

3. Tìm object `chat` trong JSON trả về.
4. Sao chép trường số `id` trong object đó.
5. Đặt giá trị đó vào `ALLOWED_CHAT_IDS` trong `~/.coding-agent-telegram/.env_coding_agent_telegram`.

Lưu ý:

- Với chat riêng, chat ID thường là số nguyên dương.
- Nếu `getUpdates` trả về rỗng, hãy gửi thêm một tin nhắn cho bot rồi thử lại.

## 📨 Loại tin nhắn được hỗ trợ

## 🤖 Lệnh Telegram

<table>
  <tr>
    <td width="250"><code>/provider</code></td>
    <td>Chọn provider cho các session mới. Lựa chọn này được lưu theo từng bot và chat cho đến khi bạn thay đổi.</td>
  </tr>
  <tr>
    <td width="250"><code>/project &lt;project_folder&gt;</code></td>
    <td>Đặt thư mục project hiện tại. Nếu thư mục chưa tồn tại, app sẽ tạo và đánh dấu là trusted. Nếu đã tồn tại nhưng vẫn untrusted, app sẽ yêu cầu xác nhận trust rõ ràng.</td>
  </tr>
  <tr>
    <td width="250"><code>/branch &lt;new_branch&gt;</code></td>
    <td>Chuẩn bị hoặc chuyển branch cho project hiện tại. Nếu branch đã tồn tại, bot coi branch đó là source candidate. Nếu chưa có, bot dùng default branch của repository làm source candidate.</td>
  </tr>
  <tr>
    <td width="250"><code>/branch &lt;origin_branch&gt; &lt;new_branch&gt;</code></td>
    <td>Chuẩn bị hoặc chuyển branch bằng cách dùng `<origin_branch>` làm source candidate. Với cả hai dạng, bot chỉ đưa ra các source choice thật sự tồn tại: `local/<branch>` và `origin/<branch>`. Nếu chỉ có một lựa chọn thì chỉ hiện lựa chọn đó. Nếu không có lựa chọn nào, bot sẽ báo thiếu branch source.</td>
  </tr>
  <tr>
    <td width="250"><code>/current</code></td>
    <td>Hiển thị active session cho bot và chat hiện tại.</td>
  </tr>
  <tr>
    <td width="250"><code>/new [session_name]</code></td>
    <td>Tạo session mới cho project hiện tại. Nếu bỏ qua tên, bot sẽ dùng session ID thật. Nếu thiếu provider, project hoặc branch, bot sẽ hướng dẫn bước còn thiếu.</td>
  </tr>
  <tr>
    <td width="250"><code>/switch</code></td>
    <td>Hiển thị các session mới nhất, mới nhất trước. Danh sách bao gồm cả session do bot quản lý và local Codex/Copilot CLI session của project hiện tại.</td>
  </tr>
  <tr>
    <td width="250"><code>/switch page &lt;number&gt;</code></td>
    <td>Hiển thị trang khác của các session đã lưu.</td>
  </tr>
  <tr>
    <td width="250"><code>/switch &lt;session_id&gt;</code></td>
    <td>Chuyển sang một session cụ thể bằng ID. Nếu bạn chọn local CLI session, bot sẽ import nó và tiếp tục từ đó.</td>
  </tr>
  <tr>
    <td width="250"><code>/compact</code></td>
    <td>Tạo một session rút gọn mới từ session đang hoạt động rồi chuyển sang session đó.</td>
  </tr>
  <tr>
    <td width="250"><code>/commit &lt;git commands&gt;</code></td>
    <td>Chạy các lệnh liên quan đến `git commit` đã được kiểm tra trong project của active session. Chỉ có khi `ENABLE_COMMIT_COMMAND=true`. Các lệnh Git có thay đổi yêu cầu project đã trusted.</td>
  </tr>
  <tr>
    <td width="250"><code>/push</code></td>
    <td>Push `origin <branch>` cho active session hiện tại. Bot sẽ hỏi xác nhận trước khi push.</td>
  </tr>
  <tr>
    <td width="250"><code>/abort</code></td>
    <td>Hủy agent run hiện tại của project hiện tại. Nếu còn queued questions chờ xử lý, bot sẽ hỏi có tiếp tục hay không.</td>
  </tr>
</table>

<h2>⚙️ Biến môi trường</h2>

<h3>Đường dẫn file env chính:</h3>

<table>
  <tr>
    <td><code>CODING_AGENT_TELEGRAM_ENV_FILE</code></td>
    <td>Dùng khi bạn muốn app trỏ tới một file env cụ thể.</td>
  </tr>
  <tr>
    <td><code>~/.coding-agent-telegram/.env_coding_agent_telegram</code></td>
    <td>Vị trí file env mặc định.</td>
  </tr>
  <tr>
    <td><code>./.env_coding_agent_telegram</code></td>
    <td>Chỉ dùng khi file local này đã tồn tại.</td>
  </tr>
</table>

<h3>Bắt buộc</h3>

<table>
  <tr>
    <td width="250"><code>WORKSPACE_ROOT</code></td>
    <td>Thư mục cha chứa các thư mục project của bạn.</td>
  </tr>
  <tr>
    <td width="250"><code>TELEGRAM_BOT_TOKENS</code></td>
    <td>Các Telegram bot token, ngăn cách bằng dấu phẩy.</td>
  </tr>
  <tr>
    <td width="250"><code>ALLOWED_CHAT_IDS</code></td>
    <td>Các Telegram private chat ID được phép dùng bot, ngăn cách bằng dấu phẩy.</td>
  </tr>
</table>

<h3>Cài đặt thường dùng</h3>

<table>
  <tr>
    <td width="250"><code>APP_LOCALE</code></td>
    <td>Ngôn ngữ UI cho các thông điệp bot dùng chung và mô tả lệnh. Giá trị hỗ trợ: <code>en</code>, <code>de</code>, <code>fr</code>, <code>ja</code>, <code>ko</code>, <code>nl</code>, <code>th</code>, <code>vi</code>, <code>zh-CN</code>, <code>zh-HK</code>, <code>zh-TW</code>.</td>
  </tr>
  <tr>
    <td width="250"><code>CODEX_BIN</code></td>
    <td>Lệnh dùng để chạy Codex CLI. Mặc định: <code>codex</code>.</td>
  </tr>
  <tr>
    <td width="250"><code>COPILOT_BIN</code></td>
    <td>Lệnh dùng để chạy Copilot CLI. Mặc định: <code>copilot</code>.</td>
  </tr>
  <tr>
    <td width="250"><code>CODEX_MODEL</code></td>
    <td>Ghi đè model Codex nếu cần. Để trống để dùng model mặc định của Codex CLI. Ví dụ: <code>gpt-5.4</code> <a href="https://developers.openai.com/codex/models" target="_blank">OpenAI Codex/OpenAI models</a></td>
  </tr>
  <tr>
    <td width="250"><code>COPILOT_MODEL</code></td>
    <td>Ghi đè model Copilot nếu cần. Để trống để dùng model mặc định của Copilot CLI. Ví dụ: <code>gpt-5.4</code>, <code>claude-sonnet-4.6</code> <a href="https://docs.github.com/en/copilot/reference/ai-models/supported-models" target="_blank">GitHub Copilot supported models</a></td>
  </tr>
  <tr>
    <td width="250"><code>CODEX_APPROVAL_POLICY</code></td>
    <td>Chế độ approval truyền cho Codex. Mặc định: <code>never</code>.</td>
  </tr>
  <tr>
    <td width="250"><code>CODEX_SANDBOX_MODE</code></td>
    <td>Chế độ sandbox truyền cho Codex. Mặc định: <code>workspace-write</code>.</td>
  </tr>
  <tr>
    <td width="250"><code>CODEX_SKIP_GIT_REPO_CHECK</code></td>
    <td>Nếu bật, luôn bỏ qua trusted-repo check của Codex.</td>
  </tr>
  <tr>
    <td width="250"><code>ENABLE_COMMIT_COMMAND</code></td>
    <td>Bật lệnh Telegram <code>/commit</code>. Mặc định: <code>false</code>.</td>
  </tr>
  <tr>
    <td width="250"><code>AGENT_HARD_TIMEOUT_SECONDS</code></td>
    <td>Timeout cứng cho một lần agent run. Mặc định: <code>0</code> (tắt).</td>
  </tr>
  <tr>
    <td width="250"><code>SNAPSHOT_TEXT_FILE_MAX_BYTES</code></td>
    <td>Kích thước file tối đa mà bot sẽ đọc dưới dạng văn bản khi tạo before/after snapshot cho diff của từng run. Mặc định: <code>200000</code>.</td>
  </tr>
  <tr>
    <td width="250"><code>MAX_TELEGRAM_MESSAGE_LENGTH</code></td>
    <td>Kích thước tin nhắn tối đa trước khi app tách phản hồi. Mặc định: <code>3000</code>.</td>
  </tr>
  <tr>
    <td width="250"><code>ENABLE_SENSITIVE_DIFF_FILTER</code></td>
    <td>Ẩn diff của các file nhạy cảm. Mặc định: <code>true</code>.</td>
  </tr>
  <tr>
    <td width="250"><code>ENABLE_SECRET_SCRUB_FILTER</code></td>
    <td>Che tokens, keys, giá trị <code>.env</code>, certificates và các đầu ra giống bí mật trước khi gửi về Telegram. Mặc định: <code>true</code> (rất nên bật).</td>
  </tr>
  <tr>
    <td width="250"><code>SNAPSHOT_INCLUDE_PATH_GLOBS</code></td>
    <td>Luôn đưa các path khớp điều kiện vào diff. Ví dụ: <code>.github/*,.profile.test,.profile.prod</code></td>
  </tr>
  <tr>
    <td width="250"><code>SNAPSHOT_EXCLUDE_PATH_GLOBS</code></td>
    <td>Thêm các rule loại trừ diff ngoài bộ mặc định của package. Ví dụ: <code>.*,personal/*,sensitive*.txt</code> Lưu ý: <code>.*</code> khớp cả path ẩn, gồm cả file trong thư mục ẩn.</td>
  </tr>
</table>

<h3>Trạng thái và log</h3>

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

Ví dụ:

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

## 🧠 Quản lý Session

Session được tách theo:

- Telegram bot
- Telegram chat

Vì vậy cùng một tài khoản Telegram có thể dùng nhiều bot mà không làm lẫn session.

Ví dụ:

- Bot A + chat của bạn -> việc backend
- Bot B + chat của bạn -> việc frontend
- Bot C + chat của bạn -> việc infra

active session cũng gắn với:

- project folder
- provider
- branch name nếu có

<details>
<summary><b>Mỗi session lưu:</b></summary>

- tên session
- project folder
- branch name
- provider
- timestamps
- active session được chọn cho phạm vi bot/chat đó
</details>

### 🔓 Workspace concurrency lock

Chỉ có thể có một agent run hoạt động trên mỗi **project folder** tại một thời điểm, bất kể chat hay Telegram bot nào khởi chạy.

- **project is busy**: workspace đó đã có một agent run đang chạy
- **agent is busy**: chính run đó vẫn đang xử lý yêu cầu hiện tại

Bot cố ý áp dụng giới hạn này để hai agent không ghi vào cùng một workspace cùng lúc. Điều đó giúp tránh sửa đổi xung đột và giảm nguy cơ hỏng dữ liệu.

Nếu có tin nhắn đến khi cùng project đã có agent chạy, bot sẽ trả lời ngay:

> ⏳ Đã có agent đang chạy trên project này. Hãy đợi cho đến khi nó hoàn tất.

Lock được giữ trong bộ nhớ, không phải trên đĩa, nên sẽ tự giải phóng khi agent hoàn tất, lỗi hoặc khi server khởi động lại.

### 💬 Câu hỏi trong hàng đợi

Nếu project hiện tại đã có agent run đang chạy, các tin nhắn văn bản gửi sau sẽ không bị từ chối mà được đưa vào queue.

- câu hỏi mới được nối vào file queued-questions trên đĩa
- agent hiện tại tiếp tục làm yêu cầu trước đó
- khi run đó kết thúc bình thường, bot tự động bắt đầu xử lý các câu hỏi trong hàng đợi

Nếu run hiện tại bị abort và vẫn còn queued questions, bot sẽ không tự tiếp tục. Bot sẽ hỏi có muốn tiếp tục xử lý phần còn lại theo dạng gộp hay từng câu một hay không.

## ⚠️ Diff (thay đổi file)

_Trong mỗi agent run, bot cũng tạo một snapshot before/after nhẹ của project để có thể tóm tắt các file thay đổi và gửi diff về Telegram. Snapshot này do chính bot app tạo ra, không phải bởi Codex hay Copilot._

**Ghi chú về snapshot:**

- app quét project directory trước và sau mỗi run
- với file văn bản thông thường, app ưu tiên snapshot diff theo từng run hơn là diff so với git head
- các thư mục dependency, cache và runtime phổ biến cũng bị bỏ qua
- file nhị phân và file lớn hơn `SNAPSHOT_TEXT_FILE_MAX_BYTES` sẽ không được đọc như văn bản
- với project rất lớn, lần quét bổ sung này có thể làm tăng đáng kể I/O và bộ nhớ
- nếu snapshot không thể biểu diễn file dưới dạng văn bản, app sẽ fallback sang `git diff` khi có thể
- với file lớn hoặc không phải văn bản, diff vẫn có thể bị bỏ qua và thay bằng thông báo ngắn

Các rule loại trừ snapshot nằm trong package resources:

- `src/coding_agent_telegram/resources/snapshot_excluded_dir_names.txt`
- `src/coding_agent_telegram/resources/snapshot_excluded_dir_globs.txt`
- `src/coding_agent_telegram/resources/snapshot_excluded_file_globs.txt`

Bạn có thể override các giá trị mặc định này trong file env mà không cần sửa package đã cài:

- `SNAPSHOT_INCLUDE_PATH_GLOBS`
  Luôn đưa các path khớp vào diff.
  Ví dụ: `.github/*,.profile.test,.profile.prod`

- `SNAPSHOT_EXCLUDE_PATH_GLOBS`
  Thêm các diff exclusion ngoài bộ mặc định của package.
  Ví dụ: `.*,personal/*,sensitive*.txt`
  Lưu ý: `.*` khớp cả hidden path, kể cả file trong hidden directory.

Nếu include và exclude cùng khớp, include sẽ được ưu tiên.

## 🌿 Hành vi của Branch

Bot coi project và branch là một cặp đi cùng nhau.

- việc chọn project sẽ không âm thầm chọn một branch không liên quan
- nếu cần branch, bot sẽ yêu cầu bạn chọn
- khi thông tin branch được hiển thị trong các thông báo liên quan đến session, project và branch sẽ được hiển thị cùng nhau

Khi bạn tạo hoặc đổi branch, bot sẽ hướng dẫn rõ source:

- `local/<branch>` nghĩa là dùng local branch làm source
- `origin/<branch>` nghĩa là cập nhật từ remote branch trước rồi mới chuyển

Nếu bot phát hiện branch lưu trong session không khớp với branch hiện tại của repository, bot sẽ không tiếp tục một cách mù quáng. Bot sẽ hỏi bạn muốn dùng branch nào:

- giữ branch đã lưu trong session
- giữ branch hiện tại của repository

Nếu source branch bạn muốn không còn, bot sẽ đưa ra các fallback source dựa trên default branch và current branch thay vì để bạn đối mặt với Git error thô.

## 🔐 Hành vi trust của Git

- thư mục đã tồn tại sẽ tuân theo `CODEX_SKIP_GIT_REPO_CHECK`
- thư mục được tạo qua `/project <name>` sẽ được app này đánh dấu là trusted
- thư mục đã có sẵn được chọn qua `/project <name>` sẽ vẫn là untrusted cho đến khi bạn xác nhận trust trong Telegram
- vì vậy các project folder mới tạo có thể dùng ngay
- có thể tắt hoàn toàn `/commit` bằng `ENABLE_COMMIT_COMMAND`
- các thao tác `/commit` có sửa đổi chỉ được phép trên trusted project

## 🪵 Logs

Log được ghi **cả ra stdout và vào file log quay vòng** dưới:

- `~/.coding-agent-telegram/logs` (quay vòng ở 10 MB, giữ 3 bản sao)

> **Lưu ý:** nếu bạn vừa xem terminal vừa tail file log, mỗi thông điệp sẽ xuất hiện hai lần. Đây là hành vi bình thường. Hãy chỉ xem một nơi tại một thời điểm.

<details>
<summary><b>Các sự kiện thường được ghi log</b></summary>

- bot khởi động và bắt đầu polling
- chọn project
- tạo session
- chuyển session
- báo cáo active session
- chạy bình thường (bao gồm audit log line với prompt đã được rút gọn)
- thay session sau khi resume thất bại
- warnings và runtime errors
</details>

## 🗂️ Cấu trúc dự án

- `src/coding_agent_telegram/`
  mã nguồn chính của ứng dụng

- `tests/`
  bộ kiểm thử

- `startup.sh`
  entrypoint bootstrap và startup cục bộ

- `src/coding_agent_telegram/resources/.env.example`
  mẫu environment chính được dùng cả khi chạy từ repo và khi cài dưới dạng package

- `pyproject.toml`
  cấu hình packaging và dependencies

## 📦 Quy ước phiên bản release

Phiên bản package được suy ra từ Git tags.

- TestPyPI/testing: `v2026.3.26.dev1`
- PyPI prerelease: `v2026.3.26rc1`
- PyPI stable: `v2026.3.26`

## 📌 Ghi chú

- Dự án này dành cho người dùng chạy agent cục bộ trên chính máy của mình.
- Telegram bot là lớp điều khiển, không phải môi trường thực thi.
- Nếu bạn chạy nhiều bot, tất cả vẫn có thể được quản lý bởi một server process duy nhất.
