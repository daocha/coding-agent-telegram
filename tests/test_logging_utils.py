"""Tests for logging_utils.setup_logging."""
from __future__ import annotations

import logging
from pathlib import Path


def test_setup_logging_creates_log_file(tmp_path: Path):
    from coding_agent_telegram.logging_utils import setup_logging

    log_file = setup_logging("INFO", tmp_path / "logs")

    assert log_file.exists()
    assert log_file.name == "coding-agent-telegram.log"


def test_setup_logging_adds_stream_and_file_handlers(tmp_path: Path):
    from coding_agent_telegram.logging_utils import setup_logging

    setup_logging("DEBUG", tmp_path / "logs")

    root = logging.getLogger()
    handler_types = {type(h).__name__ for h in root.handlers}
    assert "StreamHandler" in handler_types
    assert "RotatingFileHandler" in handler_types


def test_setup_logging_removes_existing_handlers_before_adding_new_ones(tmp_path: Path):
    from coding_agent_telegram.logging_utils import setup_logging

    # Add a stale handler manually
    stale = logging.StreamHandler()
    logging.getLogger().addHandler(stale)

    setup_logging("INFO", tmp_path / "logs")

    root = logging.getLogger()
    assert stale not in root.handlers
    # Exactly 2 handlers (StreamHandler + RotatingFileHandler)
    assert len(root.handlers) == 2


def test_setup_logging_sets_root_level_correctly(tmp_path: Path):
    from coding_agent_telegram.logging_utils import setup_logging

    setup_logging("WARNING", tmp_path / "logs")

    assert logging.getLogger().level == logging.WARNING


def test_setup_logging_suppresses_noisy_third_party_loggers(tmp_path: Path):
    from coding_agent_telegram.logging_utils import setup_logging

    setup_logging("DEBUG", tmp_path / "logs")

    for name in ("httpx", "httpcore", "telegram"):
        assert logging.getLogger(name).level == logging.WARNING


def test_setup_logging_writes_to_file(tmp_path: Path):
    from coding_agent_telegram.logging_utils import setup_logging

    log_file = setup_logging("INFO", tmp_path / "logs")
    logging.getLogger("test.write_check").info("hello from test")

    content = log_file.read_text(encoding="utf-8")
    assert "hello from test" in content
