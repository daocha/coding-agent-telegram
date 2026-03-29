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
  <p><strong>Lichtgewicht, multi-bot, multi-sessie, multitasking, 24/7 AI Coding Agent</strong></p>
  <p>Bedien je lokale AI Coding Agent vanaf elke plek via Telegram.</p>
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

   ## ✨ Waarom dit project
  - ✅ Lichtgewicht: geen zware frameworks, volledig transparant
  - ✅ Multi-bot: meerdere chats, meerdere sessies
  - ✅ Gebruik Telegram om Codex / Copilot CLI te bedienen
  - ✅ Antwoorden en gewijzigde bestanden eenvoudig beoordelen in codeblokken
  - ✅ Vervolgvragen kunnen in de wachtrij terwijl de agent werkt
  - ✅ Ondersteunt tekst- en afbeeldingsinvoer

   ## 🔁 Naadloos wisselen tussen apparaten en sessies

  Start een sessie in Telegram en ga later verder met dezelfde Codex/Copilot CLI-sessie op je computer, zonder gedoe. Met `/switch` kun je ook eenvoudig van Telegram terug naar de command line schakelen.
  
  - Gebruik `/switch` om een lokale sessie voort te zetten
  - Historische sessies worden ook ondersteund

   ## 🛠️ Typische lokale flow
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

→ Installeren met één regel: 
```
curl -fsSL https://raw.githubusercontent.com/daocha/coding-agent-telegram/main/install.sh | bash
```

<table>
   <tr>
   <td width="50%" valign="top">

   ## 🔐 Beveiliging

- Allowlist voor privéchats via `ALLOWED_CHAT_IDS`
- Slechts één actieve agent per project om conflicterende writes te beperken
- Diffs van gevoelige bestanden worden verborgen
- API-sleutels, tokens, `.env`-waarden, certificaten, SSH-sleutels en vergelijkbare geheime uitvoer worden gemaskeerd voordat ze naar Telegram worden gestuurd
- Runtime-appdata blijft onder `~/.coding-agent-telegram`
- Bestaande mappen kunnen een trust-bevestiging vereisen vóór muterende Git-bewerkingen
- Geen verborgen externe calls. Jij houdt de controle
   </td>
   <td width="50%" valign="top">

   ## ✅ Vereisten

Voordat je de server start, zorg dat je hebt:

- Python 3.9 of nieuwer
- Een Telegram bot token van _@BotFather_
- Je Telegram chat ID
- Codex CLI en/of Copilot CLI lokaal geïnstalleerd
- [Codex CLI installatie](https://developers.openai.com/codex/cli)
- [Copilot CLI installatie](https://github.com/features/copilot/cli)
   </td>
   </tr>
</table>

## 🚀 Snel starten

### Option A: Bootstrapscript in één regel
```bash
curl -fsSL https://raw.githubusercontent.com/daocha/coding-agent-telegram/main/install.sh | bash
```

### Option B: Installeren vanaf PyPI met `pip`
```bash
pip install coding-agent-telegram
coding-agent-telegram
```

### Option C: Uitvoeren vanuit een gekloonde repository
```bash
git clone https://github.com/daocha/coding-agent-telegram
cd coding-agent-telegram
./startup.sh
```

### Botserver starten
##### Bij de eerste start maakt de app het env-bestand aan en vertelt welke velden je moet invullen.
##### Start na het bijwerken van het env-bestand opnieuw:
```bash
# if you follow Option A or Option B, then run
coding-agent-telegram

# if you follow Option C, then run this again
./startup.sh
```

## 🔑 Telegram-instelling

### Een Bot Token krijgen

1. Open Telegram en start een chat met `@BotFather`.
2. Stuur `/newbot`.
3. Volg de stappen om te kiezen:
   - een weergavenaam
   - een bot-gebruikersnaam die eindigt op `bot`
4. BotFather geeft een HTTP API token terug.
5. Zet dat token in `TELEGRAM_BOT_TOKENS` in `~/.coding-agent-telegram/.env_coding_agent_telegram`. 

### Je Chat ID krijgen

De betrouwbaarste manier is de Telegram `getUpdates` API gebruiken met je eigen bot token.

1. Start een chat met je bot en stuur bijvoorbeeld `/start`.
2. Open deze URL in je browser en vervang `<BOT_TOKEN>`:

```text
https://api.telegram.org/bot<BOT_TOKEN>/getUpdates
```

3. Zoek het object `chat` in de JSON-respons.
4. Kopieer de numerieke waarde van het veld `id`.
5. Zet die waarde in `ALLOWED_CHAT_IDS` in `~/.coding-agent-telegram/.env_coding_agent_telegram`.

Opmerkingen:

- Voor privéchats is de chat ID meestal een positief geheel getal.
- Als `getUpdates` een lege respons geeft, stuur de bot nog een bericht en probeer opnieuw.

## 📨 Ondersteunde berichttypen

## 🤖 Telegram-commando’s

<table>
  <tr>
    <td width="250"><code>/provider</code></td>
    <td>Kies de provider voor nieuwe sessies. De keuze wordt per bot en chat bewaard totdat je die wijzigt.</td>
  </tr>
  <tr>
    <td width="250"><code>/project &lt;project_folder&gt;</code></td>
    <td>Stel de huidige projectmap in. Bestaat de map niet, dan maakt de app die aan en markeert hem trusted. Bestaat hij al maar is hij nog untrusted, dan vraagt de app expliciet om trust.</td>
  </tr>
  <tr>
    <td width="250"><code>/branch &lt;new_branch&gt;</code></td>
    <td>Bereid een branch voor of wissel ernaar voor het huidige project. Als de branch al bestaat, behandelt de bot die als source candidate. Anders gebruikt hij de standaard-branch van de repository als source candidate.</td>
  </tr>
  <tr>
    <td width="250"><code>/branch &lt;origin_branch&gt; &lt;new_branch&gt;</code></td>
    <td>Bereid een branch voor of wissel ernaar met `<origin_branch>` als source candidate. Voor beide vormen biedt de bot daarna alleen de source choices aan die echt bestaan: `local/<branch>` en `origin/<branch>`. Als er maar één bestaat, zie je alleen die. Als geen van beide bestaat, meldt de bot dat de branch-source ontbreekt.</td>
  </tr>
  <tr>
    <td width="250"><code>/current</code></td>
    <td>Toon de actieve sessie voor de huidige bot en chat.</td>
  </tr>
  <tr>
    <td width="250"><code>/new [session_name]</code></td>
    <td>Maak een nieuwe sessie voor het huidige project. Als je geen naam opgeeft, gebruikt de bot de echte session ID. Als provider, project of branch ontbreekt, begeleidt de bot je door de ontbrekende stap.</td>
  </tr>
  <tr>
    <td width="250"><code>/switch</code></td>
    <td>Toon de nieuwste sessies, nieuwste eerst. De lijst bevat zowel bot-managed sessies als lokale Codex/Copilot CLI-sessies voor het huidige project.</td>
  </tr>
  <tr>
    <td width="250"><code>/switch page &lt;number&gt;</code></td>
    <td>Toon een andere pagina met opgeslagen sessies.</td>
  </tr>
  <tr>
    <td width="250"><code>/switch &lt;session_id&gt;</code></td>
    <td>Schakel naar een specifieke sessie via ID. Kies je een lokale CLI-sessie, dan importeert de bot die en gaat daar verder.</td>
  </tr>
  <tr>
    <td width="250"><code>/compact</code></td>
    <td>Maak vanuit de actieve session een nieuwe compacte session en schakel daarheen over.</td>
  </tr>
  <tr>
    <td width="250"><code>/commit &lt;git commands&gt;</code></td>
    <td>Voer gevalideerde `git commit`-gerelateerde commando’s uit binnen het project van de actieve sessie. Alleen beschikbaar als `ENABLE_COMMIT_COMMAND=true`. Muterende Git-commando’s vereisen een trusted project.</td>
  </tr>
  <tr>
    <td width="250"><code>/push</code></td>
    <td>Push `origin <branch>` voor de huidige actieve sessie. De bot vraagt om bevestiging voordat hij pusht.</td>
  </tr>
  <tr>
    <td width="250"><code>/abort</code></td>
    <td>Breek de huidige agent-run voor het huidige project af. Als er vragen in de wachtrij staan, vraagt de bot of die verder verwerkt moeten worden.</td>
  </tr>
</table>

<h2>⚙️ Omgevingsvariabelen</h2>

<h3>Pad van het hoofd-env-bestand:</h3>

<table>
  <tr>
    <td><code>CODING_AGENT_TELEGRAM_ENV_FILE</code></td>
    <td>Gebruik dit als de app naar een specifiek env-bestand moet wijzen.</td>
  </tr>
  <tr>
    <td><code>~/.coding-agent-telegram/.env_coding_agent_telegram</code></td>
    <td>Standaardlocatie van het env-bestand.</td>
  </tr>
  <tr>
    <td><code>./.env_coding_agent_telegram</code></td>
    <td>Alleen gebruikt als dit lokale bestand al bestaat.</td>
  </tr>
</table>

<h3>Verplicht</h3>

<table>
  <tr>
    <td width="250"><code>WORKSPACE_ROOT</code></td>
    <td>Bovenliggende map die je projectmappen bevat.</td>
  </tr>
  <tr>
    <td width="250"><code>TELEGRAM_BOT_TOKENS</code></td>
    <td>Door komma's gescheiden Telegram bot tokens.</td>
  </tr>
  <tr>
    <td width="250"><code>ALLOWED_CHAT_IDS</code></td>
    <td>Door komma's gescheiden Telegram chat-ID's van privéchats die de bot mogen gebruiken.</td>
  </tr>
</table>

<h3>Veelgebruikte instellingen</h3>

<table>
  <tr>
    <td width="250"><code>APP_LOCALE</code></td>
    <td>UI-locale voor gedeelde botmeldingen en commandobeschrijvingen. Ondersteunde waarden: <code>en</code>, <code>de</code>, <code>fr</code>, <code>ja</code>, <code>ko</code>, <code>nl</code>, <code>th</code>, <code>vi</code>, <code>zh-CN</code>, <code>zh-HK</code>, <code>zh-TW</code>.</td>
  </tr>
  <tr>
    <td width="250"><code>CODEX_BIN</code></td>
    <td>Commando om Codex CLI te starten. Standaard: <code>codex</code>.</td>
  </tr>
  <tr>
    <td width="250"><code>COPILOT_BIN</code></td>
    <td>Commando om Copilot CLI te starten. Standaard: <code>copilot</code>.</td>
  </tr>
  <tr>
    <td width="250"><code>CODEX_MODEL</code></td>
    <td>Optionele Codex-modeloverride. Laat leeg om het standaardmodel van Codex CLI te gebruiken. Voorbeeld: <code>gpt-5.4</code> <a href="https://developers.openai.com/codex/models" target="_blank">OpenAI Codex/OpenAI-modellen</a></td>
  </tr>
  <tr>
    <td width="250"><code>COPILOT_MODEL</code></td>
    <td>Optionele Copilot-modeloverride. Laat leeg om het standaardmodel van Copilot CLI te gebruiken. Voorbeelden: <code>gpt-5.4</code>, <code>claude-sonnet-4.6</code> <a href="https://docs.github.com/en/copilot/reference/ai-models/supported-models" target="_blank">Ondersteunde GitHub Copilot-modellen</a></td>
  </tr>
  <tr>
    <td width="250"><code>CODEX_APPROVAL_POLICY</code></td>
    <td>Goedkeuringsmodus die aan Codex wordt doorgegeven. Standaard: <code>never</code>.</td>
  </tr>
  <tr>
    <td width="250"><code>CODEX_SANDBOX_MODE</code></td>
    <td>Sandboxmodus die aan Codex wordt doorgegeven. Standaard: <code>workspace-write</code>.</td>
  </tr>
  <tr>
    <td width="250"><code>CODEX_SKIP_GIT_REPO_CHECK</code></td>
    <td>Als dit is ingeschakeld, worden trusted-repo-checks van Codex altijd overgeslagen.</td>
  </tr>
  <tr>
    <td width="250"><code>ENABLE_COMMIT_COMMAND</code></td>
    <td>Schakelt het Telegram-commando <code>/commit</code> in. Standaard: <code>false</code>.</td>
  </tr>
  <tr>
    <td width="250"><code>AGENT_HARD_TIMEOUT_SECONDS</code></td>
    <td>Harde timeout voor één agent-run. Standaard: <code>0</code> (uitgeschakeld).</td>
  </tr>
  <tr>
    <td width="250"><code>SNAPSHOT_TEXT_FILE_MAX_BYTES</code></td>
    <td>Maximale bestandsgrootte die de bot als tekst leest voor de before/after-snapshot voor per-run diffs. Standaard: <code>200000</code>.</td>
  </tr>
  <tr>
    <td width="250"><code>MAX_TELEGRAM_MESSAGE_LENGTH</code></td>
    <td>Maximale berichtgrootte voordat de app antwoorden splitst. Standaard: <code>3000</code>.</td>
  </tr>
  <tr>
    <td width="250"><code>ENABLE_SENSITIVE_DIFF_FILTER</code></td>
    <td>Verberg diffs voor gevoelige bestanden. Standaard: <code>true</code>.</td>
  </tr>
  <tr>
    <td width="250"><code>ENABLE_SECRET_SCRUB_FILTER</code></td>
    <td>Maskeer tokens, sleutels, <code>.env</code>-waarden, certificaten en vergelijkbare geheime uitvoer voordat die naar Telegram wordt gestuurd. Standaard: <code>true</code> (sterk aanbevolen).</td>
  </tr>
  <tr>
    <td width="250"><code>SNAPSHOT_INCLUDE_PATH_GLOBS</code></td>
    <td>Forceer dat overeenkomende paden in diffs worden opgenomen. Voorbeeld: <code>.github/*,.profile.test,.profile.prod</code></td>
  </tr>
  <tr>
    <td width="250"><code>SNAPSHOT_EXCLUDE_PATH_GLOBS</code></td>
    <td>Voeg extra diff-exclusies toe boven op de pakketstandaard. Voorbeeld: <code>.*,personal/*,sensitive*.txt</code> Opmerking: <code>.*</code> matcht verborgen paden, inclusief bestanden in verborgen mappen.</td>
  </tr>
</table>

<h3>Status en logs</h3>

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

Voorbeeld:

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

## 🧠 Sessiebeheer

Sessies zijn gescoped per:

- Telegram-bot
- Telegram-chat

Daardoor kan hetzelfde Telegram-account meerdere bots gebruiken zonder sessies te vermengen.

Voorbeeld:

- Bot A + jouw chat -> backendwerk
- Bot B + jouw chat -> frontendwerk
- Bot C + jouw chat -> infrawerk

De actieve sessie is ook gekoppeld aan:

- projectmap
- provider
- branch-naam wanneer beschikbaar

<details>
<summary><b>Per sessie wordt opgeslagen:</b></summary>

- sessienaam
- projectmap
- branch-naam
- provider
- tijdstempels
- actieve sessiekeuze voor die bot/chat-scope
</details>

### 🔓 Workspace concurrency lock

Er kan maar één agent-run tegelijk actief zijn per **projectmap**, ongeacht welke chat of welke Telegram-bot die heeft gestart.

- **project is busy**: er draait al een agent-run in die workspace
- **agent is busy**: die ene run verwerkt de huidige aanvraag nog

De bot dwingt dit af zodat twee agents niet tegelijk naar dezelfde workspace schrijven. Dat verkleint de kans op conflicterende wijzigingen en datacorruptie.

Komt er een bericht binnen terwijl er al een agent draait op hetzelfde project, dan antwoordt de bot direct:

> ⏳ Er draait al een agent op dit project. Wacht tot die klaar is.

De lock wordt in het geheugen gehouden, niet op schijf. Daardoor wordt hij automatisch vrijgegeven wanneer de agent klaar is, faalt of de server herstart.

### 💬 Vragen in de wachtrij

Als er al een agent-run actief is op het huidige project, worden latere tekstberichten niet geweigerd maar in een wachtrij geplaatst.

- de nieuwe vraag wordt toegevoegd aan een queued-questions-bestand op schijf
- de huidige agent blijft werken aan de eerdere aanvraag
- wanneer die run normaal eindigt, start de bot automatisch met de verwerking van de vragen in de wachtrij

Wordt de huidige run afgebroken terwijl er nog vragen wachten, dan gaat de bot niet automatisch verder. Hij vraagt dan of de resterende vragen verder moeten worden verwerkt, gegroepeerd of één voor één.

## ⚠️ Diff (bestandswijzigingen)

_Tijdens elke agent-run maakt de bot ook een lichte before/after-snapshot van het project, zodat gewijzigde bestanden kunnen worden samengevat en diffs naar Telegram kunnen worden gestuurd. Deze snapshot wordt door de bot-app zelf gemaakt, niet door Codex of Copilot._

**Snapshot-opmerkingen:**

- de app loopt de projectmap door vóór en na de run
- voor normale tekstbestanden heeft de per-run snapshot-diff voorrang op een git-head-diff
- gebruikelijke dependency-, cache- en runtime-mappen worden ook overgeslagen
- binaire bestanden en bestanden groter dan `SNAPSHOT_TEXT_FILE_MAX_BYTES` worden niet als tekst geladen
- bij erg grote projecten kan deze extra scan merkbare I/O- en geheugenbelasting toevoegen
- als de snapshot een bestand niet als tekst kan weergeven, valt de app waar mogelijk terug op `git diff`
- voor grote of niet-tekstbestanden kan de diff alsnog worden weggelaten en vervangen door een kort bericht

De snapshot-uitsluitingsregels staan in package resources:

- `src/coding_agent_telegram/resources/snapshot_excluded_dir_names.txt`
- `src/coding_agent_telegram/resources/snapshot_excluded_dir_globs.txt`
- `src/coding_agent_telegram/resources/snapshot_excluded_file_globs.txt`

Je kunt deze standaardwaarden in het env-bestand overschrijven zonder het geïnstalleerde package te wijzigen:

- `SNAPSHOT_INCLUDE_PATH_GLOBS`
  Forceer opname van overeenkomende paden in diffs.
  Voorbeeld: `.github/*,.profile.test,.profile.prod`

- `SNAPSHOT_EXCLUDE_PATH_GLOBS`
  Voeg extra diff-uitsluitingen toe boven op de package-standaarden.
  Voorbeeld: `.*,personal/*,sensitive*.txt`
  Opmerking: `.*` matcht verborgen paden, inclusief bestanden in verborgen mappen.

Als include en exclude allebei matchen, wint include.

## 🌿 Branch-gedrag

De bot behandelt project en branch als één geheel.

- het kiezen van een project kiest niet stilzwijgend een ongerelateerde branch
- als branch-invoer nodig is, vraagt de bot je die te kiezen
- wanneer branch-informatie in sessieberichten wordt getoond, worden project en branch samen weergegeven

Wanneer je een branch maakt of wisselt, begeleidt de bot je expliciet bij de bron:

- `local/<branch>` betekent de lokale branch als bron gebruiken
- `origin/<branch>` betekent eerst vanaf de remote branch verversen en daarna wisselen

Als de bot ziet dat de in de sessie opgeslagen branch niet overeenkomt met de huidige repository-branch, gaat hij niet blind verder. Hij vraagt welke branch gebruikt moet worden:

- de opgeslagen sessie-branch behouden
- de huidige repository-branch behouden

Als je voorkeursbron-branch ontbreekt, biedt de bot fallback-bronnen aan op basis van de standaard-branch en de huidige branch in plaats van je achter te laten met een kale Git-fout.

## 🔐 Git-trustgedrag

- bestaande mappen volgen `CODEX_SKIP_GIT_REPO_CHECK`
- mappen die via `/project <name>` worden aangemaakt, worden door deze app als trusted gemarkeerd
- bestaande mappen die via `/project <name>` worden gekozen, blijven untrusted tot je trust bevestigt in Telegram
- nieuw aangemaakte projectmappen kunnen dus direct worden gebruikt
- `/commit` kan volledig worden uitgeschakeld met `ENABLE_COMMIT_COMMAND`
- muterende `/commit`-bewerkingen zijn alleen toegestaan voor trusted projecten

## 🪵 Logs

Logs worden **zowel naar stdout als naar een roterend logbestand** geschreven onder:

- `~/.coding-agent-telegram/logs` (rotatie bij 10 MB, 3 back-ups)

> **Opmerking:** als je tegelijk naar de terminal kijkt en het logbestand tailt, verschijnt elk bericht twee keer. Dat is verwacht gedrag. Bekijk het één of het ander, niet beide tegelijk.

<details>
<summary><b>Typisch gelogde gebeurtenissen</b></summary>

- bot-start en polling-start
- projectselectie
- sessiecreatie
- sessiewissel
- rapportage van de actieve sessie
- normale run-uitvoering (inclusief een auditlogregel met een ingekorte prompt)
- sessievervanging na mislukte resume
- waarschuwingen en runtime-fouten
</details>

## 🗂️ Projectstructuur

- `src/coding_agent_telegram/`
  hoofdcode van de applicatie

- `tests/`
  testsuite

- `startup.sh`
  lokaal bootstrap- en start-entrypoint

- `src/coding_agent_telegram/resources/.env.example`
  canonieke omgevingssjabloon gebruikt door zowel repo-start als package-installaties

- `pyproject.toml`
  packaging- en dependencyconfiguratie

## 📦 Release-versiebeheer

Packageversies worden afgeleid van Git-tags.

- TestPyPI/testen: `v2026.3.26.dev1`
- PyPI-prerelease: `v2026.3.26rc1`
- PyPI-stable: `v2026.3.26`

## 📌 Opmerkingen

- Dit project is bedoeld voor gebruikers die agents lokaal op hun eigen machine uitvoeren.
- De Telegram-bot is een bedieningslaag, niet de uitvoeringsomgeving zelf.
- Als je meerdere bots draait, kunnen die allemaal door één serverproces worden beheerd.
