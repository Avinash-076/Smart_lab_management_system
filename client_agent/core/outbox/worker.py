"""
Background delivery worker for the SLMS durable outbox.

Monitors the outbox SQLite database and delivers queued items to the SLMS backend
over HTTP according to explicit retry, backoff, and idempotency policies.
"""

from __future__ import annotations

from collections.abc import Callable
import threading
import time
from typing import Any

from core.logger import logger
from core.outbox.models import OutboxRecord
from core.outbox.policy import (
    ErrorClassification,
    calculate_backoff_delay,
    classify_exception,
)
from core.outbox.storage import DurableOutbox
from server.sender import (
    send_command_result,
    send_issue,
    send_metrics,
    send_process_inventory,
    send_software_inventory,
    send_usage_sessions,
)


class OutboxDeliveryWorker:
    """
    Dedicated worker thread responsible for draining and retrying pending outbox records.
    """

    def __init__(
        self,
        outbox: DurableOutbox,
        get_token: Callable[[], str],
        refresh_token: Callable[[], str] | None = None,
        batch_size: int = 20,
        poll_interval: float = 5.0,
        stop_event: threading.Event | None = None,
        wake_event: threading.Event | None = None,
        on_delivered: Callable[[OutboxRecord], None] | None = None,
    ):
        self.outbox = outbox
        self.get_token = get_token
        self.refresh_token = refresh_token
        self.batch_size = batch_size
        self.poll_interval = poll_interval
        self.stop_event = stop_event or threading.Event()
        self.wake_event = wake_event or self.outbox.wake_event or threading.Event()
        self.on_delivered = on_delivered
        self.outbox.wake_event = self.wake_event

        self._thread: threading.Thread | None = None
        self._is_running = False

    @property
    def is_running(self) -> bool:
        return self._is_running

    def start(self) -> None:
        """Start the background delivery thread."""
        if self._thread is not None and self._thread.is_alive():
            return

        self._is_running = True
        self._thread = threading.Thread(
            target=self._run_loop,
            name="SLMS-OutboxWorker",
            daemon=True,
        )
        self._thread.start()
        logger.info("SLMS Outbox delivery worker started.")

    def stop(self, timeout: float = 5.0) -> None:
        """Signal the delivery thread to terminate and wait for exit."""
        self._is_running = False
        self.stop_event.set()
        self.wake_event.set()

        if self._thread is not None and self._thread.is_alive():
            self._thread.join(timeout=timeout)
            self._thread = None

        logger.info("SLMS Outbox delivery worker stopped.")

    def _run_loop(self) -> None:
        """Main loop: recover stale processing items and periodically drain queue."""
        # On worker startup, immediately recover any stranded PROCESSING records from prior crashed process
        try:
            self.outbox.recover_stale_processing(stale_threshold_seconds=0.0)
        except Exception as e:
            logger.exception(f"Error recovering stale outbox records on startup: {e}")

        last_stale_check = time.monotonic()

        while not self.stop_event.is_set():
            now = time.monotonic()
            # Periodically recover any stuck PROCESSING items (e.g. every 60s)
            if now - last_stale_check >= 60.0:
                try:
                    self.outbox.recover_stale_processing(stale_threshold_seconds=60.0)
                    last_stale_check = now
                except Exception as e:
                    logger.exception(f"Error checking stale outbox records: {e}")

            try:
                has_more = self.drain_once()
                if has_more:
                    # If there were items processed, check for more immediately
                    continue
            except Exception as e:
                logger.exception(f"Unexpected error in outbox delivery worker loop: {e}")

            # Responsive wait: sleep until poll_interval or awakened by enqueue
            self.wake_event.wait(timeout=self.poll_interval)
            self.wake_event.clear()

    def drain_once(self) -> bool:
        """
        Attempt to process one batch of pending items.
        Returns True if a batch was processed (indicating more work may be available),
        or False if no items were due or delivery is paused.
        """
        # Ensure we have an access token before fetching or claiming records
        token = self.get_token()
        if not token and self.refresh_token:
            try:
                token = self.refresh_token()
            except Exception as e:
                logger.debug(f"Outbox delivery waiting for valid token: {e}")
                return False

        if not token:
            return False

        try:
            batch = self.outbox.get_pending_batch(limit=self.batch_size)
        except Exception as e:
            logger.exception(f"Error querying pending outbox records: {e}")
            return False

        if not batch:
            return False

        for idx, item in enumerate(batch):
            if self.stop_event.is_set():
                remaining_ids = [b.id for b in batch[idx:]]
                self.outbox.release_pending_batch(remaining_ids)
                break

            delivery_ok = self._process_single_item(item, token)
            if not delivery_ok:
                # If item delivery encountered an authentication loss and re-auth failed,
                # stop batch processing and release remaining items without incrementing attempt count
                remaining_ids = [b.id for b in batch[idx + 1:]]
                if remaining_ids:
                    self.outbox.release_pending_batch(remaining_ids)
                return False

        return len(batch) >= self.batch_size

    def _process_single_item(self, item: OutboxRecord, token: str | None = None) -> bool:
        """Deliver a single outbox record to the appropriate endpoint."""
        if not token:
            token = self.get_token()

        if not token and self.refresh_token:
            try:
                token = self.refresh_token()
            except Exception as e:
                logger.warning(f"Failed to obtain token for outbox delivery: {e}")
                self.outbox.release_pending_batch([item.id], last_error="No valid access token available")
                return False

        if not token:
            self.outbox.release_pending_batch([item.id], last_error="No access token configured")
            return False

        try:
            self._dispatch_event(item, token)
            self.outbox.mark_delivered(item.id)
            if self.on_delivered:
                try:
                    self.on_delivered(item)
                except Exception as cb_err:
                    logger.warning(f"Error in on_delivered callback for item {item.id}: {cb_err}")
            logger.debug(f"Outbox item {item.id} ({item.event_type}) delivered successfully.")
            return True
        except Exception as exc:
            return self._handle_delivery_failure(item, exc, token)

    def _dispatch_event(self, item: OutboxRecord, token: str) -> None:
        """Call the appropriate sender function based on event_type."""
        event_type = item.event_type
        payload = item.payload

        if event_type == "metrics":
            # Attach idempotency_key to payload if present
            metric_payload = dict(payload)
            if "idempotency_key" not in metric_payload:
                metric_payload["idempotency_key"] = item.idempotency_key
            send_metrics(metric_payload, token)

        elif event_type == "software":
            send_software_inventory(payload, token)

        elif event_type == "processes":
            send_process_inventory(payload, token)

        elif event_type == "usage":
            send_usage_sessions(payload, token)

        elif event_type == "issue":
            issue_payload = dict(payload)
            if "idempotency_key" not in issue_payload and item.idempotency_key:
                issue_payload["idempotency_key"] = item.idempotency_key
            send_issue(issue_payload, token)

        elif event_type == "command_result":
            cmd_id = payload.get("command_id")
            if cmd_id is None:
                raise ValueError("command_result payload missing command_id")
            result_payload = {
                "success": payload.get("success", False),
                "message": payload.get("message", ""),
            }
            send_command_result(int(cmd_id), result_payload, token)

        else:
            raise ValueError(f"Unknown outbox event type: '{event_type}'")

    def _handle_delivery_failure(
        self,
        item: OutboxRecord,
        exc: Exception,
        current_token: str,
    ) -> bool:
        """Analyze failure and apply retry, dead-letter, or idempotent resolution."""
        classification, error_msg = classify_exception(exc)

        # 1. Idempotent Duplicate
        if classification == ErrorClassification.IDEMPOTENT_DUPLICATE:
            logger.info(
                f"Outbox item {item.id} duplicate confirmed by server ({error_msg}); marked delivered."
            )
            self.outbox.mark_delivered(item.id)
            if self.on_delivered:
                try:
                    self.on_delivered(item)
                except Exception as cb_err:
                    logger.warning(f"Error in on_delivered callback for item {item.id}: {cb_err}")
            return True

        # 2. Authentication Expired (HTTP 401)
        if classification == ErrorClassification.AUTH_EXPIRED and self.refresh_token:
            logger.warning(f"Outbox delivery received 401 Unauthorized for item {item.id}. Re-authenticating...")
            try:
                new_token = self.refresh_token()
                if new_token:
                    # Retry immediately with refreshed token
                    self._dispatch_event(item, new_token)
                    self.outbox.mark_delivered(item.id)
                    if self.on_delivered:
                        try:
                            self.on_delivered(item)
                        except Exception as cb_err:
                            logger.warning(f"Error in on_delivered callback for item {item.id}: {cb_err}")
                    logger.info(f"Outbox item {item.id} delivered successfully after re-authentication.")
                    return True
            except Exception as retry_exc:
                logger.warning(f"Re-authentication failed after 401 for item {item.id}: {retry_exc}")
                # Auth failure is a global dependency failure: release item back to PENDING without incrementing attempt count
                self.outbox.release_pending_batch(
                    [item.id],
                    last_error=f"401 Unauthorized (re-auth failed: {retry_exc})",
                )
                return False

        # 3. Permanent Client Error (400, 403, 404, 422, InvalidServerUrlError)
        if classification == ErrorClassification.PERMANENT_FAILURE:
            logger.error(
                f"Outbox item {item.id} ({item.event_type}) non-retryable failure: {error_msg}. Moving to DEAD_LETTER."
            )
            self.outbox.mark_dead_letter(item.id, error_msg)
            return True

        # 4. Retryable Error (Network, Timeout, 429, 5xx, TransportSecurityError)
        delay = calculate_backoff_delay(item.attempt_count + 1)
        next_attempt = time.time() + delay
        self.outbox.mark_retry(item.id, error_msg, next_attempt)
        logger.warning(
            f"Outbox item {item.id} ({item.event_type}) temporary failure: {error_msg}. "
            f"Attempt {item.attempt_count + 1}/{item.max_attempts}. Retrying in {delay}s."
        )
        return True
