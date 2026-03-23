import logging
import sys
from pathlib import Path


def setup_logging(level: str, log_dir: Path) -> Path:
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "coding-agent-telegram.log"
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
        force=True,
    )
    for logger_name in ("httpx", "httpcore", "telegram", "telegram.ext.ExtBot"):
        logging.getLogger(logger_name).setLevel(logging.WARNING)
    return log_file
