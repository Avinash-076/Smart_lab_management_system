# Phase 8 Implementation: Runtime Architecture Modularization

## 1. Executive Summary

Phase 8 executes the runtime modularization and hardening objective established in the system roadmap. The monolithic, synchronous execution loop previously residing in `client_agent/core/runtime.py` and duplicated in `client_agent/main.py` has been decomposed into dedicated, cohesive, bounded sub-managers coordinated by `RuntimeManager`.

Full backwards compatibility is guaranteed through `AgentRuntime`, an adapter facade that preserves all legacy attributes, properties, cadence checkers, and module-level upload helpers.

All Phase 1–7 architectural invariants, including the Phase 3 `DurableOutbox` SQLite schema, retry backoff policies, priority classifications, Phase 5 monitoring cadences (20s/120s/900s), Phase 6 issue detection thresholds/hysteresis, and Phase 7 WebSocket lifecycle and durability semantics, have been strictly preserved.

---

## 2. Hardening Scope & Defect Remediations

| ID | Issue Description | Root Cause in Baseline | Phase 8 Remediation | Status |
|---|---|---|---|---|
| **H-01** | `main.py` had too many responsibilities & duplicate helpers | `main.py` duplicated telemetry uploads, authentication, and execution loop logic from `runtime.py`. | Extracted `RuntimeManager` as high-level coordinator; slimmed `main.py` to a thin CLI entry point handling only arguments, startup, and top-level CLI error handling. Preserved `AgentRuntime` facade. | **FIXED** |
| **H-02** | All collection was sequential | Fast metrics, hardware, network, usage, issues, running processes, and software inventory ran sequentially on a single thread. | Created `CollectorManager` with bounded thread worker pool (`max_workers=2`). Separated 20s fast telemetry from 120s process scans and 900s software inventory scans. | **FIXED** |
| **H-03** | REST uploads were sequential inside collection cycle | Main monitoring thread synchronously performed network I/O and payload assembly. | Created `UploadManager` to decouple payload building, idempotency key generation, and priority assignment, dispatching asynchronously to `OutboxManager`. | **FIXED** |
| **H-04** | Monitoring interval was not truly fixed | Loop executed collection/upload work and then invoked `time.sleep(20)` or `stop_event.wait(20)`, causing clock drift proportional to task duration. | Created `client_agent/core/scheduler.py` implementing drift-free monotonic target scheduling (`next_target = previous_target + interval`) with interruptible waits and overrun catch-up handling. | **FIXED** |
| **H-05** | No bounded worker architecture | Background tasks ran either synchronously or on ad-hoc threads without resource limits. | Enforced bounded thread pools for both collectors and outbox delivery. Outbox workers and collector threads are capped, named, and managed. | **FIXED** |

---

## 3. Architecture & Manager Responsibilities

```
main.py / service.py
        ↓
RuntimeManager (AgentRuntime Facade)
    ├── Scheduler (Drift-free monotonic cadence scheduling)
    ├── CollectorManager (Bounded workers; separates fast telemetry from slow scans)
    ├── UploadManager (Payload construction, idempotency keys, priority assignment)
    ├── OutboxManager (Wraps Phase 3 DurableOutbox & OutboxDeliveryWorker)
    ├── WebSocketManager (Orchestrates Phase 7 AgentWebSocketClient lifecycle)
    ├── TokenManager (Thread-safe JWT holder, scheduled & on-demand refresh)
    └── ShutdownManager (Staged, graceful, idempotent resource teardown)
```

### Component Details

1. **`RuntimeManager` (`client_agent/core/runtime.py`)**
   - High-level coordinator assembling and wiring sub-managers.
   - Handles enrollment verification, initial authentication, scheduling job registration, and lifecycle orchestration.
   - Contains zero collector scraping logic, outbox SQL, or WebSocket protocol parsing.

2. **`AgentRuntime` (`client_agent/core/runtime.py`)**
   - Subclasses `RuntimeManager` as a 100% backwards-compatible facade.
   - Exposes legacy attributes: `is_service`, `stop_event`, `token_holder`, `outbox`, `delivery_worker`, `ws_client`, `ws_state`, `is_connected`, `software_cache`, `process_cache`.
   - Exposes cadence checker methods: `due_for_process_collection()`, `due_for_software_scan()`.
   - Re-exports module-level helpers: `upload_metrics()`, `upload_software()`, `upload_processes()`, `upload_usage()`, `upload_issues()`, `display_console_data()`.

3. **`Scheduler` (`client_agent/core/scheduler.py`)**
   - Monotonic clock interval calculator (`target = previous_target + interval`).
   - Interruptible sleep using `stop_event.wait(wait_time)`.
   - Overrun protection: if a job takes longer than its interval, advances next run to `now + interval` to prevent queue storms.
   - Deterministic testing support via `run_pending(now)`.

4. **`CollectorManager` (`client_agent/core/managers.py`)**
   - Bounded thread pool (`ThreadPoolExecutor(max_workers=2, thread_name_prefix="SLMS-Collector")`).
   - Strictly enforces dependency ordering: `hardware` collection executes BEFORE `detect_issues()` is evaluated.
   - Isolates fast 20s telemetry from slow scans: a slow software scan never delays telemetry collection.

5. **`UploadManager` (`client_agent/core/managers.py`)**
   - Owns payload assembly and validation.
   - Generates exact Phase 3/5/6 idempotency keys:
     - Metrics: `metric_{comp_id}_{timestamp}_{uuid}`
     - Software: `software_{comp_id}_{fingerprint[:16]}`
     - Processes: `processes_{comp_id}_{timestamp}`
     - Usage: `usage_{comp_id}_{timestamp}_{len}`
     - Issues: `issue_{comp_id}_{issue_key}_{incident_id}`
   - Assigns Phase 3 priorities: `COMMAND` (1), `ISSUE` (2), `USAGE` (3), `TELEMETRY` (10).
   - Enqueues to `OutboxManager` without blocking collector cycles.

6. **`TokenManager` (`client_agent/core/managers.py`)**
   - Encapsulates `TokenHolder` with thread-safe `RLock` synchronization.
   - Manages scheduled token refreshes (12-minute cadence) and on-demand refresh callbacks for 401 re-authentication.

7. **`WebSocketManager` (`client_agent/core/managers.py`)**
   - Lifecycle management for `AgentWebSocketClient` (Phase 7).
   - Manages connection startup, state exposure (`state`, `is_connected`), and safe teardown.

8. **`ShutdownManager` (`client_agent/core/managers.py`)**
   - Coordinates multi-stage graceful shutdown in strict dependency order:
     1. Signal global stop event.
     2. Stop scheduler loop and cancel pending intervals.
     3. Stop collector worker executor.
     4. Stop outbox delivery worker with bounded flush timeout.
     5. Stop WebSocket client connection and listener threads.
   - Idempotent and thread-safe; guarded against double invocation and deadlocks.

---

## 4. Concurrency & Synchronization Model

- **Usage Collector State**: `client_agent/modules/usage.py` protects `_ACTIVE_SESSIONS` with an internal `threading.Lock()` (`_usage_lock`) across start, stop, and collection queries.
- **Cache Thread Safety**: `SoftwareCache` and `ProcessCache` in `client_agent/core/collector.py` encapsulate data access with internal `threading.Lock()` instances.
- **Token State**: `TokenHolder` and `TokenManager` use internal locks protecting read, write, and refresh cycles.
- **Bounded Worker Ceiling**: Maximum collector background workers fixed at 2, preventing resource exhaustion during heavy loads.

---

## 5. Verification & Test Results

### 1. Phase 8 Test Suite (`client_agent/tests/test_phase8_runtime.py`)
- `test_01_scheduler_drift_free_timing`: **PASSED**
- `test_02_scheduler_interruptible_shutdown`: **PASSED**
- `test_03_scheduler_overrun_catch_up`: **PASSED**
- `test_04_fast_collection_continues_while_slow_collection_runs`: **PASSED**
- `test_05_hardware_collection_precedes_issue_evaluation`: **PASSED**
- `test_06_shared_collector_state_safe_under_concurrency`: **PASSED**
- `test_07_upload_manager_payload_semantics`: **PASSED**
- `test_08_upload_manager_idempotency_keys`: **PASSED**
- `test_09_upload_manager_priorities`: **PASSED**
- `test_10_outbox_manager_uses_existing_durable_outbox`: **PASSED**
- `test_11_token_manager_concurrent_access_and_refresh`: **PASSED**
- `test_12_websocket_manager_lifecycle_compatibility`: **PASSED**
- `test_13_shutdown_manager_staged_shutdown`: **PASSED**
- `test_14_shutdown_manager_idempotency`: **PASSED**
- `test_15_agent_runtime_compatibility_facade`: **PASSED**
- `test_16_existing_cadence_methods_still_work`: **PASSED**
- `test_17_full_startup_shutdown_lifecycle`: **PASSED**

### 2. Full Regression Test Suites
- **Client Agent Suite**: `238 passed, 0 failed` in 24.82s.
- **Backend Suite**: `23 passed, 0 failed` in 1.28s.
- **Total Combined**: `261 passed, 0 failed`.

### 3. Database & Migration Invariants
- Alembic current: `a1b2c3d4e5f6 (head) (mergepoint)`
- Alembic heads: `a1b2c3d4e5f6 (head)`
- No Alembic migrations created.
- Zero changes to backend APIs or database schemas.

---

## 6. Non-Regression Confirmation

All behavior from earlier phases remains intact:
1. **Phase 1 Security**: Enrolled credentials and non-interactive Windows service constraints preserved.
2. **Phase 2 Windows Service**: Start, stop, and clean lifecycle integration preserved.
3. **Phase 3 Durable Outbox**: SQLite WAL schema, retry/backoff, priority queuing, and idempotency unchanged.
4. **Phase 4 Collectors**: Correct hardware metrics and inventory extraction preserved.
5. **Phase 5 Cadence**: 20s telemetry, 120s processes, 900s software inventory cadences strictly enforced.
6. **Phase 6 Issues**: Debounce, hysteresis, lifecycle states, and non-suppression on delivery failure preserved.
7. **Phase 7 WebSocket**: Reconnect backoff reset, token holder wiring, durable command results, and state observability preserved.
