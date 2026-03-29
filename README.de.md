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
  <p><strong>Leichtgewichtig, Multi-Bot, Multi-Session, Multi-Tasking, 24/7 AI Coding Agent</strong></p>
  <p>Steuere deinen lokalen AI Coding Agent von überall über Telegram.</p>
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

   ## ✨ Warum dieses Projekt
  - ✅ Leichtgewichtig: keine schweren Frameworks, volle Transparenz
  - ✅ Multi-Bot: mehrere Chats, mehrere Sessions
  - ✅ Telegram zum Steuern von Codex / Copilot CLI verwenden
  - ✅ Antworten und geänderte Dateien bequem in Code-Blöcken prüfen
  - ✅ Folgefragen während eines laufenden Agentenlaufs in die Queue stellen
  - ✅ Unterstützt Text- und Bildeingaben

   ## 🔁 Nahtlos zwischen Geräten und Sessions wechseln

  Starte eine Session in Telegram und setze dieselbe Codex/Copilot CLI-Session später ohne Umwege am Computer fort. Mit `/switch` kannst du auch wieder sauber von Telegram zurück ins Terminal wechseln.
  
  - Nutze `/switch`, um eine lokale Session weiterzuführen
  - Historische Sessions werden ebenfalls unterstützt

   ## 🛠️ Typischer lokaler Ablauf
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

→ Setup per Einzeiler: 
```
curl -fsSL https://raw.githubusercontent.com/daocha/coding-agent-telegram/main/install.sh | bash
```

<table>
   <tr>
   <td width="50%" valign="top">

   ## 🔐 Sicherheit

- Private Chats werden über `ALLOWED_CHAT_IDS` freigegeben
- Pro Projekt ist nur ein aktiver Agent erlaubt, um Konflikte zu reduzieren
- Diffs sensibler Dateien werden ausgeblendet
- API-Schlüssel, Tokens, `.env`-Werte, Zertifikate, SSH-Schlüssel und ähnliche Geheimnisse werden vor dem Senden an Telegram maskiert
- Laufzeitdaten der App bleiben unter `~/.coding-agent-telegram`
- Bestehende Ordner können vor schreibenden Git-Operationen eine Vertrauensbestätigung verlangen
- Keine versteckten externen Aufrufe: Du behältst die Kontrolle
   </td>
   <td width="50%" valign="top">

   ## ✅ Voraussetzungen

Vor dem Start des Servers brauchst du:

- Python 3.9 oder neuer
- Einen Telegram-Bot-Token von _@BotFather_
- Deine Telegram-Chat-ID
- Lokal installiertes Codex CLI und/oder Copilot CLI
- [Codex CLI Installation](https://developers.openai.com/codex/cli)
- [Copilot CLI Installation](https://github.com/features/copilot/cli)
   </td>
   </tr>
</table>

## 🚀 Schnellstart

### Option A: Einzeiliges Bootstrap-Skript
```bash
curl -fsSL https://raw.githubusercontent.com/daocha/coding-agent-telegram/main/install.sh | bash
```

### Option B: Installation über PyPI mit `pip`
```bash
pip install coding-agent-telegram
coding-agent-telegram
```

### Option C: Aus einem geklonten Repository starten
```bash
git clone https://github.com/daocha/coding-agent-telegram
cd coding-agent-telegram
./startup.sh
```

### Bot-Server starten
##### Beim ersten Start legt die App die Env-Datei an und sagt dir, welche Felder du ausfüllen musst.
##### Nach dem Bearbeiten der Env-Datei starte erneut:
```bash
# if you follow Option A or Option B, then run
coding-agent-telegram

# if you follow Option C, then run this again
./startup.sh
```

## 🔑 Telegram-Einrichtung

### Bot-Token holen

1. Öffne Telegram und starte einen Chat mit `@BotFather`.
2. Sende `/newbot`.
3. Folge den Anweisungen für:
   - einen Anzeigenamen
   - einen Bot-Benutzernamen, der auf `bot` endet
4. BotFather gibt dir einen HTTP-API-Token zurück.
5. Trage den Token in `TELEGRAM_BOT_TOKENS` in `~/.coding-agent-telegram/.env_coding_agent_telegram` ein.

### Chat-ID holen

Am zuverlässigsten ist die Telegram-`getUpdates`-API mit deinem eigenen Bot-Token.

1. Starte einen Chat mit deinem Bot und sende z. B. `/start`.
2. Öffne diese URL im Browser und ersetze `<BOT_TOKEN>`:

```text
https://api.telegram.org/bot<BOT_TOKEN>/getUpdates
```

3. Suche im JSON nach dem Objekt `chat`.
4. Kopiere das numerische Feld `id`.
5. Trage den Wert in `ALLOWED_CHAT_IDS` in `~/.coding-agent-telegram/.env_coding_agent_telegram` ein.

Hinweise:

- In privaten Chats ist die Chat-ID meist eine positive Ganzzahl.
- Wenn `getUpdates` leer zurückkommt, sende dem Bot noch einmal eine Nachricht und versuche es erneut.

## 📨 Unterstützte Nachrichtentypen

Der Bot akzeptiert derzeit:

- Textnachrichten
- Fotos
- Codex und Copilot unterstützen aktuell nur Text und Bilder, kein Video.

## 🤖 Telegram-Befehle

<table>
  <tr>
    <td width="250"><code>/provider</code></td>
    <td>Provider für neue Sessions wählen. Die Auswahl wird pro Bot und Chat gespeichert, bis du sie änderst.</td>
  </tr>
  <tr>
    <td width="250"><code>/project &lt;project_folder&gt;</code></td>
    <td>Aktuellen Projektordner setzen. Falls der Ordner nicht existiert, erstellt die App ihn und markiert ihn als vertrauenswürdig. Wenn er bereits existiert und noch nicht vertraut ist, fragt die App nach einer Bestätigung.</td>
  </tr>
  <tr>
    <td width="250"><code>/branch &lt;new_branch&gt;</code></td>
    <td>Eine branch für das aktuelle Projekt vorbereiten oder wechseln. Wenn die branch bereits existiert, nutzt der Bot sie als Quellkandidaten. Andernfalls verwendet er die Standard-branch des Repositorys als Quellkandidaten.</td>
  </tr>
  <tr>
    <td width="250"><code>/branch &lt;origin_branch&gt; &lt;new_branch&gt;</code></td>
    <td>Eine branch mit `<origin_branch>` als Quellkandidaten vorbereiten oder wechseln. Für beide Formen bietet der Bot anschließend nur die Quelloptionen an, die tatsächlich existieren: `local/<branch>` und `origin/<branch>`. Wenn nur eine davon existiert, wird nur diese angezeigt. Wenn keine existiert, meldet der Bot, dass die branch-Quelle fehlt.</td>
  </tr>
  <tr>
    <td width="250"><code>/current</code></td>
    <td>Die aktive Session für den aktuellen Bot und Chat anzeigen.</td>
  </tr>
  <tr>
    <td width="250"><code>/new [session_name]</code></td>
    <td>Eine neue Session für das aktuelle Projekt erstellen. Wenn du keinen Namen angibst, verwendet der Bot die echte Session-ID. Fehlen Provider, Projekt oder branch, führt dich der Bot durch den fehlenden Schritt.</td>
  </tr>
  <tr>
    <td width="250"><code>/switch</code></td>
    <td>Die neuesten Sessions anzeigen, zuerst die neuesten. Die Liste enthält sowohl vom Bot verwaltete Sessions als auch lokale Codex/Copilot CLI-Sessions für das aktuelle Projekt.</td>
  </tr>
  <tr>
    <td width="250"><code>/switch page &lt;number&gt;</code></td>
    <td>Eine andere Seite der gespeicherten Sessions anzeigen.</td>
  </tr>
  <tr>
    <td width="250"><code>/switch &lt;session_id&gt;</code></td>
    <td>Zu einer bestimmten Session per ID wechseln. Wenn du eine lokale CLI-Session auswählst, importiert der Bot sie und setzt dort fort.</td>
  </tr>
  <tr>
    <td width="250"><code>/compact</code></td>
    <td>Aus der aktiven Session eine neue kompakte Session erzeugen und dorthin wechseln.</td>
  </tr>
  <tr>
    <td width="250"><code>/commit &lt;git commands&gt;</code></td>
    <td>Geprüfte `git commit`-bezogene Befehle im Projekt der aktiven Session ausführen. Nur verfügbar, wenn `ENABLE_COMMIT_COMMAND=true`. Schreibende Git-Befehle erfordern ein vertrauenswürdiges Projekt.</td>
  </tr>
  <tr>
    <td width="250"><code>/push</code></td>
    <td>`origin <branch>` für die aktuelle aktive Session pushen. Der Bot fragt vor dem Push nach einer Bestätigung.</td>
  </tr>
  <tr>
    <td width="250"><code>/abort</code></td>
    <td>Den aktuellen Agentenlauf für das aktuelle Projekt abbrechen. Wenn Fragen in der Queue warten, fragt der Bot, ob sie weiter verarbeitet werden sollen.</td>
  </tr>
</table>

<h2>⚙️ Umgebungsvariablen</h2>

<h3>Pfad der Haupt-Env-Datei:</h3>

<table>
  <tr>
    <td><code>CODING_AGENT_TELEGRAM_ENV_FILE</code></td>
    <td>Nutze dies, wenn die App eine bestimmte Env-Datei verwenden soll.</td>
  </tr>
  <tr>
    <td><code>~/.coding-agent-telegram/.env_coding_agent_telegram</code></td>
    <td>Standardpfad der Env-Datei.</td>
  </tr>
  <tr>
    <td><code>./.env_coding_agent_telegram</code></td>
    <td>Wird nur verwendet, wenn diese lokale Datei bereits existiert.</td>
  </tr>
</table>

<h3>Erforderlich</h3>

<table>
  <tr>
    <td width="250"><code>WORKSPACE_ROOT</code></td>
    <td>Übergeordneter Ordner, der deine Projektverzeichnisse enthält.</td>
  </tr>
  <tr>
    <td width="250"><code>TELEGRAM_BOT_TOKENS</code></td>
    <td>Kommagetrennte Telegram-Bot-Tokens.</td>
  </tr>
  <tr>
    <td width="250"><code>ALLOWED_CHAT_IDS</code></td>
    <td>Kommagetrennte Telegram-Chat-IDs privater Chats, die den Bot verwenden dürfen.</td>
  </tr>
</table>

<h3>Häufige Einstellungen</h3>

<table>
  <tr>
    <td width="250"><code>APP_LOCALE</code></td>
    <td>UI-Sprache für gemeinsame Bot-Meldungen und Befehlsbeschreibungen. Unterstützte Werte: <code>en</code>, <code>de</code>, <code>fr</code>, <code>ja</code>, <code>ko</code>, <code>nl</code>, <code>th</code>, <code>vi</code>, <code>zh-CN</code>, <code>zh-HK</code>, <code>zh-TW</code>.</td>
  </tr>
  <tr>
    <td width="250"><code>CODEX_BIN</code></td>
    <td>Befehl zum Starten von Codex CLI. Standard: <code>codex</code>.</td>
  </tr>
  <tr>
    <td width="250"><code>COPILOT_BIN</code></td>
    <td>Befehl zum Starten von Copilot CLI. Standard: <code>copilot</code>.</td>
  </tr>
  <tr>
    <td width="250"><code>CODEX_MODEL</code></td>
    <td>Optionale Model-Überschreibung für Codex. Leer lassen, um das Standardmodell von Codex CLI zu verwenden. Beispiel: <code>gpt-5.4</code> <a href="https://developers.openai.com/codex/models" target="_blank">OpenAI Codex/OpenAI modelle</a></td>
  </tr>
  <tr>
    <td width="250"><code>COPILOT_MODEL</code></td>
    <td>Optionale Model-Überschreibung für Copilot. Leer lassen, um das Standardmodell von Copilot CLI zu verwenden. Beispiele: <code>gpt-5.4</code>, <code>claude-sonnet-4.6</code> <a href="https://docs.github.com/en/copilot/reference/ai-models/supported-models" target="_blank">GitHub Copilot unterstützte modelle</a></td>
  </tr>
  <tr>
    <td width="250"><code>CODEX_APPROVAL_POLICY</code></td>
    <td>An Codex übergebener Freigabemodus. Standard: <code>never</code>.</td>
  </tr>
  <tr>
    <td width="250"><code>CODEX_SANDBOX_MODE</code></td>
    <td>An Codex übergebener Sandbox-Modus. Standard: <code>workspace-write</code>.</td>
  </tr>
  <tr>
    <td width="250"><code>CODEX_SKIP_GIT_REPO_CHECK</code></td>
    <td>Wenn aktiviert, werden Codex-Prüfungen für vertrauenswürdige Repositories immer übersprungen.</td>
  </tr>
  <tr>
    <td width="250"><code>ENABLE_COMMIT_COMMAND</code></td>
    <td>Den Telegram-Befehl <code>/commit</code> aktivieren. Standard: <code>false</code>.</td>
  </tr>
  <tr>
    <td width="250"><code>AGENT_HARD_TIMEOUT_SECONDS</code></td>
    <td>Hartes Zeitlimit für einen einzelnen Agentenlauf. Standard: <code>0</code> (deaktiviert).</td>
  </tr>
  <tr>
    <td width="250"><code>SNAPSHOT_TEXT_FILE_MAX_BYTES</code></td>
    <td>Maximale Dateigröße, die der Bot als Text liest, wenn er Vorher/Nachher-Snapshots für Run-Diffs erstellt. Standard: <code>200000</code>.</td>
  </tr>
  <tr>
    <td width="250"><code>MAX_TELEGRAM_MESSAGE_LENGTH</code></td>
    <td>Maximale Nachrichtengröße, bevor die App Antworten aufteilt. Standard: <code>3000</code>.</td>
  </tr>
  <tr>
    <td width="250"><code>ENABLE_SENSITIVE_DIFF_FILTER</code></td>
    <td>Diffs für sensible Dateien ausblenden. Standard: <code>true</code>.</td>
  </tr>
  <tr>
    <td width="250"><code>ENABLE_SECRET_SCRUB_FILTER</code></td>
    <td>Tokens, Schlüssel, <code>.env</code>-Werte, Zertifikate und ähnliche geheime Ausgaben vor dem Senden an Telegram unkenntlich machen. Standard: <code>true</code> (dringend empfohlen).</td>
  </tr>
  <tr>
    <td width="250"><code>SNAPSHOT_INCLUDE_PATH_GLOBS</code></td>
    <td>Passende Pfade in Diffs immer einschließen. Beispiel: <code>.github/*,.profile.test,.profile.prod</code></td>
  </tr>
  <tr>
    <td width="250"><code>SNAPSHOT_EXCLUDE_PATH_GLOBS</code></td>
    <td>Zusätzliche Diff-Ausschlüsse zusätzlich zu den Standardwerten hinzufügen. Beispiel: <code>.*,personal/*,sensitive*.txt</code> Hinweis: <code>.*</code> erfasst versteckte Pfade, auch Dateien in versteckten Verzeichnissen.</td>
  </tr>
</table>

<h3>Status und Logs</h3>

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

Beispiel:

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

## 🧠 Session-Verwaltung

Sessions sind gebunden an:

- Telegram-Bot
- Telegram-Chat

Dadurch kann dasselbe Telegram-Konto mehrere Bots nutzen, ohne Sessions zu vermischen.

Beispiel:

- Bot A + dein Chat -> Backend-Arbeit
- Bot B + dein Chat -> Frontend-Arbeit
- Bot C + dein Chat -> Infrastruktur-Arbeit

Die aktive Session ist außerdem gebunden an:

- Projektordner
- Provider
- branch-Name, wenn vorhanden

<details>
<summary><b>In jeder Session wird gespeichert:</b></summary>

- Session-Name
- Projektordner
- branch-Name
- Provider
- Zeitstempel
- aktive Session-Auswahl für diesen Bot-/Chat-Bereich
</details>

### 🔓 Workspace-Concurrency-Lock

Pro **Projektordner** kann immer nur ein Agentenlauf aktiv sein, unabhängig davon, welcher Chat oder welcher Telegram-Bot ihn ausgelöst hat.

Das ist etwas anderes als „der Agent verarbeitet noch die aktuelle Frage“:

- **Projekt ist beschäftigt** bedeutet, dass im Workspace bereits ein Agentenlauf aktiv ist
- **Agent ist beschäftigt** bedeutet, dass dieser eine Lauf noch an der aktuellen Anfrage arbeitet

Der Bot erzwingt absichtlich genau einen aktiven Lauf pro Projekt, damit nicht zwei Agenten gleichzeitig in denselben Workspace schreiben. Das vermeidet widersprüchliche Änderungen und reduziert das Risiko von Datenkorruption.

Wenn eine Nachricht ankommt, während bereits ein Agent auf demselben Projekt läuft, antwortet der Bot sofort:

> ⏳ Auf dem Projekt läuft bereits ein Agent. Bitte warte, bis er fertig ist.

Der Lock wird nur im Speicher gehalten, nicht auf der Festplatte. Er wird automatisch freigegeben, wenn der Agent fertig ist, fehlschlägt oder der Server neu startet. Es gibt keine veralteten Lock-Dateien nach einem Absturz.

### 💬 Fragen in der Queue

Wenn im aktuellen Projekt bereits ein Agentenlauf aktiv ist, werden spätere Textnachrichten nicht abgewiesen. Sie landen stattdessen in einer Queue:

- die neue Frage wird an eine Datei für wartende Fragen auf der Festplatte angehängt
- der aktuelle Agent arbeitet weiter an der vorherigen Anfrage
- wenn dieser Lauf normal endet, beginnt der Bot automatisch mit der Verarbeitung der wartenden Fragen

Wird der aktuelle Lauf abgebrochen und es warten noch Fragen, setzt der Bot nicht automatisch fort. Er fragt dann, ob die verbleibenden Fragen weiter verarbeitet werden sollen. Du kannst sie gebündelt oder einzeln verarbeiten.

## ⚠️ Diff (Dateiänderungen)

_Während jedes Agentenlaufs erstellt der Bot außerdem einen leichten Vorher/Nachher-Snapshot des Projekts, damit er geänderte Dateien zusammenfassen und Diffs an Telegram senden kann. Dieser Snapshot wird von der Bot-App selbst erstellt, nicht von Codex oder Copilot._

**Hinweise zum Snapshot:**

- die App durchsucht das Projektverzeichnis vor und nach dem Lauf
- bei normalen Textdateien bevorzugt die App den Snapshot-Diff dieses Laufs statt eines Git-Head-Diffs
- übliche Abhängigkeits-, Cache- und Laufzeitverzeichnisse werden ebenfalls übersprungen
- Binärdateien und Dateien größer als `SNAPSHOT_TEXT_FILE_MAX_BYTES` werden nicht als Text geladen
- bei sehr großen Projekten kann dieser zusätzliche Scan spürbaren I/O- und Speicher-Overhead erzeugen
- wenn ein Snapshot eine Datei nicht als Text abbilden kann, greift die App wenn möglich auf `git diff` zurück
- bei großen oder nicht-textuellen Dateien kann der Diff trotzdem ausgelassen und durch eine kurze Hinweisnachricht ersetzt werden

Snapshot-Ausschlussregeln liegen in den Paketressourcen:

- `src/coding_agent_telegram/resources/snapshot_excluded_dir_names.txt`
- `src/coding_agent_telegram/resources/snapshot_excluded_dir_globs.txt`
- `src/coding_agent_telegram/resources/snapshot_excluded_file_globs.txt`

Du kannst diese Standardwerte in der Env-Datei überschreiben, ohne das installierte Paket zu ändern:

- `SNAPSHOT_INCLUDE_PATH_GLOBS`
  Passende Pfade in Diffs immer einschließen.
  Beispiel: `.github/*,.profile.test,.profile.prod`

- `SNAPSHOT_EXCLUDE_PATH_GLOBS`
  Zusätzliche Diff-Ausschlüsse zusätzlich zu den Paket-Standards hinzufügen.
  Beispiel: `.*,personal/*,sensitive*.txt`
  Hinweis: `.*` erfasst versteckte Pfade, einschließlich Dateien in versteckten Verzeichnissen.

Wenn Include- und Exclude-Regeln beide passen, gewinnt Include.

## 🌿 Branch-Verhalten

Der Bot behandelt Projekt und branch als zusammengehörig.

- die Wahl eines Projekts wählt nicht stillschweigend eine andere branch
- wenn eine branch-Auswahl nötig ist, fordert dich der Bot dazu auf
- wenn branch-Informationen in Session-bezogenen Meldungen ausgegeben werden, werden Projekt und branch gemeinsam angezeigt

Wenn du eine branch erstellst oder wechselst, führt dich der Bot explizit durch die Quelle:

- `local/<branch>` bedeutet: lokale branch als Quelle verwenden
- `origin/<branch>` bedeutet: zuerst von der Remote-branch aktualisieren und dann wechseln

Wenn der Bot feststellt, dass die in der Session gespeicherte branch und die aktuelle Repository-branch nicht übereinstimmen, macht er nicht blind weiter. Er fragt dich, welche branch verwendet werden soll:

- gespeicherte Session-branch behalten
- aktuelle Repository-branch behalten

Wenn die bevorzugte Quell-branch fehlt, bietet der Bot stattdessen Fallback-Quellen auf Basis der Standard-branch und der aktuellen branch an, statt dich mit einem rohen Git-Fehler allein zu lassen.

## 🔐 Git-Vertrauensverhalten

- Bestehende Ordner folgen `CODEX_SKIP_GIT_REPO_CHECK`
- Ordner, die über `/project <name>` erstellt werden, werden von dieser App als vertrauenswürdig markiert
- Bereits bestehende Ordner, die über `/project <name>` ausgewählt werden, bleiben untrusted, bis du das Vertrauen im Telegram-Prompt bestätigst
- Neu erstellte Projektordner können daher sofort verwendet werden
- `/commit` kann mit `ENABLE_COMMIT_COMMAND` komplett deaktiviert werden
- Schreibende `/commit`-Operationen sind nur für vertrauenswürdige Projekte erlaubt

## 🪵 Logs

Logs werden **sowohl auf stdout als auch in eine rotierende Log-Datei** geschrieben unter:

- `~/.coding-agent-telegram/logs` (Rotation bei 10 MB, 3 Backups)

> **Hinweis:** Weil Nachrichten sowohl auf stdout als auch in die Log-Datei geschrieben werden, erscheinen sie doppelt, wenn du gleichzeitig das Terminal beobachtest
> **und** die Log-Datei per `tail -f ~/.coding-agent-telegram/logs/coding-agent-telegram.log` verfolgst.
> Das ist erwartetes Verhalten. Beobachte entweder das eine oder das andere.

<details>
<summary><b>Typische geloggte Ereignisse</b></summary>

- Bot-Start und Polling-Start
- Projektauswahl
- Session-Erstellung
- Session-Wechsel
- Anzeige der aktiven Session
- normale Laufausführung (einschließlich Audit-Log-Zeile mit gekürztem Prompt)
- Session-Ersetzung nach fehlgeschlagenem Resume
- Warnungen und Laufzeitfehler
</details>

## 🗂️ Projektstruktur

- `src/coding_agent_telegram/`
  Hauptanwendungscode

- `tests/`
  Test-Suite

- `startup.sh`
  Lokaler Bootstrap- und Startup-Einstiegspunkt

- `src/coding_agent_telegram/resources/.env.example`
  Kanonische Umgebungs-Vorlage, die sowohl vom Repo-Start als auch von Paketinstallationen verwendet wird

- `pyproject.toml`
  Packaging- und Abhängigkeitskonfiguration

## 📦 Release-Versionierung

Paketversionen werden aus Git-Tags abgeleitet.

- TestPyPI/Testen: `v2026.3.26.dev1`
- PyPI-Prerelease: `v2026.3.26rc1`
- PyPI-Stable: `v2026.3.26`

## 📌 Hinweise

- Dieses Projekt ist für Nutzer gedacht, die die Agenten lokal auf ihrem eigenen Rechner ausführen.
- Der Telegram-Bot ist eine Steueroberfläche, nicht die Ausführungsumgebung selbst.
- Wenn du mehrere Bots betreibst, können sie alle von einem einzigen Serverprozess verwaltet werden.
