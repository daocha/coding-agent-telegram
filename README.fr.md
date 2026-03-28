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
  <p><strong>Léger, multi-bots, multi-sessions, multitâche, agent de code IA 24/7</strong></p>
  <p>Contrôlez votre agent de code IA local depuis n’importe où avec Telegram.</p>
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

   ## ✨ Pourquoi l’utiliser
  - ✅ Léger : pas de framework lourd, transparence totale
  - ✅ Multi-bot : plusieurs chats, plusieurs sessions
  - ✅ Utiliser Telegram pour piloter Codex / Copilot CLI
  - ✅ Révision facile des réponses et des fichiers modifiés dans des blocs de code
  - ✅ Les messages de suivi peuvent être mis en file d’attente pendant qu’un agent travaille
  - ✅ Prend en charge le texte et les images

   ## 🔁 Changement fluide entre appareils et sessions

  Démarrez une session dans Telegram, puis reprenez la même session Codex/Copilot CLI plus tard sur votre ordinateur sans friction. Avec `/switch`, vous pouvez aussi repasser simplement de Telegram à la ligne de commande.
  
  - Utilisez `/switch` pour reprendre une session locale
  - Les sessions historiques sont également prises en charge

   ## 🛠️ Flux local typique
   ```bash
   coding-agent-telegram # or run ./startup.sh
   ```

   ##### Dans Telegram :

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

→ Installation en une ligne : 
```
curl -fsSL https://raw.githubusercontent.com/daocha/coding-agent-telegram/main/install.sh | bash
```

<table>
   <tr>
   <td width="50%" valign="top">

   ## 🔐 Sécurité

- Liste blanche des chats privés via `ALLOWED_CHAT_IDS`
- Un seul agent actif par projet pour réduire les écritures concurrentes
- Les diffs de fichiers sensibles sont masqués
- Les clés API, tokens, valeurs `.env`, certificats, clés SSH et autres contenus sensibles similaires sont masqués avant l’envoi vers Telegram
- Les données d’exécution restent sous `~/.coding-agent-telegram`
- Les dossiers existants peuvent exiger une confirmation de confiance avant les opérations Git modifiantes
- Aucun appel externe caché : vous gardez le contrôle
   </td>
   <td width="50%" valign="top">

   ## ✅ Prérequis

Avant de démarrer le serveur, assurez-vous d’avoir :

- Python 3.9 ou plus récent
- Un token de bot Telegram créé via _@BotFather_
- Votre identifiant de chat Telegram
- Codex CLI et/ou Copilot CLI installés localement
- [Installation Codex CLI](https://developers.openai.com/codex/cli)
- [Installation Copilot CLI](https://github.com/features/copilot/cli)
   </td>
   </tr>
</table>

## 🚀 Démarrage rapide

### Option A : Script bootstrap en une ligne
```bash
curl -fsSL https://raw.githubusercontent.com/daocha/coding-agent-telegram/main/install.sh | bash
```

### Option B : Installation depuis PyPI avec `pip`
```bash
pip install coding-agent-telegram
coding-agent-telegram
```

### Option C : Exécution depuis un dépôt cloné
```bash
git clone https://github.com/daocha/coding-agent-telegram
cd coding-agent-telegram
./startup.sh
```

### Démarrer le serveur du bot
##### Au premier lancement, l’application crée le fichier env et vous indique quels champs remplir.
##### Après avoir mis à jour le fichier env, relancez :
```bash
# if you follow Option A or Option B, then run
coding-agent-telegram

# if you follow Option C, then run this again
./startup.sh
```

## 🔑 Configuration Telegram

### Obtenir un Bot Token

1. Ouvrez Telegram et démarrez une conversation avec `@BotFather`.
2. Envoyez `/newbot`.
3. Suivez les étapes pour choisir :
   - un nom d'affichage
   - un nom d'utilisateur de bot se terminant par `bot`
4. BotFather vous renverra un token HTTP API.
5. Ajoutez ce token dans `TELEGRAM_BOT_TOKENS` dans `~/.coding-agent-telegram/.env_coding_agent_telegram`.

### Obtenir votre Chat ID

La méthode la plus fiable consiste à utiliser l'API Telegram `getUpdates` avec votre propre bot token.

1. Démarrez une conversation avec votre bot et envoyez un message comme `/start`.
2. Ouvrez cette URL dans votre navigateur en remplaçant `<BOT_TOKEN>` :

```text
https://api.telegram.org/bot<BOT_TOKEN>/getUpdates
```

3. Recherchez l'objet `chat` dans la réponse JSON.
4. Copiez la valeur numérique du champ `id`.
5. Ajoutez cette valeur dans `ALLOWED_CHAT_IDS` dans `~/.coding-agent-telegram/.env_coding_agent_telegram`.

Remarques :

- Dans une conversation privée, le chat ID est généralement un entier positif.
- Si `getUpdates` renvoie une réponse vide, envoyez un autre message au bot puis réessayez.

## 📨 Types de messages pris en charge

## 🤖 Commandes Telegram

<table>
  <tr>
    <td width="250"><code>/provider</code></td>
    <td>Choisir le provider pour les nouvelles sessions. Le choix est stocké par bot et par chat jusqu’à modification.</td>
  </tr>
  <tr>
    <td width="250"><code>/project &lt;project_folder&gt;</code></td>
    <td>Définir le dossier de projet courant. Si le dossier n’existe pas, l’app le crée et le marque trusted. S’il existe déjà mais reste untrusted, l’app vous demande une confirmation.</td>
  </tr>
  <tr>
    <td width="250"><code>/branch &lt;new_branch&gt;</code></td>
    <td>Préparer ou changer une branch pour le projet courant. Si la branch existe déjà, le bot la traite comme source candidate. Sinon il utilise la branch par défaut du dépôt.</td>
  </tr>
  <tr>
    <td width="250"><code>/branch &lt;origin_branch&gt; &lt;new_branch&gt;</code></td>
    <td>Préparer ou changer une branch en utilisant `<origin_branch>` comme source candidate. Pour les deux formes, le bot ne propose ensuite que les sources réellement disponibles : `local/<branch>` et `origin/<branch>`. Si une seule existe, seule celle-ci est affichée. Si aucune n’existe, le bot signale que la source de branch est introuvable.</td>
  </tr>
  <tr>
    <td width="250"><code>/current</code></td>
    <td>Afficher la session active pour le bot et le chat courants.</td>
  </tr>
  <tr>
    <td width="250"><code>/new [session_name]</code></td>
    <td>Créer une nouvelle session pour le projet courant. Si vous omettez le nom, le bot utilise la vraie session ID. Si provider, projet ou branch manque, le bot vous guide.</td>
  </tr>
  <tr>
    <td width="250"><code>/switch</code></td>
    <td>Afficher les sessions les plus récentes, de la plus récente à la plus ancienne. La liste inclut les sessions gérées par le bot et les sessions locales Codex/Copilot CLI du projet courant.</td>
  </tr>
  <tr>
    <td width="250"><code>/switch page &lt;number&gt;</code></td>
    <td>Afficher une autre page des sessions enregistrées.</td>
  </tr>
  <tr>
    <td width="250"><code>/switch &lt;session_id&gt;</code></td>
    <td>Basculer vers une session précise via son ID. Si vous choisissez une session CLI locale, le bot l’importe et reprend à partir d’elle.</td>
  </tr>
  <tr>
    <td width="250"><code>/compact</code></td>
    <td>Compacter la session active et demander au provider de condenser l'état actuel de la conversation.</td>
  </tr>
  <tr>
    <td width="250"><code>/commit &lt;git commands&gt;</code></td>
    <td>Exécuter des commandes liées à `git commit` validées dans le projet de la session active. Disponible uniquement si `ENABLE_COMMIT_COMMAND=true`. Les commandes Git mutantes exigent un projet trusted.</td>
  </tr>
  <tr>
    <td width="250"><code>/push</code></td>
    <td>Pousser `origin <branch>` pour la session active courante. Le bot demande une confirmation avant le push.</td>
  </tr>
  <tr>
    <td width="250"><code>/abort</code></td>
    <td>Annuler l’exécution d’agent en cours pour le projet courant. Si des questions attendent dans la file, le bot demande si elles doivent continuer.</td>
  </tr>
</table>

<h2>⚙️ Variables d’environnement</h2>

<h3>Chemin principal du fichier env :</h3>

<table>
  <tr>
    <td><code>CODING_AGENT_TELEGRAM_ENV_FILE</code></td>
    <td>Utilisez ceci si vous voulez pointer l’application vers un fichier env précis.</td>
  </tr>
  <tr>
    <td><code>~/.coding-agent-telegram/.env_coding_agent_telegram</code></td>
    <td>Chemin par défaut du fichier env.</td>
  </tr>
  <tr>
    <td><code>./.env_coding_agent_telegram</code></td>
    <td>Utilisé seulement si ce fichier local existe déjà.</td>
  </tr>
</table>

<h3>Obligatoire</h3>

<table>
  <tr>
    <td width="250"><code>WORKSPACE_ROOT</code></td>
    <td>Dossier parent qui contient vos répertoires de projet.</td>
  </tr>
  <tr>
    <td width="250"><code>TELEGRAM_BOT_TOKENS</code></td>
    <td>Liste de tokens de bot Telegram séparés par des virgules.</td>
  </tr>
  <tr>
    <td width="250"><code>ALLOWED_CHAT_IDS</code></td>
    <td>Liste d’IDs de chat privés Telegram autorisés, séparés par des virgules.</td>
  </tr>
</table>

<h3>Réglages courants</h3>

<table>
  <tr>
    <td width="250"><code>APP_LOCALE</code></td>
    <td>Langue de l’interface pour les messages partagés du bot et les descriptions de commandes. Valeurs prises en charge : <code>en</code>, <code>de</code>, <code>fr</code>, <code>ja</code>, <code>ko</code>, <code>nl</code>, <code>th</code>, <code>vi</code>, <code>zh-CN</code>, <code>zh-HK</code>, <code>zh-TW</code>.</td>
  </tr>
  <tr>
    <td width="250"><code>CODEX_BIN</code></td>
    <td>Commande utilisée pour lancer Codex CLI. Valeur par défaut : <code>codex</code>.</td>
  </tr>
  <tr>
    <td width="250"><code>COPILOT_BIN</code></td>
    <td>Commande utilisée pour lancer Copilot CLI. Valeur par défaut : <code>copilot</code>.</td>
  </tr>
  <tr>
    <td width="250"><code>CODEX_MODEL</code></td>
    <td>Remplacement optionnel du modèle Codex. Laissez vide pour utiliser le modèle par défaut de Codex CLI. Exemple : <code>gpt-5.4</code> <a href="https://developers.openai.com/codex/models" target="_blank">Modèles OpenAI Codex/OpenAI</a></td>
  </tr>
  <tr>
    <td width="250"><code>COPILOT_MODEL</code></td>
    <td>Remplacement optionnel du modèle Copilot. Laissez vide pour utiliser le modèle par défaut de Copilot CLI. Exemples : <code>gpt-5.4</code>, <code>claude-sonnet-4.6</code> <a href="https://docs.github.com/en/copilot/reference/ai-models/supported-models" target="_blank">Modèles pris en charge par GitHub Copilot</a></td>
  </tr>
  <tr>
    <td width="250"><code>CODEX_APPROVAL_POLICY</code></td>
    <td>Mode d’approbation transmis à Codex. Défaut : <code>never</code>.</td>
  </tr>
  <tr>
    <td width="250"><code>CODEX_SANDBOX_MODE</code></td>
    <td>Mode sandbox transmis à Codex. Défaut : <code>workspace-write</code>.</td>
  </tr>
  <tr>
    <td width="250"><code>CODEX_SKIP_GIT_REPO_CHECK</code></td>
    <td>Si activé, contourne toujours les vérifications de dépôt trusted de Codex.</td>
  </tr>
  <tr>
    <td width="250"><code>ENABLE_COMMIT_COMMAND</code></td>
    <td>Active la commande Telegram <code>/commit</code>. Défaut : <code>false</code>.</td>
  </tr>
  <tr>
    <td width="250"><code>AGENT_HARD_TIMEOUT_SECONDS</code></td>
    <td>Timeout dur pour une exécution d’agent. Défaut : <code>0</code> (désactivé).</td>
  </tr>
  <tr>
    <td width="250"><code>SNAPSHOT_TEXT_FILE_MAX_BYTES</code></td>
    <td>Taille maximale de fichier que le bot lira en texte pour construire le snapshot avant/après des diffs. Défaut : <code>200000</code>.</td>
  </tr>
  <tr>
    <td width="250"><code>MAX_TELEGRAM_MESSAGE_LENGTH</code></td>
    <td>Taille maximale d’un message avant découpage de la réponse. Défaut : <code>3000</code>.</td>
  </tr>
  <tr>
    <td width="250"><code>ENABLE_SENSITIVE_DIFF_FILTER</code></td>
    <td>Masquer les diffs des fichiers sensibles. Défaut : <code>true</code>.</td>
  </tr>
  <tr>
    <td width="250"><code>ENABLE_SECRET_SCRUB_FILTER</code></td>
    <td>Masquer tokens, clés, valeurs <code>.env</code>, certificats et sorties similaires avant envoi vers Telegram. Défaut : <code>true</code> (fortement recommandé).</td>
  </tr>
  <tr>
    <td width="250"><code>SNAPSHOT_INCLUDE_PATH_GLOBS</code></td>
    <td>Toujours inclure les chemins correspondants dans les diffs. Exemple : <code>.github/*,.profile.test,.profile.prod</code></td>
  </tr>
  <tr>
    <td width="250"><code>SNAPSHOT_EXCLUDE_PATH_GLOBS</code></td>
    <td>Ajouter des exclusions de diff supplémentaires au-dessus des valeurs par défaut du package. Exemple : <code>.*,personal/*,sensitive*.txt</code> Remarque : <code>.*</code> inclut les chemins cachés, y compris les fichiers dans les dossiers cachés.</td>
  </tr>
</table>

<h3>État et logs</h3>

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

Exemple :

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

## 🧠 Gestion des sessions

Les sessions sont isolées par :

- bot Telegram
- chat Telegram

Ainsi, un même compte Telegram peut utiliser plusieurs bots sans mélanger les sessions.

Exemple :

- Bot A + votre chat -> travail backend
- Bot B + votre chat -> travail frontend
- Bot C + votre chat -> travail infra

La session active est aussi liée à :

- project folder
- provider
- nom de branch quand disponible

<details>
<summary><b>Chaque session stocke :</b></summary>

- nom de session
- project folder
- nom de branch
- provider
- horodatages
- sélection de session active pour cette portée bot/chat
</details>

### 🔓 Verrou de concurrence du workspace

Une seule exécution d'agent peut être active à la fois par **project folder**, quel que soit le chat ou le bot Telegram qui l'a déclenchée.

- **project is busy** : un agent est déjà en cours dans ce workspace
- **agent is busy** : cette exécution unique traite encore la requête courante

Le bot impose cette limite pour éviter que deux agents écrivent en même temps dans le même workspace. Cela réduit les modifications conflictuelles et le risque de corruption.

Si un message arrive alors qu'un agent tourne déjà sur ce projet, le bot répond immédiatement :

> ⏳ Un agent est déjà en cours sur ce projet. Veuillez attendre qu'il se termine.

Le verrou est conservé uniquement en mémoire, pas sur disque. Il est libéré automatiquement quand l'agent se termine, échoue ou quand le serveur redémarre.

### 💬 Questions en file d'attente

Si le projet courant a déjà une exécution d'agent active, les messages texte suivants ne sont pas rejetés. Ils sont mis en file d'attente :

- la nouvelle question est ajoutée à un fichier de questions en attente sur disque
- l'agent en cours continue la requête précédente
- quand cette exécution se termine normalement, le bot commence automatiquement à traiter les questions en attente

Si l'exécution en cours est annulée et que des questions attendent encore, le bot ne continue pas automatiquement. Il demande alors si les questions restantes doivent être traitées, en lot ou une par une.

## ⚠️ Diff (modifications de fichiers)

_Pendant chaque exécution d'agent, le bot prend aussi un léger snapshot avant/après du projet afin de résumer les fichiers modifiés et d'envoyer des diffs vers Telegram. Ce snapshot est produit par le bot lui-même, pas par Codex ou Copilot._

**À savoir sur le snapshot :**

- l'app parcourt le dossier du projet avant et après l'exécution
- pour les fichiers texte normaux, l'app préfère le diff du snapshot du run plutôt qu'un diff contre le head Git
- les répertoires courants de dépendances, cache et runtime sont aussi ignorés
- les fichiers binaires et les fichiers plus gros que `SNAPSHOT_TEXT_FILE_MAX_BYTES` ne sont pas lus comme texte
- sur les très gros projets, ce scan supplémentaire peut ajouter un surcoût notable en I/O et en mémoire
- si un snapshot ne peut pas représenter un fichier comme texte, l'app retombe sur `git diff` lorsque c'est possible
- pour les gros fichiers ou les fichiers non textuels, le diff peut quand même être omis et remplacé par un court message

Les règles d'exclusion du snapshot se trouvent dans les ressources du package :

- `src/coding_agent_telegram/resources/snapshot_excluded_dir_names.txt`
- `src/coding_agent_telegram/resources/snapshot_excluded_dir_globs.txt`
- `src/coding_agent_telegram/resources/snapshot_excluded_file_globs.txt`

Vous pouvez surcharger ces valeurs dans le fichier env sans modifier le package installé :

- `SNAPSHOT_INCLUDE_PATH_GLOBS`
  Force l'inclusion des chemins correspondants dans les diffs.
  Exemple : `.github/*,.profile.test,.profile.prod`

- `SNAPSHOT_EXCLUDE_PATH_GLOBS`
  Ajoute des exclusions de diff supplémentaires au-dessus des valeurs par défaut du package.
  Exemple : `.*,personal/*,sensitive*.txt`
  Remarque : `.*` couvre les chemins cachés, y compris les fichiers dans des dossiers cachés.

Si une règle d'inclusion et une règle d'exclusion correspondent toutes les deux, l'inclusion l'emporte.

## 🌿 Comportement des branch

Le bot traite le projet et la branch comme un ensemble.

- choisir un projet ne sélectionne pas silencieusement une branch sans rapport
- si une branch est nécessaire, le bot vous demande de la choisir
- lorsque des informations de branch sont affichées dans des messages liés à la session, le projet et la branch sont montrés ensemble

Quand vous créez ou changez une branch, le bot vous guide explicitement sur la source :

- `local/<branch>` : utiliser la branch locale comme source
- `origin/<branch>` : mettre à jour depuis la branch distante puis basculer

Si le bot détecte que la branch stockée dans la session ne correspond pas à la branch courante du dépôt, il ne continue pas à l'aveugle. Il vous demande quelle branch utiliser :

- conserver la branch enregistrée dans la session
- conserver la branch courante du dépôt

Si votre branch source préférée est introuvable, le bot propose des sources de secours basées sur la branch par défaut et la branch courante au lieu de vous laisser face à une erreur Git brute.

## 🔐 Comportement de trust Git

- les dossiers existants suivent `CODEX_SKIP_GIT_REPO_CHECK`
- les dossiers créés via `/project <name>` sont marqués trusted par cette app
- les dossiers existants sélectionnés via `/project <name>` restent untrusted jusqu'à votre confirmation dans Telegram
- les nouveaux dossiers de projet peuvent donc être utilisés immédiatement
- `/commit` peut être désactivé complètement avec `ENABLE_COMMIT_COMMAND`
- les opérations `/commit` qui modifient des fichiers ne sont autorisées que pour les projets trusted

## 🪵 Logs

Les logs sont écrits **à la fois sur stdout et dans un fichier rotatif** sous :

- `~/.coding-agent-telegram/logs` (rotation à 10 MB, 3 sauvegardes conservées)

> **Remarque :** si vous surveillez le terminal **et** le fichier de log en même temps, chaque message apparaît deux fois. C'est attendu. Utilisez l'un ou l'autre, pas les deux simultanément.

<details>
<summary><b>Événements généralement enregistrés</b></summary>

- démarrage du bot et début du polling
- sélection du projet
- création de session
- changement de session
- affichage de la session active
- exécution normale (avec une ligne d'audit contenant un prompt tronqué)
- remplacement de session après échec de reprise
- avertissements et erreurs runtime
</details>

## 🗂️ Structure du projet

- `src/coding_agent_telegram/`
  code principal de l'application

- `tests/`
  suite de tests

- `startup.sh`
  point d'entrée local pour le bootstrap et le démarrage

- `src/coding_agent_telegram/resources/.env.example`
  modèle d'environnement canonique utilisé à la fois par le démarrage depuis le dépôt et par les installations du package

- `pyproject.toml`
  configuration du packaging et des dépendances

## 📦 Versionnement des releases

Les versions du package sont dérivées des tags Git.

- TestPyPI/test : `v2026.3.26.dev1`
- préversion PyPI : `v2026.3.26rc1`
- version stable PyPI : `v2026.3.26`

## 📌 Remarques

- Ce projet est conçu pour les utilisateurs qui exécutent les agents localement sur leur propre machine.
- Le bot Telegram est une interface de contrôle, pas l'environnement d'exécution lui-même.
- Si vous exécutez plusieurs bots, ils peuvent tous être gérés par un seul processus serveur.
