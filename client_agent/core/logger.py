from __future__ import annotations

import logging
import os
import sys
from logging.handlers import RotatingFileHandler

from config import (
    LOG_BACKUP_COUNT,
    LOG_FILE,
    LOG_MAX_BYTES,
)


class SafeRotatingFileHandler(RotatingFileHandler):
    """
    RotatingFileHandler with Windows file-sharing lock resiliency.
    On Windows, transient file-sharing locks during rollover raise PermissionError.
    This handler prevents agent termination and logs a diagnostic warning to stderr.
    """

    def doRollover(self) -> None:
        try:
            super().doRollover()
        except (PermissionError, OSError) as exc:
            # Do not crash the application if rollover is temporarily blocked on Windows
            sys.stderr.write(f"SLMS Logger: Warning: Log rotation delayed ({exc})\n")


def create_rotating_handler(
    log_file: str = LOG_FILE,
    max_bytes: int = LOG_MAX_BYTES,
    backup_count: int = LOG_BACKUP_COUNT,
) -> SafeRotatingFileHandler:
    """Create and return a configured SafeRotatingFileHandler."""
    log_dir = os.path.dirname(os.path.abspath(log_file))
    if log_dir:
        os.makedirs(log_dir, exist_ok=True)

    handler = SafeRotatingFileHandler(
        log_file,
        mode="a",
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding="utf-8",
    )
    formatter = logging.Formatter("%(asctime)s | %(levelname)s | %(message)s")
    handler.setFormatter(formatter)
    return handler


logger = logging.getLogger("SLMS")

if not logger.handlers:
    logger.setLevel(logging.INFO)
    logger.addHandler(create_rotating_handler())