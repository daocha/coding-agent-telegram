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
  <p><strong>가볍고, 멀티 봇/멀티 세션/멀티태스킹을 지원하는 24/7 AI Coding Agent</strong></p>
  <p>Telegram으로 어디서나 로컬 AI Coding Agent를 제어하세요.</p>
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

   ## ✨ 왜 써야 하나요
  - ✅ 가벼움: 무거운 프레임워크 없이 투명한 동작
  - ✅ 멀티 봇: 여러 채팅, 여러 세션 지원
  - ✅ Telegram 으로 Codex / Copilot CLI 를 제어
  - ✅ 에이전트 응답과 변경 파일을 코드 블록으로 쉽게 검토
  - ✅ 에이전트가 작업 중일 때도 후속 질문을 큐에 저장
  - ✅ 텍스트와 이미지 입력 지원

   ## 🔁 기기/세션 간 자연스러운 전환

  Telegram에서 시작한 세션을 나중에 컴퓨터에서 같은 Codex/Copilot CLI 세션으로 이어서 작업할 수 있습니다. `/switch`만으로 Telegram과 터미널 사이를 자연스럽게 오갈 수 있습니다.
  
  - `/switch`로 로컬 세션 이어서 작업
  - 이전 세션도 지원

   ## 🛠️ 일반적인 로컬 흐름
   ```bash
   coding-agent-telegram # or run ./startup.sh
   ```

   ##### Telegram에서:

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

→ 원라인 설치: 
```
curl -fsSL https://raw.githubusercontent.com/daocha/coding-agent-telegram/main/install.sh | bash
```

<table>
   <tr>
   <td width="50%" valign="top">

   ## 🔐 보안

- `ALLOWED_CHAT_IDS` 기반 개인 채팅 allowlist
- 충돌하는 쓰기를 줄이기 위해 프로젝트당 하나의 활성 에이전트만 허용
- 민감한 파일 diff는 숨김 처리
- API 키, 토큰, `.env` 값, 인증서, SSH 키 등 비밀로 보이는 출력은 Telegram으로 보내기 전에 마스킹
- 런타임 앱 데이터는 `~/.coding-agent-telegram` 아래에 저장
- 기존 폴더는 변경성 Git 작업 전에 trust 확인을 요구할 수 있음
- 숨겨진 외부 호출 없음. 모든 제어권은 사용자에게 있음
   </td>
   <td width="50%" valign="top">

   ## ✅ 요구 사항

서버를 시작하기 전에 다음을 준비하세요:

- Python 3.9 이상
- _@BotFather_ 에서 만든 Telegram bot token
- 자신의 Telegram chat ID
- 로컬에 설치된 Codex CLI 및/또는 Copilot CLI
- [Codex CLI 설치](https://developers.openai.com/codex/cli)
- [Copilot CLI 설치](https://github.com/features/copilot/cli)
   </td>
   </tr>
</table>

## 🚀 빠른 시작

### Option A: 한 줄 부트스트랩 스크립트
```bash
curl -fsSL https://raw.githubusercontent.com/daocha/coding-agent-telegram/main/install.sh | bash
```

### Option B: `pip`으로 PyPI 설치
```bash
pip install coding-agent-telegram
coding-agent-telegram
```

### Option C: 저장소를 clone해서 실행
```bash
git clone https://github.com/daocha/coding-agent-telegram
cd coding-agent-telegram
./startup.sh
```

### Bot 서버 시작
##### 첫 실행 시 앱이 env 파일을 만들고 어떤 항목을 채워야 하는지 알려줍니다.
##### env 파일을 수정한 뒤 다시 실행하세요:
```bash
# if you follow Option A or Option B, then run
coding-agent-telegram

# if you follow Option C, then run this again
./startup.sh
```

## 🔑 Telegram 설정

### Bot Token 받기

1. Telegram을 열고 `@BotFather` 와 대화를 시작합니다.
2. `/newbot` 을 보냅니다.
3. 다음 항목에 따라 진행합니다:
   - 표시 이름
   - `bot` 으로 끝나는 bot 사용자명
4. BotFather가 HTTP API token 을 반환합니다.
5. 그 token 을 `~/.coding-agent-telegram/.env_coding_agent_telegram` 의 `TELEGRAM_BOT_TOKENS` 에 넣습니다。

### Chat ID 받기

가장 확실한 방법은 자신의 bot token 으로 Telegram `getUpdates` API 를 사용하는 것입니다.

1. bot 과 대화를 시작하고 `/start` 같은 메시지를 보냅니다.
2. `<BOT_TOKEN>` 을 바꿔 아래 URL 을 브라우저에서 엽니다:

```text
https://api.telegram.org/bot<BOT_TOKEN>/getUpdates
```

3. JSON 응답에서 `chat` 객체를 찾습니다.
4. 그 안의 숫자 `id` 값을 복사합니다.
5. 그 값을 `~/.coding-agent-telegram/.env_coding_agent_telegram` 의 `ALLOWED_CHAT_IDS` 에 넣습니다.

참고:

- 개인 채팅의 chat ID 는 보통 양의 정수입니다.
- `getUpdates` 결과가 비어 있으면 bot 에 다시 메시지를 보내고 재시도하세요.

## 📨 지원되는 메시지 유형

## 🤖 Telegram 명령어

<table>
  <tr>
    <td width="250"><code>/provider</code></td>
    <td>새 session용 provider 를 선택합니다. 선택 내용은 바꿀 때까지 bot/chat 단위로 저장됩니다.</td>
  </tr>
  <tr>
    <td width="250"><code>/project &lt;project_folder&gt;</code></td>
    <td>현재 project folder를 설정합니다. 폴더가 없으면 앱이 만들고 trusted 로 표시합니다. 이미 존재하지만 아직 untrusted 이면 trust 확인을 요청합니다.</td>
  </tr>
  <tr>
    <td width="250"><code>/branch &lt;new_branch&gt;</code></td>
    <td>현재 project에서 branch 를 준비하거나 전환합니다. branch 가 이미 있으면 source candidate 로 취급하고, 없으면 repository 의 default branch 를 source candidate 로 사용합니다.</td>
  </tr>
  <tr>
    <td width="250"><code>/branch &lt;origin_branch&gt; &lt;new_branch&gt;</code></td>
    <td>`<origin_branch>` 를 source candidate 로 사용해 branch 를 준비하거나 전환합니다. 두 형식 모두 bot 은 실제로 존재하는 source choice 만 보여줍니다: `local/<branch>`, `origin/<branch>`. 하나만 있으면 그것만 보이고, 둘 다 없으면 branch source 가 없다고 알립니다.</td>
  </tr>
  <tr>
    <td width="250"><code>/current</code></td>
    <td>현재 bot/chat 의 active session 을 보여줍니다.</td>
  </tr>
  <tr>
    <td width="250"><code>/new [session_name]</code></td>
    <td>현재 project에 새 session을 만듭니다. 이름을 생략하면 실제 session ID를 사용합니다. provider, project, branch 가 없으면 bot 이 필요한 단계를 안내합니다.</td>
  </tr>
  <tr>
    <td width="250"><code>/switch</code></td>
    <td>가장 최근 session 을 최신순으로 보여줍니다. 현재 project 의 bot-managed session 과 로컬 Codex/Copilot CLI session 이 함께 표시됩니다.</td>
  </tr>
  <tr>
    <td width="250"><code>/switch page &lt;number&gt;</code></td>
    <td>저장된 session 의 다른 페이지를 보여줍니다.</td>
  </tr>
  <tr>
    <td width="250"><code>/switch &lt;session_id&gt;</code></td>
    <td>ID 로 특정 session 으로 전환합니다. 로컬 CLI session 을 선택하면 bot 이 state 에 가져와 이어서 진행합니다.</td>
  </tr>
  <tr>
    <td width="250"><code>/compact</code></td>
    <td>활성 session 에서 새 compact session 을 만들고 그쪽으로 전환합니다.</td>
  </tr>
  <tr>
    <td width="250"><code>/commit &lt;git commands&gt;</code></td>
    <td>active session project 안에서 검증된 `git commit` 관련 명령을 실행합니다. `ENABLE_COMMIT_COMMAND=true` 일 때만 사용할 수 있습니다. 변경성 Git 명령은 trusted project 가 필요합니다.</td>
  </tr>
  <tr>
    <td width="250"><code>/push</code></td>
    <td>현재 active session 에 대해 `origin <branch>` 를 push 합니다. push 전에 bot 이 확인합니다.</td>
  </tr>
  <tr>
    <td width="250"><code>/abort</code></td>
    <td>현재 project 의 agent run 을 중단합니다. 대기 중인 queued question 이 있으면 계속할지 묻습니다.</td>
  </tr>
</table>

<h2>⚙️ 환경 변수</h2>

<h3>기본 env 파일 경로:</h3>

<table>
  <tr>
    <td><code>CODING_AGENT_TELEGRAM_ENV_FILE</code></td>
    <td>앱이 특정 env 파일을 사용하도록 지정할 때 사용합니다.</td>
  </tr>
  <tr>
    <td><code>~/.coding-agent-telegram/.env_coding_agent_telegram</code></td>
    <td>기본 env 파일 위치입니다.</td>
  </tr>
  <tr>
    <td><code>./.env_coding_agent_telegram</code></td>
    <td>이 로컬 파일이 이미 존재할 때만 사용됩니다.</td>
  </tr>
</table>

<h3>필수</h3>

<table>
  <tr>
    <td width="250"><code>WORKSPACE_ROOT</code></td>
    <td>프로젝트 디렉터리를 담는 상위 폴더입니다.</td>
  </tr>
  <tr>
    <td width="250"><code>TELEGRAM_BOT_TOKENS</code></td>
    <td>쉼표로 구분된 Telegram bot token 목록입니다.</td>
  </tr>
  <tr>
    <td width="250"><code>ALLOWED_CHAT_IDS</code></td>
    <td>이 bot 사용을 허용할 Telegram 개인 chat ID 목록입니다.</td>
  </tr>
</table>

<h3>일반 설정</h3>

<table>
  <tr>
    <td width="250"><code>APP_LOCALE</code></td>
    <td>공용 bot 메시지와 명령 설명에 사용할 UI locale 입니다. 지원 값: <code>en</code>, <code>de</code>, <code>fr</code>, <code>ja</code>, <code>ko</code>, <code>nl</code>, <code>th</code>, <code>vi</code>, <code>zh-CN</code>, <code>zh-HK</code>, <code>zh-TW</code>.</td>
  </tr>
  <tr>
    <td width="250"><code>CODEX_BIN</code></td>
    <td>Codex CLI 를 실행할 명령입니다. 기본값: <code>codex</code>.</td>
  </tr>
  <tr>
    <td width="250"><code>COPILOT_BIN</code></td>
    <td>Copilot CLI 를 실행할 명령입니다. 기본값: <code>copilot</code>.</td>
  </tr>
  <tr>
    <td width="250"><code>CODEX_MODEL</code></td>
    <td>선택적 Codex model override 입니다. 비워 두면 Codex CLI 기본 model 을 사용합니다. 예: <code>gpt-5.4</code> <a href="https://developers.openai.com/codex/models" target="_blank">OpenAI Codex/OpenAI models</a></td>
  </tr>
  <tr>
    <td width="250"><code>COPILOT_MODEL</code></td>
    <td>선택적 Copilot model override 입니다. 비워 두면 Copilot CLI 기본 model 을 사용합니다. 예: <code>gpt-5.4</code>, <code>claude-sonnet-4.6</code> <a href="https://docs.github.com/en/copilot/reference/ai-models/supported-models" target="_blank">GitHub Copilot supported models</a></td>
  </tr>
  <tr>
    <td width="250"><code>CODEX_APPROVAL_POLICY</code></td>
    <td>Codex 에 전달할 approval mode 입니다. 기본값: <code>never</code>.</td>
  </tr>
  <tr>
    <td width="250"><code>CODEX_SANDBOX_MODE</code></td>
    <td>Codex 에 전달할 sandbox mode 입니다. 기본값: <code>workspace-write</code>.</td>
  </tr>
  <tr>
    <td width="250"><code>CODEX_SKIP_GIT_REPO_CHECK</code></td>
    <td>활성화하면 Codex trusted-repo check 를 항상 건너뜁니다.</td>
  </tr>
  <tr>
    <td width="250"><code>ENABLE_COMMIT_COMMAND</code></td>
    <td>Telegram <code>/commit</code> 명령을 활성화합니다. 기본값: <code>false</code>.</td>
  </tr>
  <tr>
    <td width="250"><code>AGENT_HARD_TIMEOUT_SECONDS</code></td>
    <td>단일 agent run 의 하드 타임아웃입니다. 기본값: <code>0</code> (비활성화).</td>
  </tr>
  <tr>
    <td width="250"><code>SNAPSHOT_TEXT_FILE_MAX_BYTES</code></td>
    <td>실행별 diff 스냅샷을 만들 때 bot 이 텍스트로 읽을 최대 파일 크기입니다. 기본값: <code>200000</code>.</td>
  </tr>
  <tr>
    <td width="250"><code>MAX_TELEGRAM_MESSAGE_LENGTH</code></td>
    <td>응답을 분할하기 전 최대 메시지 크기입니다. 기본값: <code>3000</code>.</td>
  </tr>
  <tr>
    <td width="250"><code>ENABLE_SENSITIVE_DIFF_FILTER</code></td>
    <td>민감한 파일의 diff 를 숨깁니다. 기본값: <code>true</code>.</td>
  </tr>
  <tr>
    <td width="250"><code>ENABLE_SECRET_SCRUB_FILTER</code></td>
    <td>tokens, keys, <code>.env</code> 값, certificates 등 비밀스러운 출력을 Telegram 으로 보내기 전에 마스킹합니다. 기본값: <code>true</code> (강력 권장).</td>
  </tr>
  <tr>
    <td width="250"><code>SNAPSHOT_INCLUDE_PATH_GLOBS</code></td>
    <td>일치하는 경로를 diff 에 강제로 포함합니다. 예: <code>.github/*,.profile.test,.profile.prod</code></td>
  </tr>
  <tr>
    <td width="250"><code>SNAPSHOT_EXCLUDE_PATH_GLOBS</code></td>
    <td>패키지 기본값 위에 추가 diff 제외 규칙을 더합니다. 예: <code>.*,personal/*,sensitive*.txt</code> 참고: <code>.*</code> 는 hidden directory 안 파일을 포함한 hidden path 에도 매칭됩니다.</td>
  </tr>
</table>

<h3>상태와 로그</h3>

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

예시:

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

## 🧠 Session 관리

Session 은 다음 범위로 구분됩니다:

- Telegram bot
- Telegram chat

따라서 같은 Telegram 계정이라도 여러 bot 을 사용하면서 session 이 섞이지 않게 운영할 수 있습니다.

예시:

- Bot A + 내 chat -> backend 작업
- Bot B + 내 chat -> frontend 작업
- Bot C + 내 chat -> infra 작업

active session 은 다음에도 연결됩니다:

- project folder
- provider
- 가능할 경우 branch 이름

<details>
<summary><b>각 session 에 저장되는 내용</b></summary>

- session 이름
- project folder
- branch 이름
- provider
- timestamps
- 해당 bot/chat 범위의 active session 선택
</details>

### 🔓 Workspace concurrency lock

동시에 실행될 수 있는 agent run 은 **project folder** 당 하나뿐입니다. 어떤 chat 이나 Telegram bot 이 시작했는지는 관계없습니다.

- **project is busy**: 그 workspace 에 이미 agent run 이 있는 상태
- **agent is busy**: 그 하나의 run 이 현재 요청을 아직 처리 중인 상태

두 agent 가 같은 workspace 에 동시에 쓰지 않도록 bot 이 이 제한을 강제합니다. 충돌하는 수정과 데이터 손상 가능성을 줄이기 위함입니다.

같은 project 에서 이미 agent 가 실행 중이면 bot 은 즉시 다음과 같이 응답합니다:

> ⏳ 이 project 에서는 이미 agent 가 실행 중입니다. 끝날 때까지 기다려 주세요.

lock 은 디스크가 아니라 메모리에만 유지되므로 agent 가 끝나거나 실패하거나 server 가 재시작되면 자동으로 해제됩니다.

### 💬 Queued questions

현재 project 에 이미 agent run 이 있으면, 이후의 텍스트 메시지는 거절되지 않고 queue 됩니다.

- 새 질문은 디스크의 queued-questions file 에 추가됩니다
- 현재 agent 는 이전 요청을 계속 처리합니다
- run 이 정상적으로 끝나면 bot 이 queued questions 를 자동으로 처리하기 시작합니다

현재 run 이 abort 되었고 queued questions 가 남아 있으면 자동으로 계속하지 않습니다. 남은 질문을 계속 처리할지, 묶어서 할지, 하나씩 할지를 bot 이 묻습니다.

## ⚠️ Diff (파일 변경)

_각 agent run 동안 bot 은 project 의 가벼운 before/after snapshot 도 만들어 변경 파일 요약과 diff 를 Telegram 으로 보낼 수 있게 합니다. 이 snapshot 은 Codex 나 Copilot 이 아니라 bot 앱 자체가 만듭니다._

**Snapshot 참고 사항:**

- app 은 run 전후에 project directory 를 순회합니다
- 일반 텍스트 파일은 git head diff 보다 run 별 snapshot diff 를 우선합니다
- 일반적인 dependency, cache, runtime directory 도 건너뜁니다
- binary file 과 `SNAPSHOT_TEXT_FILE_MAX_BYTES` 보다 큰 file 은 텍스트로 읽지 않습니다
- 매우 큰 project 에서는 이 추가 스캔으로 I/O 와 memory 부담이 커질 수 있습니다
- snapshot 이 file 을 텍스트로 표현할 수 없으면 가능할 때 `git diff` 로 fallback 합니다
- 큰 file 이나 비텍스트 file 은 diff 를 생략하고 짧은 안내로 대체할 수 있습니다

Snapshot 제외 규칙은 package resource 에 있습니다:

- `src/coding_agent_telegram/resources/snapshot_excluded_dir_names.txt`
- `src/coding_agent_telegram/resources/snapshot_excluded_dir_globs.txt`
- `src/coding_agent_telegram/resources/snapshot_excluded_file_globs.txt`

설치된 package 를 수정하지 않고 env file 에서 기본값을 덮어쓸 수 있습니다:

- `SNAPSHOT_INCLUDE_PATH_GLOBS`
  일치하는 path 를 diff 에 강제로 포함합니다.
  예: `.github/*,.profile.test,.profile.prod`

- `SNAPSHOT_EXCLUDE_PATH_GLOBS`
  package 기본값 위에 추가 diff 제외를 더합니다.
  예: `.*,personal/*,sensitive*.txt`
  참고: `.*` 는 hidden directory 안의 file 을 포함한 hidden path 와도 일치합니다.

include 와 exclude 가 모두 맞으면 include 가 우선합니다.

## 🌿 Branch 동작

bot 은 project 와 branch 를 하나의 묶음으로 다룹니다.

- project 를 선택해도 관련 없는 branch 를 조용히 선택하지 않습니다
- branch 가 필요하면 bot 이 직접 선택을 요청합니다
- session 관련 메시지에서 branch 정보를 보여줄 때는 project 와 branch 를 함께 표시합니다

branch 를 만들거나 바꿀 때 bot 은 source 를 명시적으로 안내합니다:

- `local/<branch>`: local branch 를 source 로 사용
- `origin/<branch>`: remote branch 에서 먼저 업데이트한 뒤 전환

저장된 session branch 와 현재 repository branch 가 다르면 bot 은 그대로 진행하지 않습니다. 어떤 branch 를 쓸지 물어봅니다:

- 저장된 session branch 사용
- 현재 repository branch 사용

원하는 source branch 가 없으면 raw Git error 대신 default branch 와 current branch 를 기반으로 fallback source 를 제안합니다.

## 🔐 Git trust 동작

- 기존 folder 는 `CODEX_SKIP_GIT_REPO_CHECK` 를 따릅니다
- `/project <name>` 로 만든 folder 는 이 app 이 trusted 로 표시합니다
- `/project <name>` 로 선택한 기존 folder 는 Telegram prompt 에서 trust 를 확인하기 전까지 untrusted 로 남습니다
- 따라서 새로 만든 project folder 는 바로 사용할 수 있습니다
- `/commit` 은 `ENABLE_COMMIT_COMMAND` 로 완전히 비활성화할 수 있습니다
- 변경을 일으키는 `/commit` 작업은 trusted project 에서만 허용됩니다

## 🪵 Logs

log 는 **stdout 과 회전하는 log file 양쪽**에 기록됩니다:

- `~/.coding-agent-telegram/logs` (10 MB 에서 회전, 3개 백업 유지)

> **참고:** terminal 을 보면서 동시에 log file 을 tail 하면 각 메시지가 두 번 보입니다. 정상 동작입니다. 둘 중 하나만 보세요.

<details>
<summary><b>자주 기록되는 이벤트</b></summary>

- bot 시작과 polling 시작
- project 선택
- session 생성
- session 전환
- active session 표시
- 일반 run 실행 (잘린 prompt 가 포함된 audit log line 포함)
- resume 실패 후 session 교체
- warning 과 runtime error
</details>

## 🗂️ 프로젝트 구조

- `src/coding_agent_telegram/`
  메인 애플리케이션 코드

- `tests/`
  테스트 스위트

- `startup.sh`
  로컬 bootstrap / 시작 진입점

- `src/coding_agent_telegram/resources/.env.example`
  repo 시작과 package 설치에서 모두 사용하는 canonical environment template

- `pyproject.toml`
  packaging 및 dependency 설정

## 📦 릴리스 버전 규칙

package version 은 Git tag 에서 파생됩니다.

- TestPyPI/testing: `v2026.3.26.dev1`
- PyPI prerelease: `v2026.3.26rc1`
- PyPI stable: `v2026.3.26`

## 📌 참고

- 이 프로젝트는 자기 머신에서 agent 를 로컬로 실행하는 사용자를 위해 설계되었습니다.
- Telegram bot 은 제어 인터페이스이지 실제 실행 환경은 아닙니다.
- 여러 bot 을 사용해도 하나의 server process 로 모두 관리할 수 있습니다.
