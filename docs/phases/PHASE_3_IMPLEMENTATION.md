# Phase 3 — Durable Local State / Outbox Implementation Report

## Executive Summary

Phase 3 implements an enterprise-grade, persistent, crash-safe, bounded, and idempotent local delivery subsystem (**Durable Outbox**) for the Smart Lab Management System (SLMS) Client Agent.

Prior to Phase 3, client telemetry uploads, issue reports, application usage history, and WebSocket command execution results were transmitted synchronously over in-memory HTTP calls. Any network disruption, backend unavailability, machine reboot, or Windows Service restart resulted in permanent and silent loss of telemetry and critical command execution results. Furthermore, network response loss caused server-side duplication upon retry.

Phase 3 systematically solves these vulnerabilities across items **C-01 through C-08** by introducing:
- A local crash-safe SQLite outbox in Write-Ahead Logging (WAL) mode (`outbox.db`).
- Durable delivery queues with bounded retry for system metrics, software inventories, process inventories, usage sessions, issue alerts, and command results.
- Bounded storage backpressure with deterministic eviction that prioritizes critical command results and issue alerts.
- Bounded exponential backoff with ±20% uniform jitter and classified error handling (distinguishing retryable network/server faults from permanent 4xx client errors).
- Server-side and client-side end-to-end idempotency, ensuring duplicate transmissions never create duplicate database rows.
- Full security isolation: Zero credentials, access tokens, or secrets are ever written to the outbox database.

---

## 1. Problem Being Solved

In university lab environments across 40+ client workstations, workstations experience periodic network drops, switch reboots, backend downtime, and abrupt power cutoffs.

The specific failure modes addressed:
1. **Silent Telemetry Drop**: When the backend server or network is unreachable during periodic monitoring scans, metrics, inventory updates, and usage sessions were dropped immediately.
2. **Lost Command Results**: When remote commands (e.g. reboot, lock, message) executed while the WebSocket dropped or HTTP timed out, the result was discarded, leaving the administrator console showing commands perpetually stuck as "delivered".
3. **Lost Issue Alerts**: High-severity lab issues (CPU overheating, disk saturation, process anomalies) detected during network blips were lost.
4. **Server-Side Duplication**: When an HTTP request reached the backend and was committed, but the network failed before the response reached the agent, subsequent retries caused duplicate database rows for metrics, issues, usage sessions, and HTTP 409 Conflict errors for command results.
5. **Storage Saturation on Offline Workstations**: Long offline periods could accumulate unbounded logs and records without memory or disk caps.

---

## 2. Existing Delivery Architecture

Prior to Phase 3:
- `AgentRuntime.start()` executed a synchronous monitoring loop every `MONITOR_INTERVAL` (20s).
- `upload_metrics`, `upload_software`, `upload_processes`, `upload_usage`, and `upload_issues` called `client_agent/server/sender.py` directly using `requests.post()`.
- If an HTTP request raised `requests.RequestException` or HTTP 5xx, it was logged via `logger.exception()` and execution continued. The data was never queued or retried.
- In `client_agent/server/communication.py`, when a command message arrived over WebSocket, `execute_command()` ran and called `self._send_command_result()`. If the POST failed, the result was lost.
- All telemetry and execution state was entirely ephemeral and memory-only.

---

## 3. New Outbox Architecture

Phase 3 introduces a producer-consumer outbox architecture located in [`client_agent/core/outbox/`](file:///d:/PC/slms1/Smart_lab_management_system/client_agent/core/outbox/):

```
Producer Threads                          Durable Local Storage                     Consumer Worker
(Runtime / WebSocket)                     (%ProgramData%\SLMS\outbox)               (OutboxDeliveryWorker)
+-------------------------+               +-------------------------+               +-----------------------+
|  Telemetry / Metrics    |               |                         |               |                       |
|  Software Inventory     | -- enqueue -> |   SQLite WAL Database   | -- claim ---> |  Delivery Worker      |
|  Process Inventory      |  (< 1 ms)     |   (outbox.db)           |   (batch)     |  Thread               |
|  Usage Sessions         |               |                         |               |                       |
|  Issue Reports          |               |  - PENDING              |               |  - Token Injection    |
|  Command Results        |               |  - PROCESSING           |               |  - Error Classifier   |
+-------------------------+               |  - DEAD_LETTER          |               |  - Exponential Backoff|
            |                             +-------------------------+               +-----------------------+
            |                                          |                                        |
     wake_event.set()                                  |                                   HTTP POST
            |                                          |                                        |
            +------------------------------------------+-------------------------------> Backend Server
                                                                                         (/api/*)
```

### Components:
- **`DurableOutbox`** ([`storage.py`](file:///d:/PC/slms1/Smart_lab_management_system/client_agent/core/outbox/storage.py)): SQLite storage manager with explicit transaction boundaries, WAL mode, schema version tracking, backpressure pruning, and stale processing recovery.
- **`OutboxDeliveryWorker`** ([`worker.py`](file:///d:/PC/slms1/Smart_lab_management_system/client_agent/core/outbox/worker.py)): Background daemon thread that drains pending records in priority order, handles token injection, re-authentication, error classification, and backoff scheduling.
- **`OutboxPolicy`** ([`policy.py`](file:///d:/PC/slms1/Smart_lab_management_system/client_agent/core/outbox/policy.py)): Bounded exponential backoff calculation with jitter, error categorization, and backpressure limit definitions.
- **`OutboxModels`** ([`models.py`](file:///d:/PC/slms1/Smart_lab_management_system/client_agent/core/outbox/models.py)): Dataclass definitions and enumerations for record status and priority levels.

---

## 4. SQLite Schema

The outbox database is stored at `paths.OUTBOX_DB_PATH` (`%PROGRAMDATA%\SLMS\outbox\outbox.db` in production; project data folder in development).

### Tables:

#### `outbox_schema_version`
Tracks migrations without introducing heavy external dependencies:
```sql
CREATE TABLE IF NOT EXISTS outbox_schema_version (
    version INTEGER PRIMARY KEY,
    applied_at REAL NOT NULL
);
```

#### `outbox_items`
Stores the queued events:
```sql
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

CREATE INDEX IF NOT EXISTS ix_outbox_items_pending
ON outbox_items (status, next_attempt_at, priority, created_at);

CREATE INDEX IF NOT EXISTS ix_outbox_items_idempotency
ON outbox_items (idempotency_key);

CREATE INDEX IF NOT EXISTS ix_outbox_items_event_type
ON outbox_items (event_type);
```

### SQLite PRAGMA Configuration:
- `PRAGMA journal_mode = WAL;` (Enables concurrent readers and writers without database lock contention)
- `PRAGMA busy_timeout = 5000;` (Waits up to 5 seconds during busy lock transitions)
- `PRAGMA synchronous = NORMAL;` (Provides crash safety across power failures while maintaining optimal write throughput)

---

## 5. State Machine

Each outbox record moves through an explicit, crash-resilient state machine:

```
           [ Enqueue ]
                |
                v
         +--------------+
         |   PENDING    |<-----------------------------------+
         +--------------+                                    |
                |                                            |
       Claim due batch (<= now)                    Retryable failure
                |                                  (attempt < max_attempts)
                v                                  with exponential backoff
         +--------------+                                    |
         |  PROCESSING  |------------------------------------+
         +--------------+
           |          |
      Success /      Permanent failure (4xx) /
      409 Duplicate  Max attempts reached
           |          |
           v          v
       [ DELETED ]  +---------------+
       (from DB)    |  DEAD_LETTER  |
                    +---------------+
```

1. **`PENDING`**: Initial state on insertion. Eligible for delivery when `time.time() >= next_attempt_at`.
2. **`PROCESSING`**: Atomically claimed by the delivery worker. If the agent crashes or service stops while an item is in this state, `recover_stale_processing()` resets it to `PENDING` upon startup.
3. **`DELIVERED` (`DELETED`)**: Upon HTTP 2xx or HTTP 409 (idempotent duplicate), the record is deleted immediately from the database to maintain minimal storage footprint.
4. **`DEAD_LETTER`**: Items that fail with non-retryable 4xx client errors (400, 403, 404, 422) or exceed their configured `max_attempts` transition to `DEAD_LETTER`. They are preserved for diagnostics and purged after 7 days during backpressure maintenance.

---

## 6. Retry Policy

The retry policy is defined in [`client_agent/core/outbox/policy.py`](file:///d:/PC/slms1/Smart_lab_management_system/client_agent/core/outbox/policy.py):

| Parameter | Value | Description |
|---|---|---|
| `INITIAL_RETRY_DELAY` | `2.0s` | Initial delay before the first retry attempt |
| `MAX_RETRY_DELAY` | `300.0s` | Upper ceiling on backoff delay (5 minutes) |
| `BACKOFF_FACTOR` | `2.0` | Multiplier for exponential backoff ($2^n$) |
| `JITTER_RATIO` | `±20%` | Bounded uniform random jitter to eliminate retry thundering herds |
| `DEFAULT_MAX_ATTEMPTS_TELEMETRY` | `5` | Maximum retry attempts for metrics and inventories |
| `DEFAULT_MAX_ATTEMPTS_CRITICAL` | `10` | Maximum retry attempts for command results, issues, and usage |

### Delay Calculation:
$$\text{base} = \min(\text{INITIAL\_RETRY\_DELAY} \times 2^{\text{attempt} - 1}, \text{MAX\_RETRY\_DELAY})$$
$$\text{delay} = \max(0.5, \text{base} + (\text{base} \times 0.2 \times \text{Uniform}(-1.0, 1.0)))$$

### Error Classification Table:

| HTTP Status / Exception | Classification | Action |
|---|---|---|
| HTTP 200, 201, 204 | `SUCCESS` | Mark delivered (delete from outbox) |
| HTTP 409 Conflict | `IDEMPOTENT_DUPLICATE` | Server already committed record; mark delivered |
| HTTP 401 Unauthorized | `AUTH_EXPIRED` | Refresh access token immediately and retry in-memory |
| HTTP 400, 403, 404, 422 | `PERMANENT_FAILURE` | Mark `DEAD_LETTER` immediately (no useless retries) |
| HTTP 429 Too Many Requests | `RETRYABLE_FAILURE` | Retry with exponential backoff and jitter |
| HTTP 500, 502, 503, 504 | `RETRYABLE_FAILURE` | Retry with exponential backoff and jitter |
| `requests.ConnectionError` | `RETRYABLE_FAILURE` | Retry with exponential backoff and jitter |
| `requests.Timeout` | `RETRYABLE_FAILURE` | Retry with exponential backoff and jitter |

---

## 7. Idempotency Strategy

To prevent duplicate server-side writes caused by network response loss, Phase 3 implements coordinated client-side and server-side idempotency across all delivery paths.

### 1. Command Execution Results:
- **Client**: Assigns `idempotency_key = f"cmd_result_{command_id}"` with `priority = OutboxPriority.COMMAND`.
- **Backend** ([`backend/app/services/command_service.py`](file:///d:/PC/slms1/Smart_lab_management_system/backend/app/services/command_service.py)):
  In `submit_result()`: If `command.result is not None` and the submitted payload matches the existing result (`success` and `message`), the service idempotently returns the existing `command.result` without raising 409 Conflict.
- **Client Outbox Worker**: If HTTP 409 is received, the worker treats the duplicate as delivered and purges the outbox record.

### 2. Auto-Detected Issue Alerts:
- **Client**: Assigns `idempotency_key = f"issue_{computer_id}_{title_slug}_{timestamp}"`.
- **Backend** ([`backend/app/services/issue_service.py`](file:///d:/PC/slms1/Smart_lab_management_system/backend/app/services/issue_service.py)):
  In `create_issue()`: When `source == IssueSource.agent`, checks if an open issue with matching `computer_id` and `title` already exists. If found, updates the description, severity, and `updated_at` on the existing ticket rather than inserting duplicate issue rows.

### 3. Application Usage Sessions:
- **Client**: Assigns `idempotency_key = f"usage_{computer_id}_{timestamp}_{count}"`.
- **Backend** ([`backend/app/services/usage_service.py`](file:///d:/PC/slms1/Smart_lab_management_system/backend/app/services/usage_service.py)):
  In `create_usage_sessions()`: Checks if an existing session with `(computer_id, application_name, started_at)` is present. If found, updates `ended_at` and `duration_seconds` rather than inserting duplicate records.

### 4. System Metrics:
- **Client**: Assigns `idempotency_key = f"metric_{computer_id}_{timestamp}_{uuid}"`.
- **Backend** ([`backend/app/models/system_metric.py`](file:///d:/PC/slms1/Smart_lab_management_system/backend/app/models/system_metric.py), [`backend/app/services/metric_service.py`](file:///d:/PC/slms1/Smart_lab_management_system/backend/app/services/metric_service.py)):
  Added `idempotency_key: Mapped[str | None]` column. If `metric_data.idempotency_key` matches an existing metric row, the service returns the existing record idempotently.

### 5. Inventories (Software & Processes):
- **Backend** ([`backend/app/services/software_service.py`](file:///d:/PC/slms1/Smart_lab_management_system/backend/app/services/software_service.py), [`backend/app/services/process_service.py`](file:///d:/PC/slms1/Smart_lab_management_system/backend/app/services/process_service.py)):
  Both services execute atomic replacement in a database transaction (`DELETE FROM table WHERE computer_id = ?` followed by bulk insertion of the latest snapshot). They are inherently idempotent.

---

## 8. Backpressure Policy

To prevent an offline workstation from consuming unbounded disk space or memory:
- `MAX_OUTBOX_RECORDS`: **5,000 records**
- `MAX_OUTBOX_BYTES`: **20 Megabytes (20,971,520 bytes)**

### Deterministic Eviction Hierarchy:
When insertion would exceed limits, `DurableOutbox._enforce_backpressure()` executes in a transaction:
1. **Purge Expired Dead-Letter Items**: Deletes `DEAD_LETTER` items older than 7 days.
2. **Prune Oldest Telemetry**: If still saturated, deletes oldest `PENDING` items where `priority >= OutboxPriority.TELEMETRY` (10). Older metrics/process snapshots are superseded by newer data.
3. **Prune Oldest Usage**: If still saturated and the incoming item is a critical command or issue, prunes oldest `USAGE` records (priority 3).
4. **Critical Priority Retention Policy**: The system prioritizes `command_result` (`priority=1`) and `issue` (`priority=2`) over usage and telemetry, evicting lower-priority records first during saturation. If the queue is saturated entirely with critical records and lower priority data cannot be accommodated, a `QueueFullError` is raised and logged cleanly without unbounded memory fallback.
5. If the queue limit is reached and cannot admit an event, the producer records the enqueue failure, logs the error, and the monitoring loop continues healthy execution without unbounded memory buffering.

---

## 9. Offline Behavior

When the network or backend is offline:
1. **Producer Non-Blocking Fast Enqueue**: The monitoring loop continues collecting data without blocking for network timeouts. Enqueuing into SQLite takes less than 1 millisecond.
2. **Progressive Queue Drain**: When connectivity returns, the delivery worker wakes up immediately via its wake event and progressively drains records in priority order (`COMMAND` -> `ISSUE` -> `USAGE` -> `TELEMETRY`).
3. **No Unbounded Bursts**: The worker drains items in batches of 20 (`batch_size=20`), preventing network flooding or server starvation.

---

## 10. Crash Recovery & Atomicity

1. **Transactional Transitions**: All state changes (`enqueue`, `get_pending_batch`, `mark_retry`, `mark_dead_letter`, `mark_delivered`) execute inside SQLite transactions.
2. **Stale Processing Recovery**: If the Windows Service process terminates abruptly (e.g. power cutoff, crash, taskkill) while records are in `PROCESSING` status, the worker calls `outbox.recover_stale_processing()` upon restart, resetting them to `PENDING` so in-flight items survive restarts.
3. **Reopening Durability**: Database transactions are synchronized using WAL mode, ensuring that reopening the SQLite connection across restarts restores all pending items.

### Delivery & Durability Semantics (Bounded Retries & Idempotency):
- **Durability**: Once an item is accepted into SQLite (`outbox.db`), it survives agent restarts, Windows Service restarts, and system reboots.
- **Bounded Retries**: The system does NOT claim infinite delivery guarantees. Retries are strictly bounded (5 attempts for telemetry, 10 attempts for critical events). Records exceeding maximum attempts or failing with permanent HTTP 4xx client errors transition to `DEAD_LETTER`.
- **At-Least-Once Delivery**: The agent guarantees at-least-once delivery attempts. Network drops after server commit are handled safely via server-side database-level uniqueness constraints and idempotency keys, guaranteeing duplicate-free processing.

---

## 11. Security & Storage Analysis

1. **No Secrets in Database**:
   - Zero JWTs, access tokens, client secrets, passwords, or hashes are stored in SQLite columns or payload JSON.
   - Payloads contain only telemetry and operational data.
   - Authentication tokens are held in-memory and injected dynamically by `OutboxDeliveryWorker` during HTTP transmission.
2. **Access Control (Windows ACLs)**:
   - The production outbox database resides in `%PROGRAMDATA%\SLMS\outbox\outbox.db`.
   - Inherits Phase 2 service directory permissions granting `(OI)(CI)(M)` to `NT SERVICE\SLMSService` and Administrators, while restricting unprivileged student accounts.
3. **Git Cleanliness**:
   - `.gitignore` updated with `outbox/`, `*.db`, `*.db-wal`, and `*.db-shm`. No runtime databases are committed to source control.

---

## 12. Producers Integration

All existing producer pathways are mapped to the durable outbox:

| Producer Source | Target Event Type | Priority | Idempotency Key Format |
|---|---|---|---|
| System Metrics (`runtime.py`) | `metrics` | 10 (`TELEMETRY`) | `metric_{computer_id}_{timestamp}_{uuid}` |
| Software Inventory (`runtime.py`) | `software` | 10 (`TELEMETRY`) | `software_{computer_id}_{timestamp}` |
| Process Inventory (`runtime.py`) | `processes` | 10 (`TELEMETRY`) | `processes_{computer_id}_{timestamp}` |
| Usage History (`runtime.py`) | `usage` | 3 (`USAGE`) | `usage_{computer_id}_{timestamp}_{count}` |
| Issue Alarms (`runtime.py`) | `issue` | 2 (`ISSUE`) | `issue_{computer_id}_{title}_{timestamp}` |
| WebSocket Commands (`communication.py`) | `command_result` | 1 (`COMMAND`) | `cmd_result_{command_id}` |

---

## 13. Test Results & Verification

### Test Summary:
- **Client Tests**: **93 passed** (62 existing + 31 Phase 3 tests)
- **Backend Tests**: **23 passed** (13 existing + 10 Phase 3 tests)
- **Total Suite**: **116 passed, 0 failed** (100% pass rate)

### Automated Test Matrix:

| Requirement ID | Test Function | Result |
|---|---|---|
| 1. Enqueue item | `test_01_enqueue_item` | PASSED |
| 2. Retrieve pending item | `test_02_retrieve_pending_item` | PASSED |
| 3. Successful delivery | `test_03_successful_delivery` | PASSED |
| 4. Retryable failure | `test_04_retryable_failure` | PASSED |
| 5. Exponential backoff | `test_05_exponential_backoff` | PASSED |
| 6. Non-retryable failure | `test_06_non_retryable_failure` | PASSED |
| 7. Maximum retry / dead-letter | `test_07_maximum_retry_dead_letter_behavior` | PASSED |
| 8. Idempotency key generation | `test_08_idempotency_key_generation` | PASSED |
| 9. Duplicate enqueue prevention | `test_09_duplicate_enqueue_prevention` | PASSED |
| 10. Response-loss retry scenario | `test_10_response_loss_retry_scenario` | PASSED |
| 11. Persistence after process restart | `test_11_persistence_after_process_restart` | PASSED |
| 12. Persistence after reopening SQLite | `test_12_persistence_after_reopening_sqlite_database` | PASSED |
| 13. Queue capacity limit | `test_13_queue_capacity_limit` | PASSED |
| 14. Payload / storage limit | `test_14_payload_storage_limit` | PASSED |
| 15. Concurrent producers | `test_15_concurrent_producers` | PASSED |
| 16. Delivery worker concurrency | `test_16_delivery_worker_concurrency` | PASSED |
| 17. Network unavailable | `test_17_network_unavailable` | PASSED |
| 18. Network restored | `test_18_network_restored` | PASSED |
| 19. Authentication refresh behavior | `test_19_authentication_refresh_behavior` | PASSED |
| 20. Telemetry durability | `test_20_telemetry_durability` | PASSED |
| 21. Issue durability | `test_21_issue_durability` | PASSED |
| 22. Usage-session durability | `test_22_usage_session_durability` | PASSED |
| 23. Command-result durability | `test_23_command_result_durability` | PASSED |
| 24. Crash-safe transaction behavior | `test_24_crash_safe_transaction_behavior` | PASSED |
| 25. No secrets in outbox | `test_25_no_credentials_stored_in_outbox` | PASSED |
| 26. Service shutdown with pending records | `test_26_service_shutdown_with_pending_records` | PASSED |
| 27. Restart with pending records | `test_27_restart_with_pending_records` | PASSED |
| 28. Phase 1 regression | `test_28_phase_1_regression` | PASSED |
| 29. Phase 2 regression | `test_29_phase_2_regression` | PASSED |
| 30. Idempotency key lifecycle | `test_30_idempotency_key_lifecycle_preserved_across_retries` | PASSED |
| 31. Backpressure QueueFullError | `test_31_backpressure_queue_full_behavior` | PASSED |
| Backend Command Idempotency | `test_command_result_idempotent_retry` | PASSED |
| Backend Issue Deduplication | `test_agent_issue_idempotent_deduplication` | PASSED |
| Backend Usage Deduplication | `test_usage_session_idempotent_deduplication` | PASSED |
| Backend Metric Idempotency | `test_metrics_idempotent_deduplication` | PASSED |
| Backend Concurrent Metric Idempotency | `test_concurrent_metric_idempotency` | PASSED |
| Backend Concurrent Command Idempotency | `test_concurrent_command_result_idempotency` | PASSED |
| Backend Concurrent Issue Idempotency | `test_concurrent_agent_issue_idempotency` | PASSED |
| Backend Concurrent Usage Idempotency | `test_concurrent_usage_session_idempotency` | PASSED |
| Backend Software Inventory Idempotent Retry | `test_software_inventory_idempotent_retry` | PASSED |
| Backend Process Inventory Idempotent Retry | `test_process_inventory_idempotent_retry` | PASSED |

---

## 14. Known Limitations

1. **Dead-Letter Diagnostic UI**: `DEAD_LETTER` items remain in the SQLite table until pruned by 7-day retention or capacity backpressure. An administrative dashboard endpoint to inspect dead-letter items will be introduced in subsequent backend management phases.
2. **In-Flight Network Timeouts**: A transaction that times out during HTTP sending may take up to the configured HTTP timeout (10–30s) before marking the attempt as retryable in SQLite.

---

## 15. Explicitly Deferred Phase 4+ Work

Per the strict scope boundary:
- **Phase 4**: Collector redesign and process monitor optimization (NOT started).
- **Phase 5**: Software inventory redesign (NOT started).
- **Phase 6**: Issue hysteresis, debounce, and stateful lifecycle rules (NOT started).
- **Phase 7**: WebSocket reconnect redesign and heartbeat state machine (NOT started).
- **Phase 8**: Full scheduler / manager runtime modularization (NOT started).
- **Phase 9**: Logging rotation and Windows Event Log integration (NOT started).
- **Phase 10**: Packaging and MSI deployment (NOT started).
