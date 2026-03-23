#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

ENV_FILE="${ENV_FILE:-.env}"
VENV_DIR="${VENV_DIR:-.venv}"
PYTHON_BIN="${PYTHON_BIN:-python3}"

if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
  echo "Error: $PYTHON_BIN was not found in PATH." >&2
  exit 1
fi

if [[ ! -f "$ENV_FILE" ]]; then
  if [[ -f ".env.example" ]]; then
    cp ".env.example" "$ENV_FILE"
    echo "Created $ENV_FILE from .env.example."
    echo "Edit $ENV_FILE and set TELEGRAM_BOT_TOKENS plus ALLOWED_CHAT_IDS, then run this script again."
    exit 1
  fi

  echo "Error: $ENV_FILE is missing." >&2
  exit 1
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
    exit 1
  fi
done

if [[ -z "${ALLOWED_CHAT_IDS:-}" ]]; then
  echo "Error: set ALLOWED_CHAT_IDS in $ENV_FILE." >&2
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

echo "Starting coding-agent-telegram..."
exec python -m coding_agent_telegram
