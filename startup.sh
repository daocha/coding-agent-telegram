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
VENV_DIR="${VENV_DIR:-.venv}"
PYTHON_BIN="${PYTHON_BIN:-python3}"
STATE_FILE_DEFAULT="./state.json"
STATE_BACKUP_FILE_DEFAULT="./state.json.bak"
LOG_DIR_DEFAULT="./logs"

if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
  echo "Error: $PYTHON_BIN was not found in PATH." >&2
  exit 1
fi

if [[ ! -f "$ENV_FILE" ]]; then
  if [[ -f ".env.example" ]]; then
    cp ".env.example" "$ENV_FILE"
    echo "Created $ENV_FILE from .env.example."
  else
    echo "Error: $ENV_FILE is missing and .env.example was not found." >&2
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
touch "$STATE_FILE" "$STATE_BACKUP_FILE" "$LOG_FILE"

exec >> "$LOG_FILE" 2>&1

echo "Logging output to $LOG_FILE"

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
python -m pip install -e .

echo "Post-installation guide:"
echo "1. Confirm $ENV_FILE contains WORKSPACE_ROOT, TELEGRAM_BOT_TOKENS, and ALLOWED_CHAT_IDS."
echo "2. State files are ready at $STATE_FILE and $STATE_BACKUP_FILE."
echo "3. Application logs will be written under $LOG_DIR."
echo "4. Start the server with: ./startup.sh"
echo "5. In Telegram, use /project <folder> and then /new <session_name> [provider]."
echo "Starting coding-agent-telegram..."
exec python -m coding_agent_telegram
