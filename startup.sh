#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

resolve_path() {
  local value="$1"
  if [[ "$value" = /* ]]; then
    printf '%s\n' "$value"
  else
    printf '%s/%s\n' "$SCRIPT_DIR" "$value"
  fi
}

ENV_FILE="${ENV_FILE:-.env}"
ENV_TEMPLATE_FILE="${ENV_TEMPLATE_FILE:-src/coding_agent_telegram/resources/.env.example}"
VENV_DIR="${VENV_DIR:-.venv}"
PYTHON_BIN="${PYTHON_BIN:-python3}"
STATE_FILE_DEFAULT="./state.json"
STATE_BACKUP_FILE_DEFAULT="./state.json.bak"
LOG_DIR_DEFAULT="./logs"
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

if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
  echo "Error: $PYTHON_BIN was not found in PATH." >&2
  exit 1
fi

if [[ ! -f "$ENV_FILE" ]]; then
  if [[ -f "$ENV_TEMPLATE_FILE" ]]; then
    cp "$ENV_TEMPLATE_FILE" "$ENV_FILE"
    echo "Created $ENV_FILE from $ENV_TEMPLATE_FILE."
  else
    echo "Error: $ENV_FILE is missing and $ENV_TEMPLATE_FILE was not found." >&2
    exit 1
  fi
fi

set -a
source "$ENV_FILE"
set +a

STATE_FILE="${STATE_FILE:-$STATE_FILE_DEFAULT}"
STATE_BACKUP_FILE="${STATE_BACKUP_FILE:-$STATE_BACKUP_FILE_DEFAULT}"
LOG_DIR="${LOG_DIR:-$LOG_DIR_DEFAULT}"
STATE_FILE="$(resolve_path "$STATE_FILE")"
STATE_BACKUP_FILE="$(resolve_path "$STATE_BACKUP_FILE")"
LOG_DIR="$(resolve_path "$LOG_DIR")"
LOG_FILE="$LOG_DIR/coding-agent-telegram.log"

mkdir -p "$(dirname "$STATE_FILE")" "$(dirname "$STATE_BACKUP_FILE")" "$LOG_DIR"
touch "$STATE_FILE" "$STATE_BACKUP_FILE"

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
      exit 1
    fi
    ;;
  copilot)
    if ! command -v "$COPILOT_BIN" >/dev/null 2>&1; then
      echo "Error: Copilot CLI not found: $COPILOT_BIN" >&2
      exit 1
    fi
    ;;
  *)
    echo "Error: DEFAULT_AGENT_PROVIDER must be codex or copilot." >&2
    exit 1
    ;;
esac

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

echo "Post-installation guide:"
echo "1. Confirm $ENV_FILE contains WORKSPACE_ROOT, TELEGRAM_BOT_TOKENS, and ALLOWED_CHAT_IDS."
echo "2. State files are ready at $STATE_FILE and $STATE_BACKUP_FILE."
echo "3. Application logs will be written under $LOG_DIR."
echo "4. Start the server with: ./startup.sh"
echo "5. In Telegram, use /project <folder> and then /new <session_name> [provider]."
echo "Starting coding-agent-telegram..."
exec python -m coding_agent_telegram
