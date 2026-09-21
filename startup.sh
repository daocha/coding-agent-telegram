#!/bin/bash
# Repository entry point. It prepares the checkout once, then replaces this
# shell with the same Python supervisor used by the installed console command.
# That supervisor owns crash recovery, DNS backoff, heartbeat watchdogs, and
# cleanup of an orphaned bot left by a forced kill.
set -u

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "$(date '+%Y-%m-%d %H:%M:%S') SUPERVISOR: running bootstrap.sh..."
./bootstrap.sh
bootstrap_status=$?
if [ "$bootstrap_status" -ne 0 ]; then
  echo "$(date '+%Y-%m-%d %H:%M:%S') SUPERVISOR: bootstrap.sh failed (status $bootstrap_status); not starting." >&2
  exit "$bootstrap_status"
fi

PYTHON="$SCRIPT_DIR/.venv/bin/python3"

# Preserve the checkout-specific STT setup hint. The installed command keeps
# its normal `coding-agent-telegram-stt-install` hint instead.
export CODING_AGENT_TELEGRAM_STT_INSTALL_HINT="./install-stt.sh"
# Keep the existing checkout-local location so an orphan from the former shell
# supervisor is recovered on the first run after upgrading.
export CODING_AGENT_TELEGRAM_CHILD_PID_FILE="$SCRIPT_DIR/coding-agent-telegram.child.pid"

exec "$PYTHON" -m coding_agent_telegram.supervisor "$@"
