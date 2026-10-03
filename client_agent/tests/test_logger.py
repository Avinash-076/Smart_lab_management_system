"""
Automated tests for SLMS Client Agent logger subsystem.
Verifies:
- Logger initialization, name, and level
- SafeRotatingFileHandler configuration and log file creation
- Formatting: %(asctime)s | %(levelname)s | %(message)s
- Rotation threshold triggers rollover
- Safe rollover error handling (no crash on transient Windows file lock)
"""

import logging
import os
from logging.handlers import RotatingFileHandler
from unittest.mock import patch

from core.logger import SafeRotatingFileHandler, create_rotating_handler, logger


def test_logger_creation_and_level():
    """Verify primary logger is configured with SLMS name and INFO level."""
    assert logger.name == "SLMS"
    assert logger.level <= logging.INFO
    assert len(logger.handlers) >= 1
    assert any(isinstance(h, SafeRotatingFileHandler) for h in logger.handlers)


def test_logger_file_output_and_format(tmp_path):
    """Verify log output format adheres to '%(asctime)s | %(levelname)s | %(message)s'."""
    test_log = str(tmp_path / "test_format.log")
    handler = create_rotating_handler(log_file=test_log, max_bytes=10000, backup_count=2)
    test_logger = logging.getLogger("SLMS_Test_Format")
    test_logger.setLevel(logging.INFO)
    test_logger.addHandler(handler)

    try:
        test_logger.info("Test message for formatting verification")
        handler.flush()

        assert os.path.exists(test_log)
        with open(test_log, "r", encoding="utf-8") as f:
            content = f.read()

        assert " | INFO | Test message for formatting verification" in content
        # Verify timestamp is separated by pipe
        parts = content.strip().split(" | ")
        assert len(parts) == 3
        assert parts[1] == "INFO"
        assert parts[2] == "Test message for formatting verification"
    finally:
        handler.close()
        test_logger.removeHandler(handler)


def test_logger_rotation_behavior(tmp_path):
    """Verify log file rotates when exceeding max_bytes."""
    test_log = str(tmp_path / "test_rot.log")
    handler = create_rotating_handler(log_file=test_log, max_bytes=200, backup_count=2)
    test_logger = logging.getLogger("SLMS_Test_Rot")
    test_logger.setLevel(logging.INFO)
    test_logger.addHandler(handler)

    try:
        for i in range(20):
            test_logger.info(f"Entry index {i:03d} - padding to exceed maxBytes")
        handler.flush()

        assert os.path.exists(test_log)
        assert os.path.exists(f"{test_log}.1")
    finally:
        handler.close()
        test_logger.removeHandler(handler)


def test_safe_rotating_handler_survives_rollover_permission_error(tmp_path, capsys):
    """Verify that PermissionError during rollover does not terminate process."""
    test_log = str(tmp_path / "locked.log")
    handler = create_rotating_handler(log_file=test_log, max_bytes=100, backup_count=2)

    with patch.object(RotatingFileHandler, "doRollover", side_effect=PermissionError("File locked by AV")):
        # Must not raise PermissionError
        handler.doRollover()

    captured = capsys.readouterr()
    assert "Log rotation delayed" in captured.err
    handler.close()