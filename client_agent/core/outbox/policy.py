"""
Retry and backpressure policies for the durable outbox subsystem.
"""

from __future__ import annotations

from enum import Enum
import random
from typing import Any

import requests


# Retry Timing Constants
INITIAL_RETRY_DELAY: float = 2.0     # Initial backoff in seconds
MAX_RETRY_DELAY: float = 300.0       # Maximum backoff cap (5 minutes)
BACKOFF_FACTOR: float = 2.0          # Exponential backoff multiplier
JITTER_RATIO: float = 0.2            # ±20% jitter range

# Default Attempt Limits
DEFAULT_MAX_ATTEMPTS_TELEMETRY: int = 5
DEFAULT_MAX_ATTEMPTS_CRITICAL: int = 10  # For commands, issues, usage

# Backpressure Queue Bounds
MAX_OUTBOX_RECORDS: int = 5000       # Maximum total pending/dead-letter rows
MAX_OUTBOX_BYTES: int = 20 * 1024 * 1024  # 20 megabytes max payload storage
DEAD_LETTER_RETENTION_SECONDS: float = 7 * 86400  # 7 days


class ErrorClassification(str, Enum):
    """Classification of delivery outcome to dictate state transition."""
    SUCCESS = "SUCCESS"
    IDEMPOTENT_DUPLICATE = "IDEMPOTENT_DUPLICATE"
    AUTH_EXPIRED = "AUTH_EXPIRED"
    PERMANENT_FAILURE = "PERMANENT_FAILURE"
    RETRYABLE_FAILURE = "RETRYABLE_FAILURE"


def calculate_backoff_delay(
    attempt_count: int,
    initial_delay: float = INITIAL_RETRY_DELAY,
    max_delay: float = MAX_RETRY_DELAY,
    factor: float = BACKOFF_FACTOR,
    jitter_ratio: float = JITTER_RATIO,
) -> float:
    """
    Calculate exponential backoff delay with bounded jitter.

    Formula:
        base_delay = min(initial_delay * (factor ** (attempt - 1)), max_delay)
        jitter = base_delay * jitter_ratio * uniform(-1, 1)
        final_delay = max(0.5, base_delay + jitter)
    """
    if attempt_count <= 0:
        return initial_delay

    base = min(initial_delay * (factor ** (attempt_count - 1)), max_delay)
    jitter = base * jitter_ratio * random.uniform(-1.0, 1.0)
    return max(0.5, round(base + jitter, 2))


def classify_http_status(status_code: int, response_text: str = "") -> ErrorClassification:
    """
    Classify an HTTP status code into an actionable delivery outcome.

    - 200..299: SUCCESS
    - 401: AUTH_EXPIRED (triggers token refresh and immediate retry)
    - 409: IDEMPOTENT_DUPLICATE (server already has this record, treat as delivered)
    - 400, 403, 404, 422: PERMANENT_FAILURE (dead-letter, do not retry indefinitely)
    - 429, 500..599: RETRYABLE_FAILURE (exponential backoff)
    """
    if 200 <= status_code < 300:
        return ErrorClassification.SUCCESS
    if status_code == 401:
        return ErrorClassification.AUTH_EXPIRED
    if status_code == 409:
        return ErrorClassification.IDEMPOTENT_DUPLICATE
    if status_code in (400, 403, 404, 422):
        return ErrorClassification.PERMANENT_FAILURE
    if status_code == 429 or 500 <= status_code < 600:
        return ErrorClassification.RETRYABLE_FAILURE
    if 400 <= status_code < 500:
        return ErrorClassification.PERMANENT_FAILURE
    return ErrorClassification.RETRYABLE_FAILURE


def classify_exception(exc: Exception) -> tuple[ErrorClassification, str]:
    """
    Inspect an exception raised during delivery and determine classification and description.
    """
    if isinstance(exc, requests.HTTPError):
        status_code = exc.response.status_code if exc.response is not None else 0
        resp_text = ""
        if exc.response is not None:
            try:
                resp_text = exc.response.text[:200]
            except Exception:
                pass
        classification = classify_http_status(status_code, resp_text)
        error_msg = f"HTTP {status_code}: {resp_text or str(exc)}"
        return classification, error_msg

    if isinstance(exc, (requests.ConnectionError, requests.Timeout)):
        return ErrorClassification.RETRYABLE_FAILURE, f"Network error: {exc}"

    return ErrorClassification.RETRYABLE_FAILURE, f"Delivery error: {exc}"
