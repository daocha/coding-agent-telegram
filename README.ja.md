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
  <p><strong>軽量・マルチBot・マルチセッション・マルチタスク対応の 24/7 AI Coding Agent</strong></p>
  <p>Telegram からどこでもローカルの AI Coding Agent を操作できます。</p>
  <p>
    <img src="https://img.shields.io/badge/stability-experimental-orange.svg" alt="Experimental" />
    <a href="https://opensource.org/licenses/MIT">
      <img src="https://img.shields.io/badge/License-MIT-blue.svg" alt="MIT License" />
    </a>
    <a href="http://github.com/daocha/coding-agent-telegram/releases/latest">
      <img src="https://img.shields.io/github/v/release/daocha/coding-agent-telegram?label=Latest&color=green" alt="Latest Release" />
    </a>
  </p>
</div>

<table border="0">
   <tr>
   <td border="0">

   ## ✨ このプロジェクトを使う理由
- ✅ 軽量: 重いフレームワーク不要、挙動が見えやすい
- ✅ マルチBot: 複数チャット、複数セッションに対応
- ✅ Telegram で Codex / Copilot CLI を操作できる
- ✅ エージェントの回答や変更ファイルをコードブロックで確認しやすい
- ✅ エージェント実行中でも追加入力をキューに積める
- ✅ テキストと画像入力に対応

   ## 🔁 デバイス/セッションをシームレスに切り替え

Telegram で始めたセッションを、あとで同じ Codex/Copilot CLI セッションとして PC 上でそのまま続けられます。`/switch` を使えば Telegram とコマンドラインの行き来も簡単です。

- `/switch` でローカルセッションを再開
- 過去のセッションも利用可能

   ## 🛠️ 典型的なローカルフロー
   ```bash
   coding-agent-telegram # or run ./startup.sh
   ```

   ##### Telegram では:

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

→ ワンライナーでセットアップ: 
```
curl -fsSL https://raw.githubusercontent.com/daocha/coding-agent-telegram/main/install.sh | bash
```

<table>
   <tr>
   <td width="50%" valign="top">

   ## 🔐 セキュリティ

- `ALLOWED_CHAT_IDS` によるプライベートチャットの許可リスト
- 競合する書き込みを減らすため、1プロジェクトにつきアクティブなエージェントは1つだけ
- 機密ファイルの diff は非表示
- API キー、トークン、`.env` の値、証明書、SSH キーなどの機密らしい出力は Telegram へ返す前にマスク
- 実行時データは `~/.coding-agent-telegram` 配下に保存
- 既存フォルダでは、変更を伴う Git 操作の前に trust 確認を求める場合あり
- 隠れた外部呼び出しなし。すべて自分で管理可能
   </td>
   <td width="50%" valign="top">

   ## ✅ 必要なもの

サーバー起動前に次を用意してください:

- Python 3.9 以上
- _@BotFather_ で作成した Telegram Bot Token
- 自分の Telegram Chat ID
- ローカルにインストール済みの Codex CLI または Copilot CLI
- [Codex CLI インストール](https://developers.openai.com/codex/cli)
- [Copilot CLI インストール](https://github.com/features/copilot/cli)
   </td>
   </tr>
</table>

## 🚀 クイックスタート

### Option A: ワンライナーのブートストラップスクリプト
```bash
curl -fsSL https://raw.githubusercontent.com/daocha/coding-agent-telegram/main/install.sh | bash
```

### Option B: `pip` で PyPI からインストール
```bash
pip install coding-agent-telegram
coding-agent-telegram
```

### Option C: クローンしたリポジトリから実行
```bash
git clone https://github.com/daocha/coding-agent-telegram
cd coding-agent-telegram
./startup.sh
```

### Bot サーバーを起動
##### 初回起動時にアプリが env ファイルを作成し、入力すべき項目を案内します。
##### env ファイルを更新したら、次を再実行してください:
```bash
# if you follow Option A or Option B, then run
coding-agent-telegram

# if you follow Option C, then run this again
./startup.sh
```

## 🔑 Telegram セットアップ

### Bot Token を取得

1. Telegram を開いて `@BotFather` とのチャットを開始します。
2. `/newbot` を送信します。
3. 次の内容に従って設定します:
   - 表示名
   - `bot` で終わるユーザー名
4. BotFather から HTTP API token が返されます。
5. その token を `~/.coding-agent-telegram/.env_coding_agent_telegram` の `TELEGRAM_BOT_TOKENS` に設定します。

### Chat ID を取得

最も確実なのは、自分の bot token で Telegram の `getUpdates` API を使う方法です。

1. 自分の bot とのチャットを開き、`/start` などのメッセージを送ります。
2. `<BOT_TOKEN>` を置き換えて次の URL をブラウザで開きます:

```text
https://api.telegram.org/bot<BOT_TOKEN>/getUpdates
```

3. JSON レスポンスの `chat` オブジェクトを探します。
4. その中の数値 `id` をコピーします。
5. その値を `~/.coding-agent-telegram/.env_coding_agent_telegram` の `ALLOWED_CHAT_IDS` に設定します。

メモ:

- プライベートチャットの Chat ID は通常正の整数です。
- `getUpdates` が空なら、bot にもう一度メッセージを送り、再試行してください。

## 📨 対応メッセージタイプ

## 🤖 Telegram コマンド

<table>
  <tr>
    <td width="250"><code>/project &lt;project_folder&gt;</code></td>
    <td>現在のプロジェクトフォルダを設定します。フォルダが存在しない場合は作成して trusted として扱います。既存で untrusted の場合は明示的に trust を確認します。</td>
  </tr>
  <tr>
    <td width="250"><code>/provider</code></td>
    <td>新しい session 用の provider を選択します。選択は変更するまで bot と chat ごとに保存されます。</td>
  </tr>
  <tr>
    <td width="250"><code>/new [session_name]</code></td>
    <td>現在のプロジェクトに新しい session を作成します。名前を省略すると実際の session ID を使います。provider、project、branch が不足している場合は bot が不足分を案内します。</td>
  </tr>
  <tr>
    <td width="250"><code>/branch &lt;new_branch&gt;</code></td>
    <td>現在のプロジェクトで branch を準備または切り替えます。branch が既に存在する場合はその branch を source candidate として扱います。存在しない場合は repository の default branch を source candidate に使います。</td>
  </tr>
  <tr>
    <td width="250"><code>/branch &lt;origin_branch&gt; &lt;new_branch&gt;</code></td>
    <td>`<origin_branch>` を source candidate として branch を準備または切り替えます。どちらの形式でも bot は実在する source choice のみを提示します: `local/<branch>` と `origin/<branch>`。片方だけ存在する場合はその選択肢だけが表示され、どちらも無い場合は branch source が無いと通知します。</td>
  </tr>
  <tr>
    <td width="250"><code>/switch</code></td>
    <td>最新の session を新しい順で表示します。現在のプロジェクトに対する bot-managed session とローカルの Codex/Copilot CLI session の両方を含みます。</td>
  </tr>
  <tr>
    <td width="250"><code>/switch page &lt;number&gt;</code></td>
    <td>保存済み session の別ページを表示します。</td>
  </tr>
  <tr>
    <td width="250"><code>/switch &lt;session_id&gt;</code></td>
    <td>ID を指定して特定の session に切り替えます。ローカル CLI session を選ぶと bot がそれを取り込み、そこから続行します。</td>
  </tr>
  <tr>
    <td width="250"><code>/current</code></td>
    <td>現在の bot と chat の active session を表示します。</td>
  </tr>
  <tr>
    <td width="250"><code>/abort</code></td>
    <td>現在のプロジェクトで実行中の agent run を中断します。queued questions がある場合は続行するか確認します。</td>
  </tr>
  <tr>
    <td width="250"><code>/commit &lt;git commands&gt;</code></td>
    <td>active session の project 内で、検証済みの `git commit` 関連コマンドを実行します。`ENABLE_COMMIT_COMMAND=true` のときだけ利用できます。変更を伴う Git コマンドには trusted project が必要です。</td>
  </tr>
  <tr>
    <td width="250"><code>/push</code></td>
    <td>現在の active session に対して `origin <branch>` を push します。push 前に bot が確認します。</td>
  </tr>
</table>

<h2>⚙️ 環境変数</h2>

<h3>メイン env ファイルのパス:</h3>

<table>
  <tr>
    <td><code>CODING_AGENT_TELEGRAM_ENV_FILE</code></td>
    <td>アプリに特定の env ファイルを使わせたい場合に指定します。</td>
  </tr>
  <tr>
    <td><code>~/.coding-agent-telegram/.env_coding_agent_telegram</code></td>
    <td>既定の env ファイルの場所です。</td>
  </tr>
  <tr>
    <td><code>./.env_coding_agent_telegram</code></td>
    <td>このローカルファイルがすでに存在する場合にのみ使われます。</td>
  </tr>
</table>

<h3>必須</h3>

<table>
  <tr>
    <td width="250"><code>WORKSPACE_ROOT</code></td>
    <td>プロジェクトディレクトリを含む親フォルダです。</td>
  </tr>
  <tr>
    <td width="250"><code>TELEGRAM_BOT_TOKENS</code></td>
    <td>カンマ区切りの Telegram bot token です。</td>
  </tr>
  <tr>
    <td width="250"><code>ALLOWED_CHAT_IDS</code></td>
    <td>この bot の利用を許可する Telegram プライベート chat ID をカンマ区切りで指定します。</td>
  </tr>
</table>

<h3>よく使う設定</h3>

<table>
  <tr>
    <td width="250"><code>APP_LOCALE</code></td>
    <td>共有 bot メッセージとコマンド説明の UI 言語です。対応値: <code>en</code>, <code>de</code>, <code>fr</code>, <code>ja</code>, <code>ko</code>, <code>nl</code>, <code>th</code>, <code>vi</code>, <code>zh-CN</code>, <code>zh-HK</code>, <code>zh-TW</code>.</td>
  </tr>
  <tr>
    <td width="250"><code>CODEX_BIN</code></td>
    <td>Codex CLI を起動するコマンドです。既定値: <code>codex</code>.</td>
  </tr>
  <tr>
    <td width="250"><code>COPILOT_BIN</code></td>
    <td>Copilot CLI を起動するコマンドです。既定値: <code>copilot</code>.</td>
  </tr>
  <tr>
    <td width="250"><code>CODEX_MODEL</code></td>
    <td>Codex モデルの任意上書きです。空欄なら Codex CLI の既定モデルを使います。例: <code>gpt-5.4</code> <a href="https://developers.openai.com/codex/models" target="_blank">OpenAI Codex/OpenAI models</a></td>
  </tr>
  <tr>
    <td width="250"><code>COPILOT_MODEL</code></td>
    <td>Copilot モデルの任意上書きです。空欄なら Copilot CLI の既定モデルを使います。例: <code>gpt-5.4</code>, <code>claude-sonnet-4.6</code> <a href="https://docs.github.com/en/copilot/reference/ai-models/supported-models" target="_blank">GitHub Copilot supported models</a></td>
  </tr>
  <tr>
    <td width="250"><code>CODEX_APPROVAL_POLICY</code></td>
    <td>Codex に渡す approval mode。既定: <code>never</code>.</td>
  </tr>
  <tr>
    <td width="250"><code>CODEX_SANDBOX_MODE</code></td>
    <td>Codex に渡す sandbox mode。既定: <code>workspace-write</code>.</td>
  </tr>
  <tr>
    <td width="250"><code>CODEX_SKIP_GIT_REPO_CHECK</code></td>
    <td>有効にすると Codex の trusted-repo check を常にスキップします。</td>
  </tr>
  <tr>
    <td width="250"><code>ENABLE_COMMIT_COMMAND</code></td>
    <td>Telegram の <code>/commit</code> コマンドを有効にします。既定: <code>false</code>.</td>
  </tr>
  <tr>
    <td width="250"><code>AGENT_HARD_TIMEOUT_SECONDS</code></td>
    <td>単一の agent run に対するハードタイムアウト。既定: <code>0</code>（無効）。</td>
  </tr>
  <tr>
    <td width="250"><code>SNAPSHOT_TEXT_FILE_MAX_BYTES</code></td>
    <td>実行ごとの diff 用に before/after snapshot を作る際、bot がテキストとして読む最大ファイルサイズです。既定: <code>200000</code>.</td>
  </tr>
  <tr>
    <td width="250"><code>MAX_TELEGRAM_MESSAGE_LENGTH</code></td>
    <td>応答を分割する前に使う最大メッセージサイズ。既定: <code>3000</code>.</td>
  </tr>
  <tr>
    <td width="250"><code>ENABLE_SENSITIVE_DIFF_FILTER</code></td>
    <td>機密ファイルの diff を隠します。既定: <code>true</code>.</td>
  </tr>
  <tr>
    <td width="250"><code>ENABLE_SECRET_SCRUB_FILTER</code></td>
    <td>tokens、keys、<code>.env</code> 値、certificates などの秘密らしい出力を Telegram 送信前にマスクします。既定: <code>true</code>（強く推奨）。</td>
  </tr>
  <tr>
    <td width="250"><code>SNAPSHOT_INCLUDE_PATH_GLOBS</code></td>
    <td>一致するパスを diff に強制的に含めます。例: <code>.github/*,.profile.test,.profile.prod</code></td>
  </tr>
  <tr>
    <td width="250"><code>SNAPSHOT_EXCLUDE_PATH_GLOBS</code></td>
    <td>パッケージ既定値に加えて diff 除外を追加します。例: <code>.*,personal/*,sensitive*.txt</code> 注: <code>.*</code> は hidden directory 内のファイルも含む hidden path に一致します。</td>
  </tr>
</table>

<h3>状態ファイルとログ</h3>

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

例:

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

Session は次の単位で分かれます:

- Telegram bot
- Telegram chat

そのため、同じ Telegram アカウントでも複数の bot を使い分けながら session を混在させずに運用できます。

例:

- Bot A + あなたの chat -> backend 作業
- Bot B + あなたの chat -> frontend 作業
- Bot C + あなたの chat -> infra 作業

active session はさらに次にも紐づきます:

- project folder
- provider
- 利用可能なら branch 名

<details>
<summary><b>各 session に保存される内容</b></summary>

- session 名
- project folder
- branch 名
- provider
- timestamps
- その bot/chat スコープでの active session 選択
</details>

### 🔓 Workspace concurrency lock

**project folder** ごとに同時に動ける agent run は 1 つだけです。どの chat や Telegram bot から起動したかは関係ありません。

- **project is busy**: その workspace ですでに agent run が動いている状態
- **agent is busy**: その 1 つの run が現在の依頼をまだ処理中の状態

2 つの agent が同じ workspace に同時に書き込まないように、この制約を設けています。競合する編集やデータ破損の可能性を減らすためです。

同じ project で既に agent が動作中なら、bot はすぐに次のように返します:

> ⏳ この project ではすでに agent が実行中です。完了するまで待ってください。

lock はディスクではなくメモリ上に保持されるため、agent 完了・失敗・server 再起動時に自動で解放されます。

### 💬 キューされた質問

現在の project で既に agent run が動いている場合、後から送られたテキストメッセージは拒否されずに queue されます。

- 新しい質問はディスク上の queued-questions file に追記されます
- 現在の agent は先の依頼をそのまま処理し続けます
- run が正常終了すると、bot は queue 内の質問の処理を自動で開始します

現在の run が abort され、まだ queued questions が残っている場合は自動継続しません。残りを続けるかどうか、まとめて処理するか 1 件ずつ処理するかを bot が確認します。

## ⚠️ Diff（ファイル変更）

_各 agent run のたびに、bot はプロジェクトの軽量な before/after snapshot も取得し、変更ファイルの要約と diff を Telegram に送ります。この snapshot は Codex や Copilot ではなく、bot 自身が作成します。_

**Snapshot のポイント:**

- app は run の前後で project directory を走査します
- 通常のテキストファイルでは、git head diff よりも run ごとの snapshot diff を優先します
- 一般的な依存関係、cache、runtime directory も除外されます
- binary file と `SNAPSHOT_TEXT_FILE_MAX_BYTES` を超える file は text として読み込みません
- 非常に大きな project では、この追加走査によって I/O と memory の負荷が増えることがあります
- snapshot で text として表現できない file は、可能なら `git diff` に fallback します
- 大きい file や非 text file では、diff を省略して短いメッセージに置き換えることがあります

Snapshot の除外ルールは package resource にあります:

- `src/coding_agent_telegram/resources/snapshot_excluded_dir_names.txt`
- `src/coding_agent_telegram/resources/snapshot_excluded_dir_globs.txt`
- `src/coding_agent_telegram/resources/snapshot_excluded_file_globs.txt`

これらの既定値は、インストール済み package を編集せずに env file から上書きできます:

- `SNAPSHOT_INCLUDE_PATH_GLOBS`
  一致した path を diff に強制的に含めます。
  例: `.github/*,.profile.test,.profile.prod`

- `SNAPSHOT_EXCLUDE_PATH_GLOBS`
  package 既定値に追加の diff 除外を加えます。
  例: `.*,personal/*,sensitive*.txt`
  注: `.*` は hidden directory 内の file も含む hidden path に一致します。

include と exclude の両方が一致した場合は include が優先されます。

## 🌿 Branch の動作

bot は project と branch をひとまとまりとして扱います。

- project を選んでも、無関係な branch を勝手に選びません
- branch が必要なときは、bot が選択を求めます
- session 関連メッセージで branch を表示するときは、project と branch を一緒に表示します

branch を作成または切り替えるとき、bot は source を明示的に案内します:

- `local/<branch>`: ローカル branch を source に使う
- `origin/<branch>`: remote branch から更新してから切り替える

保存済み session の branch と現在の repository branch が一致しない場合、bot はそのまま続行しません。どちらの branch を使うか確認します:

- 保存済み session の branch を使う
- 現在の repository branch を使う

希望する source branch が存在しない場合は、生の Git error にせず、default branch と current branch を元に fallback source を提案します。

## 🔐 Git trust の動作

- 既存 folder は `CODEX_SKIP_GIT_REPO_CHECK` に従います
- `/project <name>` で作成した folder は、この app により trusted として扱われます
- 既存 folder を `/project <name>` で選択した場合は、Telegram prompt で trust を確認するまで untrusted のままです
- そのため、新しく作成した project folder はすぐに使えます
- `/commit` は `ENABLE_COMMIT_COMMAND` で完全に無効化できます
- 変更を伴う `/commit` 操作は trusted project でのみ許可されます

## 🪵 Logs

log は **stdout とローテーションする log file の両方**に書き込まれます:

- `~/.coding-agent-telegram/logs`（10 MB でローテーション、3 世代保持）

> **注意:** terminal を見ながら同時に log file を tail すると、各メッセージが 2 回表示されます。これは想定どおりです。どちらか一方だけを見てください。

<details>
<summary><b>よく記録されるイベント</b></summary>

- bot 起動と polling 開始
- project 選択
- session 作成
- session 切り替え
- active session の表示
- 通常の run 実行（切り詰められた prompt を含む audit log 行も含む）
- resume 失敗後の session 置き換え
- warning と runtime error
</details>

## 🗂️ プロジェクト構成

- `src/coding_agent_telegram/`
  アプリ本体コード

- `tests/`
  テストスイート

- `startup.sh`
  ローカル bootstrap / 起動エントリーポイント

- `src/coding_agent_telegram/resources/.env.example`
  repo 起動と package インストールの両方で使う canonical な environment template

- `pyproject.toml`
  packaging と dependency の設定

## 📦 リリース版の付け方

package version は Git tag から導出されます。

- TestPyPI/testing: `v2026.3.26.dev1`
- PyPI prerelease: `v2026.3.26rc1`
- PyPI stable: `v2026.3.26`

## 📌 メモ

- このプロジェクトは、自分のマシンで agent をローカル実行するユーザー向けです。
- Telegram bot は操作面であり、実行環境そのものではありません。
- 複数の bot を使っていても、1 つの server process でまとめて管理できます。
