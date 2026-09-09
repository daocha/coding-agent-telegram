<div align="center">
  <img width="600" alt="Coding Agent Telegram" src="https://github.com/user-attachments/assets/aca106f8-0d64-40e9-94d9-2542da5dfde9" />
  <h1>Claude Code / Codex / Copilot Coding Agent Telegram 🚀</h1>
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
  - ✅ Telegram zum Steuern von Codex / Copilot / Claude Code CLI verwenden
  - ✅ Antworten und geänderte Dateien bequem in Code-Blöcken prüfen
  - ✅ Folgefragen während eines laufenden Agentenlaufs in die Queue stellen
  - ✅ Akzeptiert ✏️ Text-, 🌄 Bild- und 🎙️ Sprachnachrichten

   ## 🔁 Nahtlos zwischen Geräten und Sessions wechseln

  Starte eine Session in Telegram und setze dieselbe Codex/Copilot/Claude Code CLI-Session später ohne Umwege am Computer fort. Mit `/switch` kannst du auch wieder sauber von Telegram zurück ins Terminal wechseln.
  
  - Nutze `/switch`, um eine lokale Session weiterzuführen
  - Historische Sessions werden ebenfalls unterstützt

   ## 🛠️ Typischer lokaler Ablauf
   ```bash
   coding-agent-telegram # oder ./startup.sh ausführen
   ```

   ##### In Telegram:

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

→ Setup per Einzeiler: 
```
curl -fsSL https://raw.githubusercontent.com/daocha/coding-agent-telegram/main/install.sh | bash
```

<table>
   <tr>
   <td width="65%" valign="top">

   ## 🔐 Sicherheit

- Whitelist für private Chats mit `ALLOWED_CHAT_IDS`
- Pro Projekt nur ein aktiver Agent, um Konflikte beim Schreiben zu reduzieren
- Diffs sensibler Dateien werden ausgeblendet
- API-Schlüssel, Tokens, `.env`-Werte, Zertifikate, SSH-Schlüssel und ähnliche geheime Ausgaben werden vor dem Senden an Telegram maskiert
- Laufzeitdaten der App bleiben unter `~/.coding-agent-telegram`
- Bestehende Ordner können vor schreibenden Git-Operationen eine Vertrauensbestätigung verlangen
- Der Server führt keine versteckten externen Aufrufe aus. Alles bleibt unter deiner Kontrolle.
- Funktioniert gut mit dem Codex Sandbox mode; du musst `danger-full-access` nicht freigeben
- Die Claude Code-Integration unterstützt konfigurierbare Permission-Modi sowie Allow-/Deny-Listen für Tools
   </td>
   <td width="35%" valign="top">

   ## ✅ Voraussetzungen

Vor dem Start des Servers brauchst du:

- Python 3.9 oder neuer
- Einen Telegram-Bot-Token von _@BotFather_
- Deine Telegram-Chat-ID
- Lokal installiertes Codex CLI und/oder Copilot CLI und/oder Claude Code CLI
- [Codex CLI Installation](https://developers.openai.com/codex/cli) / [Copilot CLI Installation](https://github.com/features/copilot/cli) / [Claude Code CLI Installation](https://code.claude.com/docs/en/quickstart)
- [Optional] Whisper, ffmpeg
   </td>
   </tr>
</table>

## 🦞 Warum brauche ich das, wenn ich Openclaw bereits habe?
Openclaw bietet dir sehr umfassende Funktionen und hat mit Pi-Agent bereits eine integrierte Agent-Loop. Es ist vielseitig und für breitere Einsatzfälle gedacht. Ich mag Openclaw ebenfalls und habe selbst damit entwickelt. Für Coding ist es aber nicht immer die beste Wahl, weil der eingebaute große System-Prompt und der zusätzliche Kontext eher ablenken können. Claude Code / Codex / Copilot sind fürs Coding oft effizienter, präziser, weniger abgelenkt und direkter. Dieses Projekt bleibt bewusst einfach und integriert nur Codex / Copilot / Claude Code CLI. Du delegierst also direkt an Codex / Copilot / Claude Code.

## 🆚 Warum brauche ich coding-agent-telegram, wenn ich bereits Claude Code + Telegram Plugin habe?

| Funktion | Claude Code + offizielles Telegram Plugin | coding-agent-telegram (mit Claude-Unterstützung) |
|----------|--------------------------------------------|--------------------------------------------------|
| KI-Chat über Telegram | ✅ | ✅ |
| Lokalen Code bearbeiten und Befehle ausführen | ✅ | ✅ |
| Erfordert eine bereits laufende CLI-Sitzung | **Ja** | **Nein** (startet oder setzt Sitzungen automatisch fort) |
| Unterstützung mehrerer KI-Anbieter | ❌ Nur Claude | ✅ Claude Code, Codex CLI, GitHub Copilot CLI |
| Projektverwaltung über Telegram | ❌ | ✅ `/project` |
| Branch-Verwaltung über Telegram | Manuelle Git-Befehle | ✅ `/branch`-Workflow |
| Sitzungen erstellen und wechseln | Auf die aktive Claude-Sitzung beschränkt | ✅ `/new`, `/switch`, `/current`, `/compact` |
| Vorhandene lokale CLI-Sitzungen fortsetzen | ❌ | ✅ |
| Sitzungen geräteübergreifend fortsetzen | Eingeschränkt | ✅ |
| Schutz vor gleichzeitigen Änderungen im Workspace | ❌ | ✅ Verhindert, dass mehrere Agents gleichzeitig dasselbe Projekt bearbeiten |
| Aufgabenwarteschlange bei ausgelastetem Agent | ❌ | ✅ |
| Unabhängige Dateisystem-Snapshots und Diffs | ❌ | ✅ |
| Strukturierte Datei-Diffs direkt in Telegram anzeigen | ❌ | ✅ |
| Filterung von Secrets und sensiblen Diffs | ❌ | ✅ |
| Integrierter Git-Workflow (pull / push / commit) | Manuell | ✅ |
| Unterstützung mehrerer Bots | Mehrere Instanzen erforderlich | ✅ Verwaltung über einen einzigen Server |
| Projektbezogene Statusverwaltung | ❌ | ✅ |
| Anbieterunabhängige Architektur | ❌ | ✅ |

> **Wichtigster Unterschied**
>
> Das offizielle Claude Code Telegram Plugin verbindet Telegram mit **einer bereits laufenden Claude Code-Sitzung**.
>
> **coding-agent-telegram** fungiert als **Telegram-Kontrollzentrale**, die Projekte, Branches, Sitzungen, Git-Workflows und mehrere Coding-Agents (Claude Code, Codex CLI, GitHub Copilot CLI) über eine einzige Oberfläche verwaltet.

### 🏛️ Architektur

#### Claude Code + Telegram Plugin

```text
Telegram
    │
    ▼
Claude Code Channel
    │
    ▼
Eine laufende Claude Code-Sitzung
```

#### coding-agent-telegram

```text
Telegram
    │
    ▼
coding-agent-telegram
    │
    ├── Claude Code
    ├── Codex CLI
    └── GitHub Copilot CLI
           │
           ▼
Projekt • Branch • Sitzung • Warteschlange • Git • Diff • Secret-Filter
```

## 🚀 Schnellstart

### Variante A: Einzeiliges Bootstrap-Skript
```bash
curl -fsSL https://raw.githubusercontent.com/daocha/coding-agent-telegram/main/install.sh | bash
```

### Variante B: Installation über PyPI mit `pip`
```bash
pip install coding-agent-telegram
coding-agent-telegram
```

### Variante C: Aus einem geklonten Repository starten
```bash
git clone https://github.com/daocha/coding-agent-telegram
cd coding-agent-telegram
./startup.sh
```

### 🌐 Bot-Server starten
##### Beim ersten Start legt die App die Env-Datei an und sagt dir, welche Felder du ausfüllen musst.
##### Nach dem Bearbeiten der Env-Datei starte erneut:
```bash
# wenn du Variante A oder Variante B verwendest, dann ausführen
coding-agent-telegram

# wenn du Variante C verwendest, dann dies erneut ausführen
./startup.sh
```

## 🎙️ [Optional] Sprach-zu-Text-Funktion: lokale OpenAI-Whisper-Voraussetzungen vorbereiten

Damit aktivierst du optional lokale Whisper-basierte Sprach-zu-Text-Unterstützung für Telegram-Sprachnotizen. Audiodateien sind auf maximal `20 MB` begrenzt.

```bash
# wenn du per pip oder per Einzeiler install.sh installiert hast
coding-agent-telegram-stt-install

# wenn du aus einem geklonten Repository startest
./install-stt.sh
```

Empfohlene Env-Einstellungen:

```text
ENABLE_OPENAI_WHISPER_SPEECH_TO_TEXT=true
OPENAI_WHISPER_MODEL=base
OPENAI_WHISPER_TIMEOUT_SECONDS=120
```

Hinweise:

- Whisper lädt das ausgewählte Modell beim ersten Aufruf automatisch nach `~/.cache/whisper` herunter.
- Wenn du `OPENAI_WHISPER_MODEL=turbo` wählst, ist es wahrscheinlicher, dass die erste Sprachnachricht das Zeitlimit erreicht, während `large-v3-turbo.pt` noch heruntergeladen wird.
- Nach der Transkription einer Sprachnachricht sendet der Bot das erkannte Transkript zuerst zurück an Telegram und gibt es danach an den Agenten weiter. So lassen sich Erkennungsfehler leichter prüfen.

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
- Sprachnachrichten und Audiodateien, wenn `ENABLE_OPENAI_WHISPER_SPEECH_TO_TEXT=true` gesetzt ist und die lokalen Whisper-Voraussetzungen installiert sind
- Codex- und Claude Code-Sessions unterstützen Text und Bilder; Copilot-Sessions unterstützen aktuell nur Text. Video wird von keinem Provider unterstützt.

## 🤖 Telegram-Befehle

<table>
  <tr>
    <td width="332"><code>/provider</code></td>
    <td>Provider für neue Sessions wählen. Die Auswahl wird pro Bot und Chat gespeichert, bis du sie änderst.</td>
  </tr>
  <tr>
    <td width="332"><code>/project &lt;project_folder&gt;</code></td>
    <td>Aktuellen Projektordner setzen. Falls der Ordner nicht existiert, erstellt die App ihn und markiert ihn als vertrauenswürdig. Wenn er bereits existiert und noch nicht vertraut ist, fragt die App nach einer Bestätigung.</td>
  </tr>
  <tr>
    <td width="332"><code>/branch &lt;new_branch&gt;</code></td>
    <td>Eine branch für das aktuelle Projekt vorbereiten oder wechseln. Wenn die branch bereits existiert, nutzt der Bot sie als Quellkandidaten. Andernfalls verwendet er die Standard-branch des Repositorys als Quellkandidaten.</td>
  </tr>
  <tr>
    <td width="332"><code>/branch &lt;origin_branch&gt; &lt;new_branch&gt;</code></td>
    <td>Eine branch mit <code>&lt;origin_branch&gt;</code> als Quellkandidaten vorbereiten oder wechseln. Für beide Formen bietet der Bot anschließend nur die Quelloptionen an, die tatsächlich existieren: <code>local/&lt;branch&gt;</code> und <code>origin/&lt;branch&gt;</code>. Wenn nur eine davon existiert, wird nur diese angezeigt. Wenn keine existiert, meldet der Bot, dass die branch-Quelle fehlt.</td>
  </tr>
  <tr>
    <td width="332"><code>/current</code></td>
    <td>Die aktive Session für den aktuellen Bot und Chat anzeigen.</td>
  </tr>
  <tr>
    <td width="332"><code>/new [session_name]</code></td>
    <td>Eine neue Session für das aktuelle Projekt erstellen. Wenn du keinen Namen angibst, verwendet der Bot die echte Session-ID. Fehlen Provider, Projekt oder branch, führt dich der Bot durch den fehlenden Schritt.</td>
  </tr>
  <tr>
    <td width="332"><code>/switch</code></td>
    <td>Die neuesten Sessions anzeigen, zuerst die neuesten. Die Liste enthält sowohl vom Bot verwaltete Sessions als auch lokale Codex/Copilot/Claude Code CLI-Sessions für das aktuelle Projekt.</td>
  </tr>
  <tr>
    <td width="332"><code>/switch page &lt;number&gt;</code></td>
    <td>Eine andere Seite der gespeicherten Sessions anzeigen.</td>
  </tr>
  <tr>
    <td width="332"><code>/switch &lt;session_id&gt;</code></td>
    <td>Zu einer bestimmten Session per ID wechseln. Wenn du eine lokale CLI-Session auswählst, importiert der Bot sie und setzt dort fort.</td>
  </tr>
  <tr>
    <td width="332"><code>/compact</code></td>
    <td>Aus der aktiven Session eine neue kompakte Session erzeugen und dorthin wechseln.</td>
  </tr>
  <tr>
    <td width="332"><code>/commit &lt;git commands&gt;</code></td>
    <td>Geprüfte <code>git commit</code>-bezogene Befehle im Projekt der aktiven Session ausführen. Nur verfügbar, wenn <code>ENABLE_COMMIT_COMMAND=true</code>. Schreibende Git-Befehle erfordern ein vertrauenswürdiges Projekt.</td>
  </tr>
  <tr>
    <td width="332"><code>/diff</code></td>
    <td>Geänderte Dateinamen im Projekt der aktiven Session anzeigen, getrennt nach versionierten und nicht versionierten Dateien. Für versionierte Dateien gibt es Inline-Buttons zum Öffnen des jeweiligen Diffs.</td>
  </tr>
  <tr>
    <td width="332"><code>/pull</code></td>
    <td>Nach Bestätigung <code>origin</code> in den Branch der aktiven Session pullen. Wenn zutreffend, aktualisiert der Bot zusätzlich den Standard-Branch.</td>
  </tr>
  <tr>
    <td width="332"><code>/push</code></td>
    <td><code>origin &lt;branch&gt;</code> für die aktuelle aktive Session pushen. Der Bot fragt vor dem Push nach einer Bestätigung.</td>
  </tr>
  <tr>
    <td width="332"><code>/abort</code></td>
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
    <td width="332"><code>WORKSPACE_ROOT</code></td>
    <td>Übergeordneter Ordner, der deine Projektverzeichnisse enthält.</td>
  </tr>
  <tr>
    <td width="332"><code>TELEGRAM_BOT_TOKENS</code></td>
    <td>Kommagetrennte Telegram-Bot-Tokens.</td>
  </tr>
  <tr>
    <td width="332"><code>ALLOWED_CHAT_IDS</code></td>
    <td>Kommagetrennte Telegram-Chat-IDs privater Chats, die den Bot verwenden dürfen.</td>
  </tr>
</table>

<h3>Häufige Einstellungen</h3>

<table>
  <tr>
    <td width="332"><code>APP_LOCALE</code></td>
    <td>UI-Sprache für gemeinsame Bot-Meldungen und Befehlsbeschreibungen. Unterstützte Werte: <code>en</code>, <code>de</code>, <code>fr</code>, <code>ja</code>, <code>ko</code>, <code>nl</code>, <code>th</code>, <code>vi</code>, <code>zh-CN</code>, <code>zh-HK</code>, <code>zh-TW</code>.</td>
  </tr>
  <tr>
    <td><code>DEFAULT_AGENT_PROVIDER</code></td>
    <td>Standard-Provider für neue Sessions: <code>codex</code>, <code>copilot</code> oder <code>claude</code>. Standard: <code>codex</code>.</td>
  </tr>
  <tr>
    <td width="332"><code>CODEX_BIN</code></td>
    <td>Befehl zum Starten von Codex CLI. Die Anwendung versucht beim Initialisieren der <code>.env_coding_agent_telegram</code>-Datei, den lokal installierten Codex-Pfad automatisch zu erkennen. Alternativ können Sie mit <code>which codex</code> den Pfad anzeigen.</td>
  </tr>
  <tr>
    <td width="332"><code>COPILOT_BIN</code></td>
    <td>Befehl zum Starten von Copilot CLI. Die Anwendung versucht beim Initialisieren der <code>.env_coding_agent_telegram</code>-Datei, den lokal installierten Copilot-Pfad automatisch zu erkennen. Alternativ können Sie mit <code>which copilot</code> den Pfad anzeigen.</td>
  </tr>
  <tr>
    <td><code>CLAUDE_BIN</code></td>
    <td>Befehl zum Starten von Claude Code CLI. Die Anwendung versucht beim Initialisieren der <code>.env_coding_agent_telegram</code>-Datei, den lokal installierten Claude-Pfad automatisch zu erkennen. Alternativ können Sie mit <code>which claude</code> den Pfad anzeigen.</td>
  </tr>
  <tr>
    <td width="332"><code>CODEX_MODEL</code></td>
    <td>Optionale Model-Überschreibung für Codex. Leer lassen, um das Standardmodell von Codex CLI zu verwenden. Beispiel: <code>gpt-5.4</code> <a href="https://developers.openai.com/codex/models" target="_blank">OpenAI Codex/OpenAI modelle</a></td>
  </tr>
  <tr>
    <td width="332"><code>COPILOT_MODEL</code></td>
    <td>Optionale Model-Überschreibung für Copilot. Leer lassen, um das Standardmodell von Copilot CLI zu verwenden. Beispiele: <code>gpt-5.4</code>, <code>claude-sonnet-4.6</code> <a href="https://docs.github.com/en/copilot/reference/ai-models/supported-models" target="_blank">GitHub Copilot unterstützte modelle</a></td>
  </tr>
  <tr>
    <td><code>CLAUDE_MODEL</code></td>
    <td>Optionale Model-Überschreibung für Claude Code.
    Leer lassen, um das Standardmodell von Claude Code CLI zu verwenden.
    Beispiele: <code>sonnet</code>, <code>opus</code>, <code>haiku</code>
    <a href="https://code.claude.com/docs/en/model-config" target="_blank">Claude Code Modellkonfiguration</a>
    </td>
  </tr>
  <tr>
    <td width="332"><code>CODEX_APPROVAL_POLICY</code></td>
    <td>An Codex übergebener Freigabemodus. Standard: <code>never</code>.</td>
  </tr>
  <tr>
    <td width="332"><code>CODEX_SANDBOX_MODE</code></td>
    <td>An Codex übergebener Sandbox-Modus. Standard: <code>workspace-write</code>.</td>
  </tr>
  <tr>
    <td width="332"><code>CODEX_SKIP_GIT_REPO_CHECK</code></td>
    <td>Wenn aktiviert, werden Codex-Prüfungen für vertrauenswürdige Repositories immer übersprungen.</td>
  </tr>
  <tr>
    <td><code>CLAUDE_PERMISSION_MODE</code></td>
    <td>An Claude Code übergebener Permission-Modus. Einer von <code>default</code>, <code>acceptEdits</code>, <code>plan</code>, <code>auto</code>, <code>dontAsk</code>, <code>bypassPermissions</code>, <code>manual</code>. Standard: <code>bypassPermissions</code> (vollständig autonom, da kein interaktives Terminal zum Bestätigen von Prompts vorhanden ist).</td>
  </tr>
  <tr>
    <td><code>CLAUDE_ALLOWED_TOOLS</code></td>
    <td>Kommagetrennte Allowlist für Claude Code-Tools, nach der Permission-Regel-Syntax von Claude Code. Beispiel: <code>Read,Edit,Bash(git *)</code></td>
  </tr>
  <tr>
    <td><code>CLAUDE_DISALLOWED_TOOLS</code></td>
    <td>Kommagetrennte Denylist für Claude Code-Tools. Beispiel: <code>Bash(rm *)</code></td>
  </tr>
  <tr>
    <td width="332"><code>ENABLE_COMMIT_COMMAND</code></td>
    <td>Den Telegram-Befehl <code>/commit</code> aktivieren. Standard: <code>false</code>.</td>
  </tr>
  <tr>
    <td width="332"><code>AGENT_HARD_TIMEOUT_SECONDS</code></td>
    <td>Hartes Zeitlimit für einen einzelnen Agentenlauf. Standard: <code>0</code> (deaktiviert).</td>
  </tr>
  <tr>
    <td width="332"><code>LONG_GAP_WARNING_ENABLED</code></td>
    <td>Warnt, bevor eine Sitzung fortgesetzt wird, die lange im Leerlauf war <em>und</em> genug Kontext angesammelt hat, dass ein erneutes Verarbeiten teuer wäre, dass der Prompt-Cache des Anbieters wahrscheinlich abgelaufen ist — mit Schaltflächen zum vorherigen Komprimieren oder trotzdem Fortsetzen. Standard: <code>true</code>. Siehe FAQ weiter unten.</td>
  </tr>
  <tr>
    <td width="332"><code>CLAUDE_LONG_GAP_SECONDS</code></td>
    <td>Leerlaufschwelle in Sekunden, ab der die Warnung für Claude-Code-Sitzungen ausgelöst wird. Standard: <code>3600</code> (1 Stunde, entsprechend dem erweiterten Prompt-Cache-Fenster von Claude Code).</td>
  </tr>
  <tr>
    <td width="332"><code>CODEX_LONG_GAP_SECONDS</code></td>
    <td>Leerlaufschwelle in Sekunden, ab der die Warnung für Codex-Sitzungen ausgelöst wird. Standard: <code>3600</code> (1 Stunde, wie bei Claude; OpenAI dokumentiert für Codex keine cache-verfallszeit basierend auf Leerlauf, und Codex' eigener Cache ist ohnehin meist kurzlebiger als der von Claude, sodass ein Angleichen an Claudes Schwelle keine Genauigkeit kostet — kombiniert mit dem Größen-Gate, damit kleine Sitzungen nicht nerven).</td>
  </tr>
  <tr>
    <td width="332"><code>COPILOT_LONG_GAP_SECONDS</code></td>
    <td>Leerlaufschwelle in Sekunden, ab der die Warnung für Copilot-Sitzungen ausgelöst wird. Standard: <code>0</code> (deaktiviert). GitHubs eigene Dokumentation besagt, dass die Copilot-CLI kein Inaktivitäts-Timeout hat und ihren Kontext bereits nativ selbst komprimiert (bei ~80–95 % Auslastung) — hier gibt es kein leerlaufbezogenes Risiko zu warnen, daher verlässt sich diese App auf Copilots eigenen Mechanismus, statt einen zu erfinden, der nicht existiert. Setze einen positiven Wert, um trotzdem einen leerlaufbasierten Hinweis für Copilot zu aktivieren.</td>
  </tr>
  <tr>
    <td width="332"><code>SNAPSHOT_TEXT_FILE_MAX_BYTES</code></td>
    <td>Maximale Dateigröße, die der Bot als Text liest, wenn er Vorher/Nachher-Snapshots für Run-Diffs erstellt. Standard: <code>200000</code>.</td>
  </tr>
  <tr>
    <td width="332"><code>MAX_TELEGRAM_MESSAGE_LENGTH</code></td>
    <td>Maximale Nachrichtengröße, bevor die App Antworten aufteilt. Standard: <code>3000</code>.</td>
  </tr>
  <tr>
    <td width="332"><code>ENABLE_SENSITIVE_DIFF_FILTER</code></td>
    <td>Diffs für sensible Dateien ausblenden. Standard: <code>true</code>.</td>
  </tr>
  <tr>
    <td width="332"><code>ENABLE_SECRET_SCRUB_FILTER</code></td>
    <td>Tokens, Schlüssel, <code>.env</code>-Werte, Zertifikate und ähnliche geheime Ausgaben vor dem Senden an Telegram unkenntlich machen. Standard: <code>true</code> (dringend empfohlen).</td>
  </tr>
  <tr>
    <td width="332"><code>SNAPSHOT_INCLUDE_PATH_GLOBS</code></td>
    <td>Passende Pfade in Diffs immer einschließen. Beispiel: <code>.github/*,.profile.test,.profile.prod</code></td>
  </tr>
  <tr>
    <td width="332"><code>SNAPSHOT_EXCLUDE_PATH_GLOBS</code></td>
    <td>Zusätzliche Diff-Ausschlüsse zusätzlich zu den Standardwerten hinzufügen. Beispiel: <code>.*,personal/*,sensitive*.txt</code> Hinweis: <code>.*</code> erfasst versteckte Pfade, auch Dateien in versteckten Verzeichnissen.</td>
  </tr>
</table>




<h3>Spracherkennung</h3>

<table>
  <tr>
    <td width="332"><code>ENABLE_OPENAI_WHISPER_SPEECH_TO_TEXT</code></td>
    <td>Standard: <code>false</code>. Wenn <code>true</code>, werden Sprachnachrichten und Audiodateien erkannt. Das System prüft die erforderlichen Binärdateien oder Bibliotheken und fordert zur Installation auf, falls etwas fehlt.</td>
  </tr>
  <tr>
    <td><code>OPENAI_WHISPER_MODEL</code></td>
    <td>Modell für Whisper STT. Standard: <code>base</code><br />Verfügbare Modelle: <code>tiny</code> ca. <code>72 MB</code>, <code>base</code> ca. <code>139 MB</code>, <code>large-v3-turbo</code> ca. <code>1.5 GB</code><br />Modelle werden bei der ersten Sprachnachricht automatisch heruntergeladen. Empfehlung: <code>base</code> für den allgemeinen Gebrauch. Wenn du bessere Genauigkeit und Qualität willst, kannst du <code>turbo</code> ausprobieren.</td>
  </tr>
  <tr>
    <td><code>OPENAI_WHISPER_TIMEOUT_SECONDS</code></td>
    <td>Standard: <code>120</code>. Timeout für den STT-Prozess. Normalerweise ist die Verarbeitung schnell genug. Wenn du jedoch <code>turbo</code> wählst, kann der erste Sprachaufruf während des Modelldownloads je nach Internetgeschwindigkeit das Timeout überschreiten.</td>
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
    <td>Sicherungsdatei für den Status.</td>
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
CLAUDE_BIN=claude
CODEX_APPROVAL_POLICY=never
CODEX_SANDBOX_MODE=workspace-write
CLAUDE_PERMISSION_MODE=bypassPermissions
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

_Während jedes Agentenlaufs erstellt der Bot außerdem einen leichten Vorher/Nachher-Snapshot des Projekts, damit er geänderte Dateien zusammenfassen und Diffs an Telegram senden kann. Dieser Snapshot wird von der Bot-App selbst erstellt, nicht von Codex, Copilot oder Claude Code._

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

- <code>local/&lt;branch&gt;</code> bedeutet: lokale branch als Quelle verwenden
- <code>origin/&lt;branch&gt;</code> bedeutet: zuerst von der Remote-branch aktualisieren und dann wechseln

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

## 🪵 Protokolle

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

## 📦 Veröffentlichung-Versionierung

Paketversionen werden aus Git-Tags abgeleitet.

- TestPyPI/Testen: `v2026.3.26.dev1`
- PyPI-Prerelease: `v2026.3.26rc1`
- PyPI-Stable: `v2026.3.26`

## ❓ FAQ / Fehlerbehebung

<details>
<summary><b>Warum zeigt <code>claude --resume</code> in einem normalen Terminal keine von Telegram erstellten Sitzungen an?</b></summary>

Das ist erwartetes Verhalten der Claude-Code-CLI, kein Fehler in dieser App.

Von diesem Bot erstellte Sitzungen laufen über den Headless-Modus `-p`/print von Claude Code. Claude Code markiert jede so gestartete Sitzung im Transkript mit `entrypoint: "sdk-cli"`, im Gegensatz zu `entrypoint: "cli"` für eine Sitzung, die du direkt im Terminal durch Eingabe von `claude` startest. Der interaktive `claude --resume`-Picker (ohne Sitzungs-ID) listet nur Sitzungen mit `cli`-Entrypoint auf — er blendet Headless-/SDK-gesteuerte Läufe bewusst aus und behandelt sie als Automatisierungs-Output statt als Unterhaltungen, die von Hand fortgesetzt werden sollen.

Die Sitzungsdaten selbst sind weder verloren noch anders — es handelt sich um eine ganz normale, vollständig fortsetzbare Claude-Code-Sitzung, gespeichert unter `~/.claude/projects/<encoded-project-path>/<session-id>.jsonl`. Sobald du die ID hast, kannst du sie direkt fortsetzen:

```bash
claude --resume <session-id>
```

Genau deshalb bringt diese App eine eigene Sitzungserkennung mit (verwendet von `/switch`), statt sich auf den nativen Picker zu verlassen — sie durchsucht die JSONL-Dateien direkt und gleicht sie über den Projektpfad ab, sodass von Telegram erstellte Sitzungen dort auftauchen, obwohl sie in einem einfachen `claude --resume` nie erscheinen.

Codex und Copilot machen diesen Unterschied zwischen interaktiv und Headless in ihren eigenen Resume-/Listenbefehlen nicht, weshalb Sitzungen dieser Anbieter in einem normalen Terminal weiterhin ganz normal auftauchen.
</details>

<details>
<summary><b>Verbraucht diese App mehr Tokens als die direkte Nutzung des Claude-Code-Terminals?</b></summary>

Nicht wegen eines grundsätzlichen Unterschieds im Overhead pro Aufruf — Headless (`-p`) und interaktives Claude Code nutzen dasselbe zugrunde liegende Protokoll und dieselbe Preisgestaltung. In der Praxis kann 24/7-Telegram-Nutzung aber spürbar mehr Tokens verbrauchen als typische Terminal-Nutzung, aus zwei sich verstärkenden Gründen:

- **Sitzungen können unbegrenzt wachsen.** Da der Bot bequem dieselbe Sitzung über Stunden oder Tage hinweg fortsetzt, kann eine Sitzung Hunderte von Turns und Megabytes an Transkript ansammeln, wenn du sie nie rotierst. In einem interaktiven Terminal würdest du eher eine Aufgabe abschließen und beim nächsten Mal neu anfangen, wodurch der Kontext kleiner bleibt.
- **Leerlaufphasen zwischen Telegram-Nachrichten lassen den Prompt-Cache ablaufen.** Claudes Prompt-Cache hat eine kurze TTL. Antwortest du innerhalb dieses Fensters, sind Folge-Turns günstige Cache-Reads. Gibt es eine lange Pause (z. B. du schläfst und antwortest erst am nächsten Morgen), muss der *gesamte* angesammelte Kontext bei deiner nächsten Nachricht als deutlich teurerer Cache-Write komplett neu verarbeitet werden — und diese Kosten wachsen mit der bisherigen Größe der Sitzung. Deshalb kann der Verbrauch genau dann in die Höhe schnellen, wenn du deine erste Nachricht des Tages schickst, sogar vor den „Hauptzeiten“.

**Abhilfe:** Führe bei langlebigen Sitzungen regelmäßig `/compact` aus (dieser Telegram-Befehl wird von der App unterstützt), statt eine Sitzung unbegrenzt weiterlaufen zu lassen — besonders, wenn sie länger im Leerlauf war. Auch eine neue `/new`-Sitzung für nicht zusammenhängende Arbeit hilft, Kontext — und Kosten — begrenzt zu halten.

Die App tut das inzwischen auch automatisch, indem sie pro Anbieter zwei Signale kombiniert, damit sie dich nur dann unterbricht, wenn es wirklich wichtig ist: eine Leerlaufzeit-Schwelle (`CLAUDE_LONG_GAP_SECONDS` / `CODEX_LONG_GAP_SECONDS` / `COPILOT_LONG_GAP_SECONDS`) *und* wie viel Kontext die Sitzung bereits angesammelt hat (die Warnung wird für kleine/günstige Sitzungen übersprungen, selbst wenn sie eine Weile im Leerlauf waren, da ein erneutes Verarbeiten dann vernachlässigbar wäre). Standardwerte: 1 Stunde sowohl für Claude Code als auch für Codex — Claudes Wert ist durch echte Daten belegt (siehe oben), und obwohl OpenAI für Codex keinen dokumentiert, ist Codex' eigener Prompt-Cache ohnehin meist kurzlebiger als der von Claude, sodass ein Angleichen an Claudes Schwelle keine Genauigkeit kostet und einfach zu weniger Unterbrechungen führt, besonders jetzt kombiniert mit dem Größen-Gate; für Copilot ist es standardmäßig deaktiviert, weil [GitHubs eigene Dokumentation](https://docs.github.com/en/copilot/concepts/agents/copilot-cli/context-management) besagt, dass die Copilot-CLI überhaupt kein Inaktivitäts-Timeout hat und ihren Kontext bereits nativ selbst komprimiert (bei etwa 80–95 % Auslastung) — dort gibt es nichts Leerlaufbezogenes zu warnen, daher verlässt sich diese App auf Copilots eigenen Mechanismus, statt einen zu erfinden. Setze `COPILOT_LONG_GAP_SECONDS` auf einen positiven Wert, wenn du trotzdem einen leerlaufbasierten Hinweis für Copilot möchtest.

Sind sowohl die Schwelle als auch das Größen-Gate erreicht, hält sie deine Nachricht zurück und fragt:

> ⏳ Diese Sitzung war {gap} im Leerlauf. Sie jetzt fortzusetzen, verarbeitet die gesamte Unterhaltung wahrscheinlich komplett neu (der Antwort-Cache des Anbieters ist vermutlich abgelaufen), was deutlich mehr Tokens als üblich verbrauchen kann. Auch das Komprimieren verarbeitet den aktuellen Kontext einmal neu, um die Zusammenfassung zu erstellen, und kann daher ebenfalls viele Tokens kosten, wenn diese Sitzung bereits groß ist. Zu einer neuen Sitzung zu wechseln, umgeht diese Neuverarbeitung vollständig, startet dann aber ohne jede Erinnerung an diese Unterhaltung. Zu einer neuen Sitzung wechseln, erst komprimieren oder trotzdem fortsetzen?
>
> [🆕 Zu neuer Sitzung wechseln]
> [🔄 Erst komprimieren]
> [⚠️ Trotzdem fortsetzen]

Zu beachten ist, dass `/compact` selbst nicht kostenlos ist: Es funktioniert, indem die aktuelle (möglicherweise kalte) Sitzung fortgesetzt wird und diese gebeten wird, sich selbst zusammenzufassen — es fällt also derselbe einmalige Neuverarbeitungsaufwand für das gesamte Transkript an wie beim einfachen Antworten. Der Unterschied ist nur, dass du ihn danach nur einmal statt bei jeder weiteren Runde zahlst, da die entstehende Sitzung klein beginnt. **Zu neuer Sitzung wechseln** ist die einzige Option, die diese Neuverarbeitung vollständig vermeidet: Sie verlässt den Kontext der alten Sitzung, ohne sie je fortzusetzen, und startet komplett neu — auf Kosten davon, diesen Kontext vollständig zu verlieren, statt ihn in eine Zusammenfassung zu verdichten.

Wählst du **Zu neuer Sitzung wechseln**, wird eine brandneue, leere Sitzung gestartet und deine Nachricht dort fortgesetzt — benannt nach der alten Sitzung mit einem fortlaufenden `-newN`-Suffix (z. B. `fix-bug` → `fix-bug-new1` → `fix-bug-new2` beim nächsten Wechsel), damit du sie in `/switch` weiterhin von der ursprünglichen unterscheiden kannst. Wählst du **Erst komprimieren**, wird die Sitzung zusammengefasst, eine neue Sitzung aus dieser Zusammenfassung gestartet und deine Nachricht anschließend auf der neuen Sitzung fortgesetzt — ähnlich benannt, aber mit einem `-resumeN`-Suffix (z. B. `fix-bug` → `fix-bug-resume1` → `fix-bug-resume2` bei der nächsten Komprimierung). Wählst du **Trotzdem fortsetzen**, wird ganz normal auf der bestehenden Sitzung weitergemacht. Die gesamte Prüfung lässt sich mit `LONG_GAP_WARNING_ENABLED=false` deaktivieren.
</details>

## 📌 Hinweise

- Dieses Projekt ist für Nutzer gedacht, die die Agenten lokal auf ihrem eigenen Rechner ausführen.
- Der Telegram-Bot ist eine Steueroberfläche, nicht die Ausführungsumgebung selbst.
- Wenn du mehrere Bots betreibst, können sie alle von einem einzigen Serverprozess verwaltet werden.
