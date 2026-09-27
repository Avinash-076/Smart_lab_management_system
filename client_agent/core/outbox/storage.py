"""
Durable local SQLite storage engine for the SLMS outbox subsystem.

Ensures reliable persistence across network outages, service restarts,
and system reboots using crash-safe SQLite transactions and WAL mode.
"""

from __future__ import annotations

import json
import os
import sqlite3
import threading
import time
from typing import Any
import uuid

from core.logger import logger
from core.outbox.models import OutboxPriority, OutboxRecord, OutboxStatus
from core.outbox.policy import (
    DEAD_LETTER_RETENTION_SECONDS,
    DEFAULT_MAX_ATTEMPTS_CRITICAL,
    DEFAULT_MAX_ATTEMPTS_TELEMETRY,
    MAX_OUTBOX_BYTES,
    MAX_OUTBOX_RECORDS,
)
from paths import OUTBOX_DB_PATH


SCHEMA_VERSION = 1


class QueueFullError(Exception):
    """Raised when the outbox is saturated and backpressure cannot free space."""
    pass


class DurableOutbox:
    """
    Manages persistent queuing of outgoing telemetry, issues, usage, and commands.
    Thread-safe and crash-resilient via SQLite transactions and WAL journal mode.
    """

    def __init__(
        self,
        db_path: str = OUTBOX_DB_PATH,
        max_records: int = MAX_OUTBOX_RECORDS,
        max_bytes: int = MAX_OUTBOX_BYTES,
        wake_event: threading.Event | None = None,
    ):
        self.db_path = db_path
        self.max_records = max_records
        self.max_bytes = max_bytes
        self.wake_event = wake_event
        self._lock = threading.RLock()

        # Ensure target folder exists
        os.makedirs(os.path.dirname(os.path.abspath(self.db_path)), exist_ok=True)
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        """Create and configure a SQLite connection with WAL mode and busy timeout."""
        conn = sqlite3.connect(
            self.db_path,
            timeout=10.0,
            check_same_thread=False,
        )
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode = WAL;")
        conn.execute("PRAGMA busy_timeout = 5000;")
        conn.execute("PRAGMA synchronous = NORMAL;")
        return conn

    def _init_db(self) -> None:
        """Initialize schema and run migrations if necessary."""
        with self._lock:
            with self._get_connection() as conn:
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS outbox_schema_version (
                        version INTEGER PRIMARY KEY,
                        applied_at REAL NOT NULL
                    );
                    """
                )
                cur = conn.execute("SELECT MAX(version) FROM outbox_schema_version;")
                row = cur.fetchone()
                current_version = row[0] if (row and row[0] is not None) else 0

                if current_version < 1:
                    conn.execute(
                        """
                        CREATE TABLE IF NOT EXISTS outbox_items (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            event_type TEXT NOT NULL,
                            payload TEXT NOT NULL,
                            idempotency_key TEXT NOT NULL UNIQUE,
                            priority INTEGER NOT NULL DEFAULT 10,
                            status TEXT NOT NULL DEFAULT 'PENDING',
                            attempt_count INTEGER NOT NULL DEFAULT 0,
                            max_attempts INTEGER NOT NULL DEFAULT 5,
                            next_attempt_at REAL NOT NULL,
                            created_at REAL NOT NULL,
                            updated_at REAL NOT NULL,
                            last_error TEXT,
                            payload_size INTEGER NOT NULL
                        );
                        """
                    )
                    conn.execute(
                        """
                        CREATE INDEX IF NOT EXISTS ix_outbox_items_pending
                        ON outbox_items (status, next_attempt_at, priority, created_at);
                        """
                    )
                    conn.execute(
                        """
                        CREATE INDEX IF NOT EXISTS ix_outbox_items_idempotency
                        ON outbox_items (idempotency_key);
                        """
                    )
                    conn.execute(
                        """
                        CREATE INDEX IF NOT EXISTS ix_outbox_items_event_type
                        ON outbox_items (event_type);
                        """
                    )
                    conn.execute(
                        "INSERT INTO outbox_schema_version (version, applied_at) VALUES (?, ?);",
                        (1, time.time()),
                    )
                    conn.commit()

    def enqueue(
        self,
        event_type: str,
        payload: dict[str, Any],
        idempotency_key: str | None = None,
        priority: int = OutboxPriority.TELEMETRY,
        max_attempts: int | None = None,
    ) -> OutboxRecord:
        """
        Atomically enqueue a payload with an idempotency key.
        If a record with the same idempotency key already exists and is active,
        returns the existing record (preventing duplicate enqueue).
        """
        if not idempotency_key:
            idempotency_key = f"{event_type}_{uuid.uuid4().hex}"

        if max_attempts is None:
            max_attempts = (
                DEFAULT_MAX_ATTEMPTS_CRITICAL
                if priority <= OutboxPriority.USAGE
                else DEFAULT_MAX_ATTEMPTS_TELEMETRY
            )

        payload_json = json.dumps(payload, default=str)
        payload_size = len(payload_json.encode("utf-8"))
        now = time.time()

        with self._lock:
            with self._get_connection() as conn:
                # Idempotency check: see if record already exists
                cur = conn.execute(
                    "SELECT * FROM outbox_items WHERE idempotency_key = ?;",
                    (idempotency_key,),
                )
                row = cur.fetchone()
                if row:
                    record = self._row_to_record(row)
                    logger.debug(
                        f"Outbox idempotency hit for key '{idempotency_key}' (id={record.id})"
                    )
                    return record

                # Enforce backpressure bounds
                self._enforce_backpressure(conn, payload_size, priority)

                # Insert new outbox record
                cur = conn.execute(
                    """
                    INSERT INTO outbox_items (
                        event_type, payload, idempotency_key, priority, status,
                        attempt_count, max_attempts, next_attempt_at, created_at,
                        updated_at, last_error, payload_size
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                    """,
                    (
                        event_type,
                        payload_json,
                        idempotency_key,
                        int(priority),
                        OutboxStatus.PENDING.value,
                        0,
                        max_attempts,
                        now,
                        now,
                        now,
                        None,
                        payload_size,
                    ),
                )
                record_id = cur.lastrowid
                conn.commit()

        if self.wake_event:
            self.wake_event.set()

        return OutboxRecord(
            id=record_id,
            event_type=event_type,
            payload=payload,
            idempotency_key=idempotency_key,
            priority=priority,
            status=OutboxStatus.PENDING,
            attempt_count=0,
            max_attempts=max_attempts,
            next_attempt_at=now,
            created_at=now,
            updated_at=now,
            last_error=None,
            payload_size=payload_size,
        )

    def get_record_by_idempotency_key(self, idempotency_key: str) -> OutboxRecord | None:
        """Find an outbox record by its idempotency key."""
        with self._lock:
            with self._get_connection() as conn:
                cur = conn.execute(
                    "SELECT * FROM outbox_items WHERE idempotency_key = ?;",
                    (idempotency_key,),
                )
                row = cur.fetchone()
                if row:
                    return self._row_to_record(row)
                return None

    def requeue_dead_letter(self, record_id: int) -> bool:
        """Re-activate a DEAD_LETTER record to PENDING status for re-delivery."""
        now = time.time()
        with self._lock:
            with self._get_connection() as conn:
                cur = conn.execute(
                    """
                    UPDATE outbox_items
                    SET status = ?, attempt_count = 0, next_attempt_at = ?,
                        updated_at = ?, last_error = NULL
                    WHERE id = ? AND status = ?;
                    """,
                    (OutboxStatus.PENDING.value, now, now, record_id, OutboxStatus.DEAD_LETTER.value),
                )
                conn.commit()
                requeued = cur.rowcount > 0

        if requeued and self.wake_event:
            self.wake_event.set()
        return requeued

    def get_pending_batch(
        self,
        limit: int = 20,
        now: float | None = None,
    ) -> list[OutboxRecord]:
        """
        Retrieve and atomically claim up to `limit` pending records due for attempt.
        Transition claimed items to PROCESSING status.
        """
        current_time = now if now is not None else time.time()
        records: list[OutboxRecord] = []

        with self._lock:
            with self._get_connection() as conn:
                cur = conn.execute(
                    """
                    SELECT * FROM outbox_items
                    WHERE status = ? AND next_attempt_at <= ?
                    ORDER BY priority ASC, created_at ASC
                    LIMIT ?;
                    """,
                    (OutboxStatus.PENDING.value, current_time, limit),
                )
                rows = cur.fetchall()
                if not rows:
                    return []

                ids = [row["id"] for row in rows]
                placeholders = ",".join("?" for _ in ids)
                conn.execute(
                    f"""
                    UPDATE outbox_items
                    SET status = ?, updated_at = ?
                    WHERE id IN ({placeholders});
                    """,
                    [OutboxStatus.PROCESSING.value, current_time] + ids,
                )
                conn.commit()

                for row in rows:
                    rec = self._row_to_record(row)
                    rec.status = OutboxStatus.PROCESSING
                    rec.updated_at = current_time
                    records.append(rec)

        return records

    def mark_delivered(self, record_id: int) -> None:
        """
        Mark a record successfully delivered by deleting it from SQLite.
        Immediate deletion upon delivery prevents storage bloat.
        """
        with self._lock:
            with self._get_connection() as conn:
                conn.execute(
                    "DELETE FROM outbox_items WHERE id = ?;",
                    (record_id,),
                )
                conn.commit()

    def mark_retry(
        self,
        record_id: int,
        error_message: str,
        next_attempt_at: float,
    ) -> None:
        """
        Schedule a record for retry after backoff delay.
        If attempt_count reaches max_attempts, moves record to DEAD_LETTER.
        """
        now = time.time()
        with self._lock:
            with self._get_connection() as conn:
                cur = conn.execute(
                    "SELECT attempt_count, max_attempts FROM outbox_items WHERE id = ?;",
                    (record_id,),
                )
                row = cur.fetchone()
                if not row:
                    return

                new_attempts = row["attempt_count"] + 1
                max_attempts = row["max_attempts"]

                if new_attempts >= max_attempts:
                    dead_msg = f"Max attempts ({max_attempts}) reached: {error_message}"
                    conn.execute(
                        """
                        UPDATE outbox_items
                        SET status = ?, attempt_count = ?, last_error = ?, updated_at = ?
                        WHERE id = ?;
                        """,
                        (OutboxStatus.DEAD_LETTER.value, new_attempts, dead_msg, now, record_id),
                    )
                    logger.warning(
                        f"Outbox record {record_id} reached max attempts and moved to DEAD_LETTER: {dead_msg}"
                    )
                else:
                    conn.execute(
                        """
                        UPDATE outbox_items
                        SET status = ?, attempt_count = ?, next_attempt_at = ?,
                            last_error = ?, updated_at = ?
                        WHERE id = ?;
                        """,
                        (OutboxStatus.PENDING.value, new_attempts, next_attempt_at, error_message, now, record_id),
                    )
                conn.commit()

    def mark_dead_letter(self, record_id: int, error_message: str) -> None:
        """Move a record directly to DEAD_LETTER (e.g. for non-retryable 4xx errors)."""
        now = time.time()
        with self._lock:
            with self._get_connection() as conn:
                conn.execute(
                    """
                    UPDATE outbox_items
                    SET status = ?, last_error = ?, updated_at = ?
                    WHERE id = ?;
                    """,
                    (OutboxStatus.DEAD_LETTER.value, error_message, now, record_id),
                )
                conn.commit()
                logger.warning(f"Outbox record {record_id} marked DEAD_LETTER: {error_message}")

    def recover_stale_processing(self, stale_threshold_seconds: float = 60.0) -> int:
        """
        Recover records that were stuck in PROCESSING status due to an ungraceful
        process termination or crash. Resets them to PENDING.
        """
        now = time.time()
        stale_cutoff = now - stale_threshold_seconds
        with self._lock:
            with self._get_connection() as conn:
                cur = conn.execute(
                    """
                    UPDATE outbox_items
                    SET status = ?, updated_at = ?
                    WHERE status = ? AND updated_at < ?;
                    """,
                    (OutboxStatus.PENDING.value, now, OutboxStatus.PROCESSING.value, stale_cutoff),
                )
                recovered = cur.rowcount
                conn.commit()
                if recovered > 0:
                    logger.info(f"Recovered {recovered} stale processing outbox records.")
                return recovered

    def _enforce_backpressure(
        self,
        conn: sqlite3.Connection,
        needed_bytes: int,
        priority: int,
    ) -> None:
        """
        Enforce bounded queue limits.

        Eviction Policy:
        1. Prune expired DEAD_LETTER records (> 7 days).
        2. If still saturated and new item is high priority, prune oldest PENDING
           telemetry records (priority >= TELEMETRY).
        3. If still saturated and new item is COMMAND or ISSUE, prune oldest USAGE records.
        4. CRITICAL INVARIANT: NEVER prune COMMAND_RESULT (priority=1) or ISSUE (priority=2).
        5. If still saturated and new item cannot be admitted, raise QueueFullError.
        """
        cur = conn.execute("SELECT COUNT(*), COALESCE(SUM(payload_size), 0) FROM outbox_items;")
        row = cur.fetchone()
        total_count = row[0]
        total_bytes = row[1]

        if total_count < self.max_records and (total_bytes + needed_bytes) <= self.max_bytes:
            return

        # 1. Purge expired dead-letter items
        cutoff = time.time() - DEAD_LETTER_RETENTION_SECONDS
        conn.execute(
            "DELETE FROM outbox_items WHERE status = ? AND created_at < ?;",
            (OutboxStatus.DEAD_LETTER.value, cutoff),
        )

        # Check again
        cur = conn.execute("SELECT COUNT(*), COALESCE(SUM(payload_size), 0) FROM outbox_items;")
        row = cur.fetchone()
        total_count, total_bytes = row[0], row[1]

        if total_count < self.max_records and (total_bytes + needed_bytes) <= self.max_bytes:
            return

        # 2. Prune oldest PENDING telemetry (priority >= TELEMETRY) if admitting any item
        # If admitting telemetry itself, we prune older telemetry to make room for newer telemetry.
        cur = conn.execute(
            """
            SELECT id, payload_size FROM outbox_items
            WHERE priority >= ? AND status != ?
            ORDER BY created_at ASC;
            """,
            (int(OutboxPriority.TELEMETRY), OutboxStatus.PROCESSING.value),
        )
        telemetry_rows = cur.fetchall()
        for trow in telemetry_rows:
            conn.execute("DELETE FROM outbox_items WHERE id = ?;", (trow["id"],))
            total_count -= 1
            total_bytes -= trow["payload_size"]
            if total_count < self.max_records and (total_bytes + needed_bytes) <= self.max_bytes:
                return

        # 3. If still saturated and incoming item is COMMAND (1) or ISSUE (2), prune USAGE (3)
        if priority <= OutboxPriority.ISSUE:
            cur = conn.execute(
                """
                SELECT id, payload_size FROM outbox_items
                WHERE priority = ? AND status != ?
                ORDER BY created_at ASC;
                """,
                (int(OutboxPriority.USAGE), OutboxStatus.PROCESSING.value),
            )
            usage_rows = cur.fetchall()
            for urow in usage_rows:
                conn.execute("DELETE FROM outbox_items WHERE id = ?;", (urow["id"],))
                total_count -= 1
                total_bytes -= urow["payload_size"]
                if total_count < self.max_records and (total_bytes + needed_bytes) <= self.max_bytes:
                    return

        # If saturated and cannot admit
        if total_count >= self.max_records or (total_bytes + needed_bytes) > self.max_bytes:
            if priority >= OutboxPriority.TELEMETRY:
                raise QueueFullError("Outbox queue is full. Telemetry record rejected by backpressure.")
            elif priority == OutboxPriority.USAGE:
                raise QueueFullError("Outbox queue is full. Usage record rejected by backpressure.")
            elif priority == OutboxPriority.ISSUE:
                raise QueueFullError("Outbox queue is full of critical records. Issue rejected by backpressure.")
            else:
                raise QueueFullError("Outbox queue is full of critical records. Command result rejected by backpressure.")

    def get_stats(self) -> dict[str, Any]:
        """Return summary queue metrics."""
        with self._lock:
            with self._get_connection() as conn:
                cur = conn.execute("SELECT COUNT(*), COALESCE(SUM(payload_size), 0) FROM outbox_items;")
                total_row = cur.fetchone()
                total_count = total_row[0]
                total_bytes = total_row[1]

                status_counts: dict[str, int] = {}
                cur = conn.execute("SELECT status, COUNT(*) FROM outbox_items GROUP BY status;")
                for srow in cur.fetchall():
                    status_counts[srow[0]] = srow[1]

                priority_counts: dict[int, int] = {}
                cur = conn.execute("SELECT priority, COUNT(*) FROM outbox_items GROUP BY priority;")
                for prow in cur.fetchall():
                    priority_counts[prow[0]] = prow[1]

                return {
                    "total_count": total_count,
                    "total_bytes": total_bytes,
                    "status_counts": status_counts,
                    "priority_counts": priority_counts,
                }

    def clear_all(self) -> None:
        """Clear all outbox items. Intended for test fixtures and isolation."""
        with self._lock:
            with self._get_connection() as conn:
                conn.execute("DELETE FROM outbox_items;")
                conn.commit()

    @staticmethod
    def _row_to_record(row: sqlite3.Row) -> OutboxRecord:
        """Convert a SQLite row to an OutboxRecord dataclass instance."""
        try:
            payload = json.loads(row["payload"])
        except Exception:
            payload = {}

        return OutboxRecord(
            id=row["id"],
            event_type=row["event_type"],
            payload=payload,
            idempotency_key=row["idempotency_key"],
            priority=row["priority"],
            status=OutboxStatus(row["status"]),
            attempt_count=row["attempt_count"],
            max_attempts=row["max_attempts"],
            next_attempt_at=row["next_attempt_at"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            last_error=row["last_error"],
            payload_size=row["payload_size"],
        )
