#!/bin/bash
# Entry point: run this to start the bot(s). One-time environment setup
# (venv, deps, .env validation) lives in bootstrap.sh, run once below; this
# script then supervises the actual bot process, keeping it alive across
# crashes and network outages and recycling it if it hangs (see the
# heartbeat watchdog below). Launched by launchd (see the plist in
# ~/Library/LaunchAgents) but safe to run directly in the foreground too.
#
# Why the supervision exists: python-telegram-bot retries transient
# get_updates errors on its own, but it has no way to notice its own event
# loop wedging (a connection stuck past its configured timeout that never
# actually fires). When that happens the process stays alive -- doing
# nothing -- and nothing then brings it back on its own. This loop restarts
# it, and waits for DNS to actually work again before each restart so the
# fresh process does not immediately die the same way.
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
APP_HOME_DIR="${HOME}/.coding-agent-telegram"
HEARTBEAT_FILE="$APP_HOME_DIR/polling.heartbeat"
CHILD_PID_FILE="$SCRIPT_DIR/coding-agent-telegram.child.pid"

# stt_setup.py reads this at runtime to point users at the installer if
# speech-to-text isn't set up yet. bootstrap.sh runs as a separate
# subprocess above, so its own `export` of this does not reach the bot
# process started by the loop below -- it has to be set here instead.
export CODING_AGENT_TELEGRAM_STT_INSTALL_HINT="./install-stt.sh"

# Restart pacing: quick after the first failure, backing off to
# MAX_BACKOFF while the network stays down, and reset once a run has
# survived long enough to count as healthy.
MIN_BACKOFF=5
MAX_BACKOFF=300
HEALTHY_RUN_SECONDS=60

# Watchdog: the app touches HEARTBEAT_FILE roughly every 60s (see
# cli.py's POLLING_HEARTBEAT_INTERVAL_SECONDS) for as long as polling is
# actually alive. If it stops moving while the process is still alive, the
# event loop is wedged -- polling is dead but nothing exits, which is the
# failure that leaves the bot silently offline. Five missed beats is well
# past any legitimate slow tick.
HEARTBEAT_MAX_AGE=300
WATCHDOG_CHECK_SECONDS=30

# DNS probe between restarts. 60 x 5s = 5 minutes, after which we start
# anyway and let the backoff loop handle it if it fails again.
DNS_MAX_ATTEMPTS=60
DNS_RETRY_SECONDS=5

child=""
sleeper=""
shutting_down=0

log() {
  echo "$(date '+%Y-%m-%d %H:%M:%S') SUPERVISOR: $*"
}

# launchd (or launchctl stop) sends SIGTERM here. Forward it to the bot's
# python child, wait for it to finish its own shutdown (PTB closes the
# polling session cleanly on SIGTERM), and exit *without* restarting --
# otherwise stopping the bot would be impossible.
terminate() {
  shutting_down=1
  [ -n "$sleeper" ] && kill "$sleeper" 2>/dev/null
  if [ -n "$child" ] && kill -0 "$child" 2>/dev/null; then
    log "stop requested, forwarding SIGTERM to bot (pid $child)"
    kill "$child" 2>/dev/null
    for _ in $(seq 1 20); do
      kill -0 "$child" 2>/dev/null || break
      sleep 1
    done
    if kill -0 "$child" 2>/dev/null; then
      log "bot (pid $child) did not exit after 20s, sending SIGKILL"
      kill -9 "$child" 2>/dev/null
    fi
  fi
  rm -f "$CHILD_PID_FILE"
  log "supervisor exiting"
  exit 0
}
trap terminate TERM INT

# Sleep that can still be interrupted by SIGTERM. Bash defers traps until the
# current foreground command returns, so a plain `sleep 300` would make a
# stop request hang for up to five minutes; `wait` is the one builtin a
# signal cuts short.
interruptible_sleep() {
  sleep "$1" &
  sleeper=$!
  wait "$sleeper" 2>/dev/null
  sleeper=""
}

# Wait for DNS, not just for IP reachability. Pinging 1.1.1.1 only proves
# packets get out; the bot immediately needs to *resolve* api.telegram.org,
# and this host has been observed with working routing but a stuck resolver.
# Resolving through the same interpreter the bot actually runs under tests
# exactly what it needs. Falls back to system python3 if the venv somehow
# doesn't exist (bootstrap.sh above already guarantees it does).
wait_for_dns() {
  local probe="$PYTHON"
  [ -x "$probe" ] || probe="python3"
  local attempt=0
  until "$probe" -c \
    'import socket; socket.getaddrinfo("api.telegram.org", 443)' >/dev/null 2>&1; do
    attempt=$((attempt + 1))
    if [ "$attempt" -ge "$DNS_MAX_ATTEMPTS" ]; then
      log "DNS still down after $((DNS_MAX_ATTEMPTS * DNS_RETRY_SECONDS))s -- starting anyway."
      return
    fi
    [ "$attempt" -eq 1 ] && log "waiting for DNS..."
    interruptible_sleep "$DNS_RETRY_SECONDS"
    [ "$shutting_down" -eq 1 ] && return
  done
  [ "$attempt" -gt 0 ] && log "DNS is back after $((attempt * DNS_RETRY_SECONDS))s."
  return 0
}

# Prints the seconds since the heartbeat file was last written; returns
# non-zero if there is no readable heartbeat yet, which callers treat as
# "no opinion" rather than "wedged".
heartbeat_age() {
  [ -f "$HEARTBEAT_FILE" ] || return 1
  local mtime
  mtime=$(date -r "$HEARTBEAT_FILE" +%s 2>/dev/null) || return 1
  echo $(( $(date +%s) - mtime ))
}

# A stale child pid file means a previous supervisor was SIGKILLed and left
# the bot behind. Two pollers sharing a token make Telegram return 409
# Conflict, so clear it out before starting a new one.
if [ -f "$CHILD_PID_FILE" ]; then
  stray="$(cat "$CHILD_PID_FILE" 2>/dev/null)"
  if [ -n "$stray" ] && kill -0 "$stray" 2>/dev/null; then
    log "found an orphaned bot process (pid $stray) -- stopping it first."
    kill "$stray" 2>/dev/null
    for _ in $(seq 1 20); do
      kill -0 "$stray" 2>/dev/null || break
      sleep 1
    done
    kill -0 "$stray" 2>/dev/null && kill -9 "$stray" 2>/dev/null
  fi
  rm -f "$CHILD_PID_FILE"
fi

backoff=$MIN_BACKOFF
while :; do
  wait_for_dns
  [ "$shutting_down" -eq 1 ] && exit 0

  # Drop the previous process's heartbeat: it is stale by definition, and
  # the new one only writes its first beat once every bot has connected.
  rm -f "$HEARTBEAT_FILE"
  "$PYTHON" -m coding_agent_telegram &
  child=$!
  echo "$child" > "$CHILD_PID_FILE"
  log "bot started (pid $child)."
  started=$(date +%s)

  # Watch the heartbeat while it runs. Plain `wait` would block until the
  # process exits, which never happens in the wedged case.
  while kill -0 "$child" 2>/dev/null; do
    interruptible_sleep "$WATCHDOG_CHECK_SECONDS"
    [ "$shutting_down" -eq 1 ] && exit 0
    age=$(heartbeat_age) || continue
    if [ "$age" -gt "$HEARTBEAT_MAX_AGE" ]; then
      log "no heartbeat for ${age}s -- bot (pid $child) looks wedged, restarting it."
      kill "$child" 2>/dev/null
      for _ in $(seq 1 20); do
        kill -0 "$child" 2>/dev/null || break
        sleep 1
      done
      kill -0 "$child" 2>/dev/null && kill -9 "$child" 2>/dev/null
      break
    fi
  done

  wait "$child" 2>/dev/null
  status=$?
  child=""
  rm -f "$CHILD_PID_FILE"
  [ "$shutting_down" -eq 1 ] && exit 0

  ran=$(( $(date +%s) - started ))
  if [ "$ran" -ge "$HEALTHY_RUN_SECONDS" ]; then
    backoff=$MIN_BACKOFF
  fi
  log "bot exited (status $status) after ${ran}s -- restarting in ${backoff}s."
  interruptible_sleep "$backoff"
  [ "$shutting_down" -eq 1 ] && exit 0
  # Back off while the failure keeps repeating, so a misconfiguration (bad
  # token, missing .env) settles into one retry every MAX_BACKOFF seconds
  # instead of filling the log at five-second intervals.
  backoff=$((backoff * 2))
  [ "$backoff" -gt "$MAX_BACKOFF" ] && backoff=$MAX_BACKOFF
done
