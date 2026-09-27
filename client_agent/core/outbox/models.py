"""
Data models and enumerations for the durable outbox subsystem.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, IntEnum
from typing import Any


class OutboxStatus(str, Enum):
    """Lifecycle status of an outbox record."""
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    DEAD_LETTER = "DEAD_LETTER"


class OutboxPriority(IntEnum):
    """
    Priority levels for outbox queuing and backpressure eviction.
    Lower numerical values represent higher priority (retained during saturation).
    """
    COMMAND = 1      # Remote command execution results (must never be dropped)
    ISSUE = 2        # Auto-detected issues / alerts (critical system alerts)
    USAGE = 3        # Application usage sessions
    TELEMETRY = 10   # High-frequency metrics, process snapshot, software inventory


@dataclass
class OutboxRecord:
    """Represents a single persistent item in the local outbox queue."""
    id: int
    event_type: str
    payload: dict[str, Any]
    idempotency_key: str
    priority: int
    status: OutboxStatus
    attempt_count: int
    max_attempts: int
    next_attempt_at: float
    created_at: float
    updated_at: float
    last_error: str | None
    payload_size: int
