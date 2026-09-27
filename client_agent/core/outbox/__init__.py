"""
SLMS Client Agent Durable Outbox Subsystem.

Provides persistent, crash-safe, bounded, and idempotent local delivery
for metrics, software, processes, application usage, issues, and command results.
"""

from core.outbox.models import (
    OutboxPriority,
    OutboxRecord,
    OutboxStatus,
)
from core.outbox.policy import (
    DEFAULT_MAX_ATTEMPTS_CRITICAL,
    DEFAULT_MAX_ATTEMPTS_TELEMETRY,
    INITIAL_RETRY_DELAY,
    MAX_OUTBOX_BYTES,
    MAX_OUTBOX_RECORDS,
    MAX_RETRY_DELAY,
    ErrorClassification,
    calculate_backoff_delay,
    classify_exception,
    classify_http_status,
)
from core.outbox.storage import (
    DurableOutbox,
    QueueFullError,
)
from core.outbox.worker import OutboxDeliveryWorker

__all__ = [
    "DurableOutbox",
    "OutboxDeliveryWorker",
    "OutboxRecord",
    "OutboxStatus",
    "OutboxPriority",
    "QueueFullError",
    "ErrorClassification",
    "calculate_backoff_delay",
    "classify_exception",
    "classify_http_status",
    "INITIAL_RETRY_DELAY",
    "MAX_RETRY_DELAY",
    "MAX_OUTBOX_RECORDS",
    "MAX_OUTBOX_BYTES",
    "DEFAULT_MAX_ATTEMPTS_TELEMETRY",
    "DEFAULT_MAX_ATTEMPTS_CRITICAL",
]
