#!/usr/bin/env bash

set -euo pipefail

PYTHON_BIN="${PYTHON_BIN:-python3}"
PACKAGE_SPEC="${PACKAGE_SPEC:-coding-agent-telegram}"

if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
  echo "Error: $PYTHON_BIN was not found in PATH." >&2
  exit 1
fi

"$PYTHON_BIN" -m pip install --upgrade "$PACKAGE_SPEC"
SCRIPT_DIR="$("$PYTHON_BIN" - <<'PY'
import sysconfig
print(sysconfig.get_path("scripts"))
PY
)"
COMMAND_PATH="$(command -v coding-agent-telegram || true)"
echo "Installed $PACKAGE_SPEC using $PYTHON_BIN."
if [[ -n "$COMMAND_PATH" ]]; then
  echo "Command path: $COMMAND_PATH"
else
  echo "Command path: $SCRIPT_DIR/coding-agent-telegram"
fi
if [[ -z "$COMMAND_PATH" && ":$PATH:" != *":$SCRIPT_DIR:"* ]]; then
  echo "Note: $SCRIPT_DIR is not currently on PATH."
fi

echo "Starting coding-agent-telegram..."
if [[ -n "$COMMAND_PATH" ]]; then
  exec "$COMMAND_PATH"
fi
exec "$PYTHON_BIN" -m coding_agent_telegram
