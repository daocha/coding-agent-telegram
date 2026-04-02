#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

PYTHON_BIN="${PYTHON_BIN:-python3}"
VENV_DIR="${VENV_DIR:-.venv}"
ENV_FILE="${ENV_FILE:-}"
LOCAL_PRETEND_VERSION="${SETUPTOOLS_SCM_PRETEND_VERSION_FOR_CODING_AGENT_TELEGRAM:-0.0.dev0}"

if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
  echo "Error: $PYTHON_BIN was not found in PATH." >&2
  exit 1
fi

if [[ ! -d "$VENV_DIR" ]]; then
  "$PYTHON_BIN" -m venv "$VENV_DIR"
fi

source "$VENV_DIR/bin/activate"
python -m pip install --upgrade pip >/dev/null

if ! python -c "import coding_agent_telegram" >/dev/null 2>&1; then
  echo "Installing local package into $VENV_DIR so the shared STT installer is available."
  SETUPTOOLS_SCM_PRETEND_VERSION_FOR_CODING_AGENT_TELEGRAM="$LOCAL_PRETEND_VERSION" \
    python -m pip install -e .
fi

ARGS=("install")
if [[ -n "$ENV_FILE" ]]; then
  ARGS+=("--env-file" "$ENV_FILE")
fi
ARGS+=("--python-bin" "$(command -v python)")

exec python -m coding_agent_telegram.stt_setup "${ARGS[@]}"
