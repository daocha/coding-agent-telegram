from __future__ import annotations

"""Keep the installed console command alive across Telegram/network failures.

The repository's ``startup.sh`` has an equivalent shell supervisor.  Installed
users do not have that script, so the public console entry point uses this
portable implementation instead.  The polling child remains in ``cli.py``;
keeping it separate means a restart always creates a fresh asyncio loop and
Telegram HTTP client.
"""

import os
import signal
import socket
import subprocess
import sys
import time
from pathlib import Path
from typing import NoReturn, Sequence

from coding_agent_telegram.config import default_app_internal_root


MIN_BACKOFF_SECONDS = 5.0
MAX_BACKOFF_SECONDS = 300.0
HEALTHY_RUN_SECONDS = 60.0
HEARTBEAT_MAX_AGE_SECONDS = 300.0
WATCHDOG_CHECK_SECONDS = 30.0
DNS_MAX_ATTEMPTS = 60
DNS_RETRY_SECONDS = 5.0
CHILD_PID_FILE_NAME = "coding-agent-telegram.child.pid"
CHILD_COMMAND_MARKER = "coding_agent_telegram"
CHILD_PID_FILE_ENV = "CODING_AGENT_TELEGRAM_CHILD_PID_FILE"


def _log(message: str) -> None:
    print(f"{time.strftime('%Y-%m-%d %H:%M:%S')} SUPERVISOR: {message}", flush=True)


def _heartbeat_path() -> Path:
    # cli.py obtains the same location from the loaded AppConfig.  No dotenv
    # parsing is needed before the child has validated its configuration.
    return default_app_internal_root() / "polling.heartbeat"


def _child_pid_path() -> Path:
    configured_path = os.getenv(CHILD_PID_FILE_ENV, "").strip()
    if configured_path:
        return Path(configured_path).expanduser()
    return default_app_internal_root() / CHILD_PID_FILE_NAME


def _write_child_pid(pid_path: Path, pid: int) -> None:
    pid_path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = pid_path.with_suffix(pid_path.suffix + ".tmp")
    temporary_path.write_text(f"{pid}\n", encoding="utf-8")
    temporary_path.replace(pid_path)


def _remove_child_pid(pid_path: Path) -> None:
    pid_path.unlink(missing_ok=True)


def _process_command(pid: int) -> str | None:
    """Return a process command line when the platform exposes one."""
    try:
        result = subprocess.run(
            ["ps", "-p", str(pid), "-o", "command="],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
        )
    except OSError:
        return None
    return result.stdout.strip() if result.returncode == 0 else None


def _stop_orphaned_child(pid_path: Path) -> None:
    """Stop a bot left behind by a force-killed supervisor.

    The command check prevents a stale, reused PID from terminating an
    unrelated process. It also recognizes the previous startup.sh child
    command, so migration does not create a temporary 409 polling conflict.
    """
    try:
        pid = int(pid_path.read_text(encoding="utf-8").strip())
    except (OSError, ValueError):
        _remove_child_pid(pid_path)
        return

    try:
        os.kill(pid, 0)
    except OSError:
        _remove_child_pid(pid_path)
        return

    command = _process_command(pid)
    if command is None or CHILD_COMMAND_MARKER not in command:
        _log(f"stale child pid file refers to pid {pid}, but it is not a bot process; leaving it alone.")
        _remove_child_pid(pid_path)
        return

    _log(f"found an orphaned bot process (pid {pid}) -- stopping it first.")
    try:
        os.kill(pid, signal.SIGTERM)
    except OSError:
        pass
    for _ in range(20):
        try:
            os.kill(pid, 0)
        except OSError:
            break
        time.sleep(1)
    else:
        _log(f"orphaned bot (pid {pid}) did not exit after 20s, sending SIGKILL")
        try:
            os.kill(pid, signal.SIGKILL)
        except OSError:
            pass
    _remove_child_pid(pid_path)


def _wait_for_dns() -> None:
    for attempt in range(DNS_MAX_ATTEMPTS):
        try:
            socket.getaddrinfo("api.telegram.org", 443)
            if attempt:
                _log(f"DNS is back after {attempt * DNS_RETRY_SECONDS:.0f}s.")
            return
        except OSError:
            if attempt == 0:
                _log("waiting for DNS...")
            time.sleep(DNS_RETRY_SECONDS)
    _log(f"DNS still down after {DNS_MAX_ATTEMPTS * DNS_RETRY_SECONDS:.0f}s -- starting anyway.")


def _stop_child(child: subprocess.Popen[object]) -> None:
    if child.poll() is not None:
        return
    child.terminate()
    try:
        child.wait(timeout=20)
    except subprocess.TimeoutExpired:
        _log(f"bot (pid {child.pid}) did not exit after 20s, sending SIGKILL")
        child.kill()
        child.wait()


def _run_supervisor(argv: Sequence[str]) -> int:
    # The only public one-shot command must not start a long-lived supervisor.
    if argv and argv[0] == "claude-auth":
        from coding_agent_telegram.cli import main as cli_main

        original_argv = sys.argv
        try:
            sys.argv = [original_argv[0], *argv]
            cli_main()
        finally:
            sys.argv = original_argv
        return 0

    heartbeat_file = _heartbeat_path()
    child_pid_file = _child_pid_path()
    stopping = False
    child: subprocess.Popen[object] | None = None

    def stop_requested(_signum: int, _frame: object) -> None:
        nonlocal stopping
        stopping = True
        if child is not None:
            _log(f"stop requested, forwarding SIGTERM to bot (pid {child.pid})")
            _stop_child(child)

    previous_term = signal.signal(signal.SIGTERM, stop_requested)
    previous_int = signal.signal(signal.SIGINT, stop_requested)
    try:
        _stop_orphaned_child(child_pid_file)
        backoff = MIN_BACKOFF_SECONDS
        while not stopping:
            _wait_for_dns()
            if stopping:
                break

            # A previous child's heartbeat is stale by definition.
            heartbeat_file.unlink(missing_ok=True)
            child = subprocess.Popen([sys.executable, "-m", "coding_agent_telegram.cli", *argv])
            _write_child_pid(child_pid_file, child.pid)
            _log(f"bot started (pid {child.pid}).")
            started_at = time.monotonic()

            while child.poll() is None and not stopping:
                time.sleep(WATCHDOG_CHECK_SECONDS)
                if heartbeat_file.exists():
                    age = time.time() - heartbeat_file.stat().st_mtime
                    if age > HEARTBEAT_MAX_AGE_SECONDS:
                        _log(f"no heartbeat for {age:.0f}s -- bot (pid {child.pid}) looks wedged, restarting it.")
                        _stop_child(child)
                        break

            if stopping:
                break
            status = child.wait()
            _remove_child_pid(child_pid_file)
            ran_for = time.monotonic() - started_at
            if ran_for >= HEALTHY_RUN_SECONDS:
                backoff = MIN_BACKOFF_SECONDS
            _log(f"bot exited (status {status}) after {ran_for:.0f}s -- restarting in {backoff:.0f}s.")
            time.sleep(backoff)
            backoff = min(backoff * 2, MAX_BACKOFF_SECONDS)
    finally:
        if child is not None:
            _stop_child(child)
        _remove_child_pid(child_pid_file)
        signal.signal(signal.SIGTERM, previous_term)
        signal.signal(signal.SIGINT, previous_int)
    _log("supervisor exiting")
    return 0


def main() -> NoReturn:
    raise SystemExit(_run_supervisor(sys.argv[1:]))


if __name__ == "__main__":
    main()
