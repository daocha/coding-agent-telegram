#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

DEFAULT_ENV_FILE=".env_coding_agent_telegram"
PYTHON_BIN="${PYTHON_BIN:-python3}"
ENV_FILE="${ENV_FILE:-}"
ENV_TEMPLATE_FILE="${ENV_TEMPLATE_FILE:-src/coding_agent_telegram/resources/.env.example}"
VENV_DIR="${VENV_DIR:-.venv}"

resolve_user_home() {
  "$PYTHON_BIN" - <<'PY'
from pathlib import Path
import os
import pwd

sudo_user = os.getenv("SUDO_USER", "").strip()
if sudo_user and sudo_user != "root":
    try:
        print(pwd.getpwnam(sudo_user).pw_dir)
    except KeyError:
        print(Path.home())
else:
    print(Path.home())
PY
}

if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
  echo "Error: $PYTHON_BIN was not found in PATH." >&2
  exit 1
fi

APP_HOME_DIR="$(resolve_user_home)/.coding-agent-telegram"
HOME_ENV_FILE="$APP_HOME_DIR/$DEFAULT_ENV_FILE"
STATE_FILE_DEFAULT="$APP_HOME_DIR/state.json"
STATE_BACKUP_FILE_DEFAULT="$APP_HOME_DIR/state.json.bak"
LOG_DIR_DEFAULT="$APP_HOME_DIR/logs"
LOCAL_PRETEND_VERSION="${SETUPTOOLS_SCM_PRETEND_VERSION_FOR_CODING_AGENT_TELEGRAM:-0.0.dev0}"
INSTALL_STATE_FILE_NAME=".coding-agent-telegram-install-state"
FORCE_REINSTALL="${FORCE_REINSTALL:-0}"

compute_install_fingerprint() {
  local files=()
  local file
  for file in pyproject.toml setup.py; do
    if [[ -f "$file" ]]; then
      files+=("$file")
    fi
  done
  if [[ "${#files[@]}" -eq 0 ]]; then
    printf 'no-packaging-files\n'
    return
  fi
  shasum -a 256 "${files[@]}" | shasum -a 256 | awk '{print $1}'
}

if [[ -z "$ENV_FILE" ]]; then
  if [[ -f "$HOME_ENV_FILE" ]]; then
    ENV_FILE="$HOME_ENV_FILE"
  elif [[ -f "$DEFAULT_ENV_FILE" ]]; then
    ENV_FILE="$DEFAULT_ENV_FILE"
  else
    ENV_FILE="$HOME_ENV_FILE"
  fi
fi

NEW_ENV_CREATED=0
if [[ ! -f "$ENV_FILE" ]]; then
  if [[ -f "$ENV_TEMPLATE_FILE" ]]; then
    ENV_FILE_TARGET="$ENV_FILE" ENV_TEMPLATE_SOURCE="$ENV_TEMPLATE_FILE" PYTHONPATH="$SCRIPT_DIR/src${PYTHONPATH:+:$PYTHONPATH}" "$PYTHON_BIN" - <<'PY'
from pathlib import Path
import os
from coding_agent_telegram.config import create_initial_env_file
from coding_agent_telegram.i18n import translate

env_path = Path(os.environ["ENV_FILE_TARGET"]).expanduser()
template_path = Path(os.environ["ENV_TEMPLATE_SOURCE"]).expanduser()
app_locale = create_initial_env_file(env_path, template_path)
print(translate(app_locale, "bootstrap.env_created_locale_line", env_path=env_path, app_locale=app_locale))
print(translate(app_locale, "bootstrap.env_created_change_line", env_path=env_path))
PY
    NEW_ENV_CREATED=1
  else
    echo "Error: $ENV_FILE is missing and $ENV_TEMPLATE_FILE was not found." >&2
    exit 1
  fi
fi

STATE_FILE="$STATE_FILE_DEFAULT"
STATE_BACKUP_FILE="$STATE_BACKUP_FILE_DEFAULT"
if [[ -f "$APP_HOME_DIR/state.json" ]]; then
  STATE_FILE="$APP_HOME_DIR/state.json"
elif [[ -f "./state.json" ]]; then
  STATE_FILE="./state.json"
fi
if [[ -f "$APP_HOME_DIR/state.json.bak" ]]; then
  STATE_BACKUP_FILE="$APP_HOME_DIR/state.json.bak"
elif [[ -f "./state.json.bak" ]]; then
  STATE_BACKUP_FILE="./state.json.bak"
fi
LOG_DIR="$LOG_DIR_DEFAULT"

mkdir -p "$(dirname "$STATE_FILE")" "$(dirname "$STATE_BACKUP_FILE")" "$LOG_DIR"
touch "$STATE_FILE" "$STATE_BACKUP_FILE"

if [[ ! -d "$VENV_DIR" ]]; then
  "$PYTHON_BIN" -m venv "$VENV_DIR"
fi

source "$VENV_DIR/bin/activate"

python -m pip install --upgrade pip >/dev/null
INSTALL_STATE_FILE="$VENV_DIR/$INSTALL_STATE_FILE_NAME"
CURRENT_INSTALL_FINGERPRINT="$(compute_install_fingerprint)"
STORED_INSTALL_FINGERPRINT=""
if [[ -f "$INSTALL_STATE_FILE" ]]; then
  STORED_INSTALL_FINGERPRINT="$(<"$INSTALL_STATE_FILE")"
fi

NEEDS_REINSTALL=0
if [[ "$FORCE_REINSTALL" == "1" ]]; then
  NEEDS_REINSTALL=1
elif ! python -c "import coding_agent_telegram" >/dev/null 2>&1; then
  NEEDS_REINSTALL=1
elif [[ "$CURRENT_INSTALL_FINGERPRINT" != "$STORED_INSTALL_FINGERPRINT" ]]; then
  NEEDS_REINSTALL=1
fi

if [[ "$NEEDS_REINSTALL" == "1" ]]; then
  echo "Installing local package into $VENV_DIR."
  SETUPTOOLS_SCM_PRETEND_VERSION_FOR_CODING_AGENT_TELEGRAM="$LOCAL_PRETEND_VERSION" \
    python -m pip install -e .
  printf '%s\n' "$CURRENT_INSTALL_FINGERPRINT" > "$INSTALL_STATE_FILE"
else
  echo "Existing editable install detected; skipping reinstall."
fi

if [[ "$NEW_ENV_CREATED" == "1" ]]; then
  python -m coding_agent_telegram.stt_setup offer \
    --env-file "$ENV_FILE" \
    --python-bin "$VENV_DIR/bin/python" \
    --installer-label "./install-stt.sh"
fi

set -a
source "$ENV_FILE"
set +a

required_vars=(
  WORKSPACE_ROOT
  TELEGRAM_BOT_TOKENS
)

for var_name in "${required_vars[@]}"; do
  if [[ -z "${!var_name:-}" ]]; then
    echo "Error: $var_name must be set in $ENV_FILE." >&2
    echo "Post-installation checklist:"
    echo "1. Edit $ENV_FILE"
    echo "2. Set WORKSPACE_ROOT to the parent folder containing your projects"
    echo "3. Set TELEGRAM_BOT_TOKENS to one or more bot tokens"
    echo "4. Set ALLOWED_CHAT_IDS to your Telegram chat id(s)"
    echo "5. Run: ./startup.sh"
    exit 1
  fi
done

if [[ -z "${ALLOWED_CHAT_IDS:-}" ]]; then
  echo "Error: set ALLOWED_CHAT_IDS in $ENV_FILE." >&2
  echo "Run: ./startup.sh after updating $ENV_FILE."
  exit 1
fi

DEFAULT_AGENT_PROVIDER="${DEFAULT_AGENT_PROVIDER:-codex}"
CODEX_BIN="${CODEX_BIN:-codex}"
COPILOT_BIN="${COPILOT_BIN:-copilot}"

case "$DEFAULT_AGENT_PROVIDER" in
  codex)
    if ! command -v "$CODEX_BIN" >/dev/null 2>&1; then
      echo "Error: Codex CLI not found: $CODEX_BIN" >&2
      echo "Check DEFAULT_AGENT_PROVIDER and CODEX_BIN in $ENV_FILE." >&2
      echo "If this machine only has Copilot, set DEFAULT_AGENT_PROVIDER=copilot." >&2
      exit 1
    fi
    ;;
  copilot)
    if ! command -v "$COPILOT_BIN" >/dev/null 2>&1; then
      echo "Error: Copilot CLI not found: $COPILOT_BIN" >&2
      echo "Check DEFAULT_AGENT_PROVIDER and COPILOT_BIN in $ENV_FILE." >&2
      echo "If this machine only has Codex, set DEFAULT_AGENT_PROVIDER=codex." >&2
      exit 1
    fi
    ;;
  *)
    echo "Error: DEFAULT_AGENT_PROVIDER must be codex or copilot." >&2
    exit 1
    ;;
esac

echo "Post-installation guide:"
echo "1. Confirm $ENV_FILE contains WORKSPACE_ROOT, TELEGRAM_BOT_TOKENS, and ALLOWED_CHAT_IDS."
echo "2. State files are ready at $STATE_FILE and $STATE_BACKUP_FILE."
echo "3. Application logs will be written under $LOG_DIR."
echo "4. Optional voice-to-text: run ./install-stt.sh if you want local Whisper support."
echo "5. Start the server with: ./startup.sh"
echo "6. In Telegram, start conversations."
echo "Starting coding-agent-telegram..."
export CODING_AGENT_TELEGRAM_STT_INSTALL_HINT="./install-stt.sh"
exec python -m coding_agent_telegram
