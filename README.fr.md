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
    <img src="https://img.shields.io/badge/python-3.9+-blue" alt="Python 3.9+" />
  </p>
</div>

<table border="0">
   <tr>
   <td border="0">

   ## ✨ Pourquoi l’utiliser
  - ✅ Léger : pas de framework lourd, transparence totale
  - ✅ Multi-bot : plusieurs chats, plusieurs sessions
  - ✅ Utiliser Telegram pour piloter Codex / Copilot / Claude Code CLI
  - ✅ Révision facile des réponses et des fichiers modifiés dans des blocs de code
  - ✅ Les messages de suivi peuvent être mis en file d’attente pendant qu’un agent travaille
  - ✅ Accepte les messages ✏️ texte, 🌄 image et 🎙️ vocaux

   ## 🔁 Changement fluide entre appareils et sessions

  Démarrez une session dans Telegram, puis reprenez la même session Codex/Copilot/Claude Code CLI plus tard sur votre ordinateur sans friction. Avec `/switch`, vous pouvez aussi repasser simplement de Telegram à la ligne de commande.
  
  - Utilisez `/switch` pour reprendre une session locale
  - Les sessions historiques sont également prises en charge

   ## 🛠️ Flux local typique
   ```bash
   coding-agent-telegram # ou exécutez ./startup.sh
   ```

   ##### Dans Telegram :

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

→ Installation en une ligne : 
```
curl -fsSL https://raw.githubusercontent.com/daocha/coding-agent-telegram/main/install.sh | bash
```

<table>
   <tr>
   <td width="65%" valign="top">

   ## 🔐 Sécurité

- Liste blanche des chats privés via `ALLOWED_CHAT_IDS`
- Un seul agent actif par projet pour réduire les écritures concurrentes
- Les diffs de fichiers sensibles sont masqués
- Les clés API, tokens, valeurs `.env`, certificats, clés SSH et autres contenus de type secret sont masqués avant l’envoi vers Telegram
- Les données d’exécution restent sous `~/.coding-agent-telegram`
- Les dossiers existants peuvent exiger une confirmation de confiance avant les opérations Git modifiantes
- Le serveur n’effectue aucun appel externe caché. Vous gardez le contrôle.
- Fonctionne bien avec le mode sandbox de Codex, sans devoir accorder `danger-full-access`
- L’intégration Claude Code prend en charge des modes de permission configurables ainsi que des listes d’autorisation/interdiction d’outils
   </td>
   <td width="35%" valign="top">

   ## ✅ Prérequis

Avant de démarrer le serveur, assurez-vous d’avoir :

- Python 3.9 ou plus récent
- Un token de bot Telegram créé via _@BotFather_
- Votre identifiant de chat Telegram
- Codex CLI et/ou Copilot CLI et/ou Claude Code CLI installés localement
- [Installation Codex CLI](https://developers.openai.com/codex/cli) / [Installation Copilot CLI](https://github.com/features/copilot/cli) / [Installation Claude Code CLI](https://code.claude.com/docs/en/quickstart)
- [Optionnel] Whisper, ffmpeg
   </td>
   </tr>
</table>

## 🦞 Pourquoi en ai-je besoin si j’ai déjà Openclaw ?
Openclaw offre des capacités très complètes et intègre déjà une boucle d’agent appelée Pi-Agent. C’est un outil riche, pensé pour des cas d’usage plus variés. J’aime aussi Openclaw et j’ai déjà codé avec lui. Mais pour le coding pur, ce n’est pas toujours le meilleur choix à cause du gros system prompt intégré et du contexte supplémentaire. Pour coder, Claude Code / Codex / Copilot restent souvent plus efficaces, plus précis, moins distraits et plus directs. Ce projet reste volontairement simple et se contente d’intégrer Codex / Copilot / Claude Code CLI. Vous déléguez donc directement le travail à Codex / Copilot / Claude Code.

## 🆚 Pourquoi utiliser coding-agent-telegram si j'ai déjà Claude Code + Telegram Plugin ?

| Fonctionnalité | Claude Code + Plugin Telegram officiel | coding-agent-telegram (avec prise en charge de Claude) |
|----------------|-----------------------------------------|--------------------------------------------------------|
| Discussion avec l'IA via Telegram | ✅ | ✅ |
| Modifier le code local et exécuter des commandes | ✅ | ✅ |
| Nécessite une session CLI déjà en cours d'exécution | **Oui** | **Non** (démarre ou reprend automatiquement les sessions) |
| Prise en charge de plusieurs fournisseurs d'IA | ❌ Claude uniquement | ✅ Claude Code, Codex CLI, GitHub Copilot CLI |
| Gestion des projets depuis Telegram | ❌ | ✅ `/project` |
| Gestion des branches depuis Telegram | Commandes Git manuelles | ✅ Workflow `/branch` |
| Créer et changer de session | Limité à la session Claude active | ✅ `/new`, `/switch`, `/current`, `/compact` |
| Reprendre des sessions CLI locales existantes | ❌ | ✅ |
| Continuité des sessions entre plusieurs appareils | Limitée | ✅ |
| Protection contre les modifications simultanées d'un même workspace | ❌ | ✅ Empêche plusieurs agents de modifier le même projet en même temps |
| File d'attente des tâches lorsqu'un agent est occupé | ❌ | ✅ |
| Snapshots et diffs du système de fichiers indépendants | ❌ | ✅ |
| Affichage des diffs structurés directement dans Telegram | ❌ | ✅ |
| Filtrage des secrets et des diffs sensibles | ❌ | ✅ |
| Workflow Git intégré (pull / push / commit) | Manuel | ✅ |
| Prise en charge de plusieurs bots | Plusieurs instances nécessaires | ✅ Gérés par un serveur unique |
| Gestion de l'état au niveau du projet | ❌ | ✅ |
| Architecture indépendante du fournisseur | ❌ | ✅ |

> **Différence principale**
>
> Le plugin Telegram officiel de Claude Code connecte Telegram à **une seule session Claude Code déjà en cours d'exécution**.
>
> **coding-agent-telegram** agit comme un **plan de contrôle Telegram** permettant de gérer les projets, les branches, les sessions, les workflows Git et plusieurs agents de développement (Claude Code, Codex CLI, GitHub Copilot CLI) depuis une interface unique.

### 🏛️ Architecture

#### Claude Code + Telegram Plugin

```text
Telegram
    │
    ▼
Canal Claude Code
    │
    ▼
Une session Claude Code en cours d'exécution
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
Projet • Branche • Session • File d'attente • Git • Diff • Filtre des secrets
```

## 🚀 Démarrage rapide

### Variante A : Script bootstrap en une ligne
```bash
curl -fsSL https://raw.githubusercontent.com/daocha/coding-agent-telegram/main/install.sh | bash
```

### Variante B : Installation depuis PyPI avec `pip`
```bash
pip install coding-agent-telegram
coding-agent-telegram
```

### Variante C : Exécution depuis un dépôt cloné
```bash
git clone https://github.com/daocha/coding-agent-telegram
cd coding-agent-telegram
./startup.sh
```

### 🌐 Démarrer le serveur du bot
##### Au premier lancement, l’application crée le fichier env et vous indique quels champs remplir.
##### Après avoir mis à jour le fichier env, relancez :
```bash
# si vous suivez l’option A ou l’option B, exécutez ensuite
coding-agent-telegram

# si vous suivez l’option C, exécutez ceci de nouveau
./startup.sh
```

## 🎙️ [Optionnel] Fonction de transcription vocale : préparer les prérequis locaux OpenAI-Whisper

Cela active la transcription locale optionnelle des notes vocales Telegram avec Whisper. Les fichiers audio sont limités à `20 MB` maximum.

```bash
# si vous avez installé avec pip ou avec l’install.sh en une ligne
coding-agent-telegram-stt-install

# si vous utilisez un dépôt cloné
./install-stt.sh
```

Réglages env recommandés :

```text
ENABLE_OPENAI_WHISPER_SPEECH_TO_TEXT=true
OPENAI_WHISPER_MODEL=base
OPENAI_WHISPER_TIMEOUT_SECONDS=120
```

Remarques :

- Whisper télécharge automatiquement le modèle sélectionné lors du premier usage dans `~/.cache/whisper`.
- Si vous choisissez `OPENAI_WHISPER_MODEL=turbo`, la première transcription vocale a davantage de chances d’atteindre le délai pendant que `large-v3-turbo.pt` est encore en cours de téléchargement.
- Après transcription d’un message vocal, le bot renvoie d’abord le texte reconnu dans Telegram avant de l’envoyer à l’agent. Cela aide à diagnostiquer les erreurs de reconnaissance.

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

Le bot accepte actuellement :

- les messages texte
- les photos
- les messages vocaux et les fichiers audio quand `ENABLE_OPENAI_WHISPER_SPEECH_TO_TEXT=true` et que les prérequis locaux de Whisper sont installés
- Codex et Claude Code prennent en charge le texte et les images ; Copilot ne prend actuellement en charge que le texte. Aucun fournisseur ne prend en charge la vidéo.

## 🤖 Commandes Telegram

<table>
  <tr>
    <td width="332"><code>/provider</code></td>
    <td>Choisir le fournisseur pour les nouvelles sessions. Le choix est stocké par bot et par chat jusqu’à modification.</td>
  </tr>
  <tr>
    <td width="332"><code>/project &lt;project_folder&gt;</code></td>
    <td>Définir le dossier de projet courant. Si le dossier n’existe pas, l’app le crée et le marque trusted. S’il existe déjà mais reste untrusted, l’app vous demande une confirmation.</td>
  </tr>
  <tr>
    <td width="332"><code>/branch &lt;new_branch&gt;</code></td>
    <td>Préparer ou changer une branch pour le projet courant. Si la branch existe déjà, le bot la traite comme source candidate. Sinon il utilise la branch par défaut du dépôt.</td>
  </tr>
  <tr>
    <td width="332"><code>/branch &lt;origin_branch&gt; &lt;new_branch&gt;</code></td>
    <td>Préparer ou changer une branch en utilisant <code>&lt;origin_branch&gt;</code> comme source candidate. Pour les deux formes, le bot ne propose ensuite que les sources réellement disponibles : <code>local/&lt;branch&gt;</code> et <code>origin/&lt;branch&gt;</code>. Si une seule existe, seule celle-ci est affichée. Si aucune n’existe, le bot signale que la source de branch est introuvable.</td>
  </tr>
  <tr>
    <td width="332"><code>/current</code></td>
    <td>Afficher la session active pour le bot et le chat courants.</td>
  </tr>
  <tr>
    <td><code>/status</code></td>
    <td>Affiche l'utilisation du quota de chaque fournisseur : pourcentages d'utilisation sur 5 heures et hebdomadaire, avec les heures de réinitialisation. Ne déclenche jamais un appel API payant : Codex est toujours une requête locale gratuite, et les chiffres de Claude sont réutilisés uniquement depuis votre dernière activité Claude réelle via le bot, affichés comme « observé pour la dernière fois il y a X » (comptes Pro/Max connectés via OAuth uniquement). Les deux fenêtres sont suivies séparément : si l'une a dépassé son heure de réinitialisation (ou n'a encore jamais été observée), elle affiche N/A jusqu'à ce que votre prochain tour Claude la rafraîchisse, même si l'autre fenêtre a encore des données à jour. Copilot n'a pas d'API prise en charge pour cela et est signalé comme indisponible.</td>
  </tr>
  <tr>
    <td width="332"><code>/new [session_name]</code></td>
    <td>Créer une nouvelle session pour le projet courant. Si vous omettez le nom, le bot utilise le véritable ID de session. Si fournisseur, projet ou branch manque, le bot vous guide.</td>
  </tr>
  <tr>
    <td width="332"><code>/switch</code></td>
    <td>Afficher les sessions les plus récentes, de la plus récente à la plus ancienne. La liste inclut les sessions gérées par le bot et les sessions locales Codex/Copilot/Claude Code CLI du projet courant.</td>
  </tr>
  <tr>
    <td width="332"><code>/switch page &lt;number&gt;</code></td>
    <td>Afficher une autre page des sessions enregistrées.</td>
  </tr>
  <tr>
    <td width="332"><code>/switch &lt;session_id&gt;</code></td>
    <td>Basculer vers une session précise via son ID. Si vous choisissez une session CLI locale, le bot l’importe et reprend à partir d’elle.</td>
  </tr>
  <tr>
    <td width="332"><code>/compact</code></td>
    <td>Créer une nouvelle session compactée à partir de la session active et basculer dessus.</td>
  </tr>
  <tr>
    <td width="332"><code>/commit &lt;git commands&gt;</code></td>
    <td>Exécuter des commandes liées à <code>git commit</code> validées dans le projet de la session active. Disponible uniquement si <code>ENABLE_COMMIT_COMMAND=true</code>. Les commandes Git mutantes exigent un projet trusted.</td>
  </tr>
  <tr>
    <td width="332"><code>/diff</code></td>
    <td>Afficher les noms des fichiers modifiés du projet de la session active, séparés entre fichiers suivis et non suivis. Les fichiers suivis proposent des boutons inline pour ouvrir le diff de chaque fichier.</td>
  </tr>
  <tr>
    <td width="332"><code>/pull</code></td>
    <td>Après confirmation, exécuter un <code>pull</code> depuis <code>origin</code> pour la branche de la session active. Le bot rafraîchit aussi la branche par défaut si nécessaire.</td>
  </tr>
  <tr>
    <td width="332"><code>/push</code></td>
    <td>Pousser <code>origin &lt;branch&gt;</code> pour la session active courante. Le bot demande une confirmation avant le push.</td>
  </tr>
  <tr>
    <td width="332"><code>/abort</code></td>
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
    <td width="332"><code>WORKSPACE_ROOT</code></td>
    <td>Dossier parent qui contient vos répertoires de projet.</td>
  </tr>
  <tr>
    <td width="332"><code>TELEGRAM_BOT_TOKENS</code></td>
    <td>Liste de tokens de bot Telegram séparés par des virgules.</td>
  </tr>
  <tr>
    <td width="332"><code>ALLOWED_CHAT_IDS</code></td>
    <td>Liste d’IDs de chat privés Telegram autorisés, séparés par des virgules.</td>
  </tr>
</table>

<h3>Réglages courants</h3>

<table>
  <tr>
    <td width="332"><code>APP_LOCALE</code></td>
    <td>Langue de l’interface pour les messages partagés du bot et les descriptions de commandes. Valeurs prises en charge : <code>en</code>, <code>de</code>, <code>fr</code>, <code>ja</code>, <code>ko</code>, <code>nl</code>, <code>th</code>, <code>vi</code>, <code>zh-CN</code>, <code>zh-HK</code>, <code>zh-TW</code>.</td>
  </tr>
  <tr>
    <td width="332"><code>DEFAULT_AGENT_PROVIDER</code></td>
    <td>Fournisseur par défaut pour les nouvelles sessions : <code>codex</code>, <code>copilot</code>, ou <code>claude</code>. Valeur par défaut : <code>codex</code>.</td>
  </tr>
  <tr>
    <td width="332"><code>CODEX_BIN</code></td>
    <td>Commande utilisée pour lancer Codex CLI. L'application essaiera de détecter automatiquement le chemin d'installation local de Codex lors de l'initialisation de <code>.env_coding_agent_telegram</code>. Vous pouvez également utiliser <code>which codex</code> pour afficher ce chemin.</td>
  </tr>
  <tr>
    <td width="332"><code>COPILOT_BIN</code></td>
    <td>Commande utilisée pour lancer Copilot CLI. L'application essaiera de détecter automatiquement le chemin d'installation local de Copilot lors de l'initialisation de <code>.env_coding_agent_telegram</code>. Vous pouvez également utiliser <code>which copilot</code> pour afficher ce chemin.</td>
  </tr>
  <tr>
    <td width="332"><code>CLAUDE_BIN</code></td>
    <td>Commande utilisée pour lancer Claude Code CLI. L'application essaiera de détecter automatiquement le chemin d'installation local de Claude lors de l'initialisation de <code>.env_coding_agent_telegram</code>. Vous pouvez également utiliser <code>which claude</code> pour afficher ce chemin.</td>
  </tr>
  <tr>
    <td width="332"><code>CODEX_MODEL</code></td>
    <td>Remplacement optionnel du modèle Codex. Laissez vide pour utiliser le modèle par défaut de Codex CLI. Exemple : <code>gpt-5.4</code> <a href="https://developers.openai.com/codex/models" target="_blank">Modèles OpenAI Codex/OpenAI</a></td>
  </tr>
  <tr>
    <td width="332"><code>COPILOT_MODEL</code></td>
    <td>Remplacement optionnel du modèle Copilot. Laissez vide pour utiliser le modèle par défaut de Copilot CLI. Exemples : <code>gpt-5.4</code>, <code>claude-sonnet-4.6</code> <a href="https://docs.github.com/en/copilot/reference/ai-models/supported-models" target="_blank">Modèles pris en charge par GitHub Copilot</a></td>
  </tr>
  <tr>
    <td width="332"><code>CLAUDE_MODEL</code></td>
    <td>Remplacement optionnel du modèle Claude Code.
    Laissez vide pour utiliser le modèle par défaut de Claude Code CLI.
    Exemples : <code>sonnet</code>, <code>opus</code>, <code>haiku</code>
    <a href="https://code.claude.com/docs/en/model-config" target="_blank">Configuration des modèles Claude Code</a>
    </td>
  </tr>
  <tr>
    <td width="332"><code>CODEX_APPROVAL_POLICY</code></td>
    <td>Mode d’approbation transmis à Codex. Défaut : <code>never</code>.</td>
  </tr>
  <tr>
    <td width="332"><code>CODEX_SANDBOX_MODE</code></td>
    <td>Mode sandbox transmis à Codex. Défaut : <code>workspace-write</code>.</td>
  </tr>
  <tr>
    <td width="332"><code>CODEX_SKIP_GIT_REPO_CHECK</code></td>
    <td>Si activé, contourne toujours les vérifications de dépôt trusted de Codex.</td>
  </tr>
  <tr>
    <td width="332"><code>CLAUDE_PERMISSION_MODE</code></td>
    <td>Mode de permission transmis à Claude Code. Un parmi <code>default</code>, <code>acceptEdits</code>, <code>plan</code>, <code>auto</code>, <code>dontAsk</code>, <code>bypassPermissions</code>, <code>manual</code>. Défaut : <code>bypassPermissions</code> (entièrement autonome, puisqu’il n’y a pas de terminal interactif pour approuver les invites).</td>
  </tr>
  <tr>
    <td width="332"><code>CLAUDE_ALLOWED_TOOLS</code></td>
    <td>Liste blanche d’outils Claude Code séparés par des virgules, utilisant la syntaxe des règles de permission de Claude Code. Exemple : <code>Read,Edit,Bash(git *)</code></td>
  </tr>
  <tr>
    <td width="332"><code>CLAUDE_DISALLOWED_TOOLS</code></td>
    <td>Liste noire d’outils Claude Code séparés par des virgules. Exemple : <code>Bash(rm *)</code></td>
  </tr>
  <tr>
    <td width="332"><code>ENABLE_COMMIT_COMMAND</code></td>
    <td>Active la commande Telegram <code>/commit</code>. Défaut : <code>false</code>.</td>
  </tr>
  <tr>
    <td width="332"><code>AGENT_HARD_TIMEOUT_SECONDS</code></td>
    <td>Timeout dur pour une exécution d’agent. Défaut : <code>0</code> (désactivé).</td>
  </tr>
  <tr>
    <td width="332"><code>LONG_GAP_WARNING_ENABLED</code></td>
    <td>Avant de reprendre une session restée inactive un moment <em>et</em> ayant accumulé assez de contexte pour qu'un retraitement soit coûteux, avertit que le cache de prompt du fournisseur a probablement expiré — avec des boutons pour compacter d'abord ou continuer quand même. Défaut : <code>true</code>. Voir la FAQ ci-dessous.</td>
  </tr>
  <tr>
    <td width="332"><code>CLAUDE_LONG_GAP_SECONDS</code></td>
    <td>Seuil d'inactivité en secondes avant que l'avertissement se déclenche pour les sessions Claude Code. Défaut : <code>3600</code> (1 heure, correspondant à la fenêtre de cache de prompt étendue de Claude Code).</td>
  </tr>
  <tr>
    <td width="332"><code>CODEX_LONG_GAP_SECONDS</code></td>
    <td>Seuil d'inactivité en secondes avant que l'avertissement se déclenche pour les sessions Codex. Défaut : <code>3600</code> (1 heure, comme pour Claude ; OpenAI ne documente aucun chiffre d'expiration de cache basé sur l'inactivité pour Codex, et le cache propre de Codex est de toute façon généralement plus éphémère que celui de Claude, donc s'aligner sur le seuil de Claude ne coûte rien en précision — combiné au filtre de taille pour que les petites sessions n'agacent pas).</td>
  </tr>
  <tr>
    <td width="332"><code>COPILOT_LONG_GAP_SECONDS</code></td>
    <td>Seuil d'inactivité en secondes avant que l'avertissement se déclenche pour les sessions Copilot. Défaut : <code>0</code> (désactivé). La documentation officielle de GitHub indique que Copilot CLI n'a aucun délai d'inactivité et compacte déjà nativement son propre contexte (autour de 80-95 % d'utilisation) — il n'y a ici aucun risque lié à l'inactivité à signaler, donc ceci s'en remet au mécanisme propre de Copilot plutôt que d'en inventer un. Définissez une valeur positive pour activer quand même une alerte basée sur l'inactivité pour Copilot.</td>
  </tr>
  <tr>
    <td width="332"><code>SNAPSHOT_TEXT_FILE_MAX_BYTES</code></td>
    <td>Taille maximale de fichier que le bot lira en texte pour construire le instantané avant/après des diffs. Défaut : <code>200000</code>.</td>
  </tr>
  <tr>
    <td width="332"><code>MAX_TELEGRAM_MESSAGE_LENGTH</code></td>
    <td>Taille maximale d’un message avant découpage de la réponse. Défaut : <code>3000</code>.</td>
  </tr>
  <tr>
    <td width="332"><code>ENABLE_SENSITIVE_DIFF_FILTER</code></td>
    <td>Masquer les diffs des fichiers sensibles. Défaut : <code>true</code>.</td>
  </tr>
  <tr>
    <td width="332"><code>ENABLE_SECRET_SCRUB_FILTER</code></td>
    <td>Masquer tokens, clés, valeurs <code>.env</code>, certificats et sorties similaires avant envoi vers Telegram. Défaut : <code>true</code> (fortement recommandé).</td>
  </tr>
  <tr>
    <td width="332"><code>SNAPSHOT_INCLUDE_PATH_GLOBS</code></td>
    <td>Toujours inclure les chemins correspondants dans les diffs. Exemple : <code>.github/*,.profile.test,.profile.prod</code></td>
  </tr>
  <tr>
    <td width="332"><code>SNAPSHOT_EXCLUDE_PATH_GLOBS</code></td>
    <td>Ajouter des exclusions de diff supplémentaires au-dessus des valeurs par défaut du paquet. Exemple : <code>.*,personal/*,sensitive*.txt</code> Remarque : <code>.*</code> inclut les chemins cachés, y compris les fichiers dans les dossiers cachés.</td>
  </tr>
</table>




<h3>Reconnaissance vocale</h3>

<table>
  <tr>
    <td width="332"><code>ENABLE_OPENAI_WHISPER_SPEECH_TO_TEXT</code></td>
    <td>Valeur par défaut : <code>false</code>. Si activé, la reconnaissance des messages vocaux et des fichiers audio est disponible. Le système vérifie les binaires ou bibliothèques requis et invite l’utilisateur à les installer si nécessaire.</td>
  </tr>
  <tr>
    <td><code>OPENAI_WHISPER_MODEL</code></td>
    <td>Modèle utilisé pour la STT Whisper. Valeur par défaut : <code>base</code><br />Modèles disponibles : <code>tiny</code> environ <code>72 MB</code>, <code>base</code> environ <code>139 MB</code>, <code>large-v3-turbo</code> environ <code>1.5 GB</code><br />Les modèles sont téléchargés automatiquement lors de votre premier message vocal. Recommandé : <code>base</code> pour un usage général. Si vous souhaitez une meilleure précision et qualité, vous pouvez essayer <code>turbo</code>.</td>
  </tr>
  <tr>
    <td><code>OPENAI_WHISPER_TIMEOUT_SECONDS</code></td>
    <td>Valeur par défaut : <code>120</code>. Délai d’expiration du processus STT. En général, le traitement est assez rapide. Mais si vous choisissez <code>turbo</code>, le premier message vocal peut dépasser ce délai pendant le téléchargement du modèle selon la vitesse de votre connexion.</td>
  </tr>
</table>

<h3>État et logs</h3>

<table>
  <tr>
    <td><code>~/.coding-agent-telegram/state.json</code></td>
    <td>Fichier principal de l’état des sessions.</td>
  </tr>
  <tr>
    <td><code>~/.coding-agent-telegram/state.json.bak</code></td>
    <td>Fichier de sauvegarde de l’état.</td>
  </tr>
  <tr>
    <td><code>~/.coding-agent-telegram/logs</code></td>
    <td>Répertoire des logs.</td>
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
CLAUDE_BIN=claude
CODEX_APPROVAL_POLICY=never
CODEX_SANDBOX_MODE=workspace-write
CLAUDE_PERMISSION_MODE=bypassPermissions
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

- dossier de projet
- fournisseur
- nom de branch quand disponible

<details>
<summary><b>Chaque session stocke :</b></summary>

- nom de session
- dossier de projet
- nom de branch
- fournisseur
- horodatages
- sélection de session active pour cette portée bot/chat
</details>

### 🔓 Verrou de concurrence du workspace

Une seule exécution d'agent peut être active à la fois par **dossier de projet**, quel que soit le chat ou le bot Telegram qui l'a déclenchée.

- **le projet est occupé** : un agent est déjà en cours dans cet espace de travail
- **l’agent est occupé** : cette exécution unique traite encore la requête courante

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

_Pendant chaque exécution d'agent, le bot prend aussi un léger instantané avant/après du projet afin de résumer les fichiers modifiés et d'envoyer des diffs vers Telegram. Ce instantané est produit par le bot lui-même, pas par Codex, Copilot ou Claude Code._

**À savoir sur le instantané :**

- l'app parcourt le dossier du projet avant et après l'exécution
- pour les fichiers texte normaux, l'app préfère le diff du instantané du run plutôt qu'un diff contre le head Git
- les répertoires courants de dépendances, cache et runtime sont aussi ignorés
- les fichiers binaires et les fichiers plus gros que `SNAPSHOT_TEXT_FILE_MAX_BYTES` ne sont pas lus comme texte
- sur les très gros projets, ce scan supplémentaire peut ajouter un surcoût notable en I/O et en mémoire
- si un instantané ne peut pas représenter un fichier comme texte, l'app retombe sur `git diff` lorsque c'est possible
- pour les gros fichiers ou les fichiers non textuels, le diff peut quand même être omis et remplacé par un court message

Les règles d'exclusion du instantané se trouvent dans les ressources du paquet :

- `src/coding_agent_telegram/resources/instantané_excluded_dir_names.txt`
- `src/coding_agent_telegram/resources/instantané_excluded_dir_globs.txt`
- `src/coding_agent_telegram/resources/instantané_excluded_file_globs.txt`

Vous pouvez surcharger ces valeurs dans le fichier env sans modifier le paquet installé :

- `SNAPSHOT_INCLUDE_PATH_GLOBS`
  Force l'inclusion des chemins correspondants dans les diffs.
  Exemple : `.github/*,.profile.test,.profile.prod`

- `SNAPSHOT_EXCLUDE_PATH_GLOBS`
  Ajoute des exclusions de diff supplémentaires au-dessus des valeurs par défaut du paquet.
  Exemple : `.*,personal/*,sensitive*.txt`
  Remarque : `.*` couvre les chemins cachés, y compris les fichiers dans des dossiers cachés.

Si une règle d'inclusion et une règle d'exclusion correspondent toutes les deux, l'inclusion l'emporte.

## 🌿 Comportement des branch

Le bot traite le projet et la branch comme un ensemble.

- choisir un projet ne sélectionne pas silencieusement une branch sans rapport
- si une branch est nécessaire, le bot vous demande de la choisir
- lorsque des informations de branch sont affichées dans des messages liés à la session, le projet et la branch sont montrés ensemble

Quand vous créez ou changez une branch, le bot vous guide explicitement sur la source :

- <code>local/&lt;branch&gt;</code> : utiliser la branch locale comme source
- <code>origin/&lt;branch&gt;</code> : mettre à jour depuis la branch distante puis basculer

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

## 🪵 Journaux

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
  modèle d'environnement canonique utilisé à la fois par le démarrage depuis le dépôt et par les installations du paquet

- `pyproject.toml`
  configuration du packaging et des dépendances

## 📦 Versionnement des releases

Les versions du paquet sont dérivées des tags Git.

- TestPyPI/test : `v2026.3.26.dev1`
- préversion PyPI : `v2026.3.26rc1`
- version stable PyPI : `v2026.3.26`

## ❓ FAQ / Dépannage

<details>
<summary><b>Pourquoi <code>claude --resume</code> dans un terminal classique n'affiche-t-il aucune session créée depuis Telegram ?</b></summary>

C'est un comportement attendu de la CLI Claude Code, pas un bug de cette app.

Les sessions créées par ce bot passent par le mode headless `-p`/print de Claude Code. Claude Code marque toute session démarrée ainsi avec `entrypoint: "sdk-cli"` dans sa transcription, contre `entrypoint: "cli"` pour une session que vous démarrez en tapant directement `claude` dans un terminal. Le sélecteur interactif `claude --resume` (sans ID de session) ne liste que les sessions avec un entrypoint `cli` — il masque délibérément les runs headless/pilotés par le SDK, les traitant comme de la sortie d'automatisation plutôt que des conversations destinées à être reprises à la main.

Les données de session elles-mêmes ne sont ni perdues ni différentes — c'est une session Claude Code normale et totalement reprenable, stockée sous `~/.claude/projects/<encoded-project-path>/<session-id>.jsonl`. Vous pouvez la reprendre directement une fois l'ID en main :

```bash
claude --resume <session-id>
```

C'est exactement pour ça que cette app embarque sa propre découverte de sessions (utilisée par `/switch`) au lieu de se fier au sélecteur natif — elle scanne directement les fichiers JSONL et les associe par chemin de projet, si bien que les sessions créées depuis Telegram y apparaissent même si elles n'apparaissent jamais dans un simple `claude --resume`.

Codex et Copilot ne font pas cette distinction interactif/headless dans leurs propres commandes de reprise/liste, ce qui explique pourquoi les sessions de ces fournisseurs continuent d'apparaître normalement dans un terminal classique.
</details>

<details>
<summary><b>Cette app consomme-t-elle plus de tokens que l'utilisation directe du terminal Claude Code ?</b></summary>

Pas à cause d'une différence de surcoût inhérente par appel — le mode headless (`-p`) et Claude Code interactif utilisent le même protocole sous-jacent et la même tarification. Mais en pratique, un usage Telegram 24/7 peut consommer nettement plus de tokens qu'un usage terminal classique, pour deux raisons qui se cumulent :

- **Les sessions peuvent grossir sans limite.** Comme le bot reprend commodément la même session sur des heures voire des jours, une session peut accumuler des centaines d'échanges et des mégaoctets de transcription si vous ne la faites jamais tourner. Dans un terminal interactif, vous auriez plus naturellement tendance à finir une tâche et repartir de zéro la fois suivante, gardant ainsi un contexte plus petit.
- **Les intervalles d'inactivité entre messages Telegram font expirer le cache de prompt.** Le cache de prompt de Claude a une durée de vie courte. Si vous répondez dans cette fenêtre, les échanges suivants sont des lectures de cache peu coûteuses. S'il y a un long intervalle (par exemple vous dormez et répondez le lendemain matin), tout le contexte accumulé doit être retraité intégralement lors de votre prochain message, sous forme d'une écriture de cache bien plus coûteuse — et ce coût augmente avec la taille déjà atteinte par la session. C'est pourquoi la consommation peut s'envoler dès votre premier message de la journée, même avant les heures de « pointe ».

**Mitigation :** exécutez périodiquement `/compact` sur les sessions longue durée (cette app le prend en charge comme commande Telegram) plutôt que de laisser une session tourner indéfiniment, surtout si vous remarquez qu'elle est restée inactive longtemps. Démarrer une nouvelle session `/new` pour un travail sans rapport aide aussi à garder le contexte — et le coût — sous contrôle.

L'app le fait désormais aussi automatiquement, en combinant deux signaux par fournisseur pour ne vous interrompre que quand c'est vraiment susceptible d'importer : un seuil d'inactivité (`CLAUDE_LONG_GAP_SECONDS` / `CODEX_LONG_GAP_SECONDS` / `COPILOT_LONG_GAP_SECONDS`) *et* la quantité de contexte déjà accumulée par la session (l'avertissement est ignoré pour les petites sessions peu coûteuses même après une longue inactivité, puisque les retraiter depuis zéro est alors négligeable). Valeurs par défaut : 1 heure pour Claude Code comme pour Codex — le chiffre de Claude repose sur des données réelles (voir plus haut), et bien qu'OpenAI n'en documente aucun pour Codex, le cache propre de Codex est de toute façon généralement plus éphémère que celui de Claude, donc s'aligner sur le seuil de Claude ne coûte rien en précision et se traduit simplement par moins d'interruptions, surtout désormais combiné au filtre de taille ; et désactivé par défaut pour Copilot, car [la documentation officielle de GitHub](https://docs.github.com/en/copilot/concepts/agents/copilot-cli/context-management) indique que Copilot CLI n'a aucun délai d'inactivité et compacte déjà nativement son propre contexte (autour de 80-95 % d'utilisation) — il n'y a là rien de lié à l'inactivité à signaler, donc ceci s'en remet au mécanisme propre de Copilot plutôt que d'en inventer un. Définissez `COPILOT_LONG_GAP_SECONDS` à une valeur positive si vous voulez quand même une alerte basée sur l'inactivité pour Copilot.

Quand le seuil et le filtre de taille sont tous deux atteints, elle retient votre message et demande :

> ⏳ Cette session est inactive depuis {gap}. La reprendre maintenant va probablement retraiter toute la conversation depuis le début (le cache de réponses du fournisseur a sans doute expiré), ce qui peut consommer bien plus de tokens que d'habitude. Compacter retraite aussi le contexte actuel une fois pour rédiger son résumé, donc cela peut aussi consommer beaucoup de tokens si cette session est déjà volumineuse. Basculer vers une nouvelle session évite complètement ce retraitement, mais démarre sans aucune mémoire de cette conversation. Basculer vers une nouvelle session, compacter d'abord, ou continuer quand même ?
>
> [🆕 Basculer vers une nouvelle session]
> [🔄 Compacter d'abord]
> [⚠️ Continuer quand même]

Notez que `/compact` lui-même n'est pas exempt de ce coût : il fonctionne en reprenant la session actuelle (potentiellement froide) et en lui demandant de se résumer elle-même, donc il paie le même retraitement complet et ponctuel du transcript que le simple fait de répondre — la différence est que vous ne le payez alors qu'une seule fois plutôt qu'à chaque tour suivant, puisque la session résultante démarre petite. **Basculer vers une nouvelle session** est la seule option qui évite entièrement ce retraitement : elle abandonne le contexte de l'ancienne session sans jamais la reprendre et repart entièrement à zéro, au prix de perdre ce contexte entièrement plutôt que de le condenser en résumé.

Choisir **Basculer vers une nouvelle session** démarre une session toute neuve et vide, puis y poursuit avec votre message — nommée d'après l'ancienne session avec un suffixe `-newN` incrémental (par ex. `fix-bug` → `fix-bug-new1` → `fix-bug-new2` si vous basculez à nouveau), pour pouvoir toujours la distinguer de l'originale dans `/switch`. Choisir **Compacter d'abord** résume la session, en démarre une nouvelle à partir de ce résumé, puis poursuit avec votre message sur la nouvelle session — nommée de façon similaire mais avec un suffixe `-resumeN` (par ex. `fix-bug` → `fix-bug-resume1` → `fix-bug-resume2` à la compaction suivante). Choisir **Continuer quand même** poursuit simplement sur la session existante comme d'habitude. Désactivez tout le mécanisme avec `LONG_GAP_WARNING_ENABLED=false`.
</details>

## 📌 Remarques

- Ce projet est conçu pour les utilisateurs qui exécutent les agents localement sur leur propre machine.
- Le bot Telegram est une interface de contrôle, pas l'environnement d'exécution lui-même.
- Si vous exécutez plusieurs bots, ils peuvent tous être gérés par un seul processus serveur.
