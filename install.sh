#!/usr/bin/env bash

set -euo pipefail

APP_HOME_DIR="${HOME}/.coding-agent-telegram"
VENV_DIR="${VENV_DIR:-$APP_HOME_DIR/.venv}"
PYTHON_BIN="${PYTHON_BIN:-python3}"
PACKAGE_SPEC="${PACKAGE_SPEC:-coding-agent-telegram}"

if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
  echo "Error: $PYTHON_BIN was not found in PATH." >&2
  exit 1
fi

mkdir -p "$APP_HOME_DIR"

if [[ ! -d "$VENV_DIR" ]]; then
  "$PYTHON_BIN" -m venv "$VENV_DIR"
fi

source "$VENV_DIR/bin/activate"

python -m pip install --upgrade pip >/dev/null
python -m pip install --upgrade "$PACKAGE_SPEC"

echo "Installed $PACKAGE_SPEC into $VENV_DIR."
echo "Starting coding-agent-telegram..."
exec "$VENV_DIR/bin/coding-agent-telegram"
