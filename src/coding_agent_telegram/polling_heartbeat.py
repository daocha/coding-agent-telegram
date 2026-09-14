from __future__ import annotations

"""Writes a heartbeat file that an external supervisor watches.

python-telegram-bot retries network errors indefinitely on its own (see
``telegram.ext._utils.networkloop``), but only for errors it actually sees
raised inside a still-running event loop -- it has no way to notice the loop
itself wedging (observed in production: the process stayed alive with
established TCP sockets to Telegram, but never issued another request for
12+ hours). Since the process never exits, a restart-on-crash supervisor
never triggers either.

This module only records liveness; it makes no decision about staleness or
restarting. That decision belongs to ``startup.sh``, which runs this process
as a child, watches this file's mtime, and restarts the child (after waiting
for DNS to actually work again) if it goes stale.
"""

from pathlib import Path


def touch_heartbeat(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    tmp_path.write_text("", encoding="utf-8")
    tmp_path.replace(path)
