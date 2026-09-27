# Phase 5 Implementation Report: Monitoring Optimization

## 1. Objective
Optimize monitoring frequency, process collection, software inventory collection, payload size, filtering, and change detection. Decouple expensive inventory scans from the 20-second high-frequency metrics cycle while preserving hardware telemetry, network counters, and issue detection cadence.

Approved target cadence:
- Metrics: 20 seconds
- Network: 20 seconds
- Issues: 20 seconds
- Usage: event / local (20s polling)
- Processes: 1–5 minutes (configured to 120s / 2 minutes)
- Software: 10–30 minutes / change-based (configured to 900s / 15 minutes)

---

## 2. Problems Addressed (E-01 through E-07)
| ID | Defect / Problem | Resolution Summary |
| :--- | :--- | :--- |
| **E-01** | Full process list every 20 seconds is too expensive | Gated process enumeration to 120s interval via `AgentRuntime.due_for_process_collection` and `ProcessCache` (TTL=120s). Metrics remain strictly on 20s cadence. |
| **E-02** | No system-process filtering | Added deterministic filtering of Windows kernel and idle pseudo-processes (PID 0, PID 4, Registry, Memory Compression, Secure System, Idle, Interrupts). Preserved legitimate services and user apps. |
| **E-03** | Process usernames / privacy | Verified and enforced that process owners, Windows login accounts, and user strings are never queried or collected. Hardcoded `user: None` in output; validated JSON serialization produces `user: null`. |
| **E-04** | Process payload can become large | Implemented explicit bounded limit (`MAX_PROCESSES_INVENTORY = 500`, configurable) and maximum process name truncation (`MAX_PROCESS_NAME_LENGTH = 255`). Sorted deterministically with resource-prioritized ordering (`-cpu_percent`, `-memory_percent`, `name.casefold()`, `pid`). |
| **E-05** | Software inventory uploaded every 20 seconds | Gated software scanning to 15-minute interval (`SOFTWARE_SCAN_INTERVAL = 900`). Decoupled software upload from the 20s metric cycle. Reuses `SoftwareCache` between scans. |
| **E-06** | Software inventory is not change-aware | Implemented deterministic SHA-256 fingerprinting with normalized field values and canonical item sorting. Persisted fingerprint across agent restarts via atomic JSON file. Skipped upload when inventory is unchanged. |
| **E-07** | Software discovery coverage incomplete | Audited registry coverage (HKLM 64-bit and 32-bit). Documented explicit scope and known limitations (HKCU per-user applications, MSIX/Store packages, portable executables). Avoided premature discovery expansion. |

---

## 3. Existing Behavior Found During Inspection
1. **Unconditional 20-Second Process Collection**: In Phase 4, `core/collector.py::collect_all_data()` invoked `get_running_processes()` on every single iteration of the monitoring loop. `psutil.process_iter()` enumerated hundreds of process handles every 20 seconds, causing continuous CPU spikes.
2. **Unconditional 20-Second Software Upload**: Although Phase 4 added `SoftwareCache` to avoid scanning the registry every 20s, `core/runtime.py` called `upload_software(data, ...)` on every 20s cycle, enqueuing the identical cached software list into the durable outbox repeatedly.
3. **No Process Inventory Filtering**: While Phase 4 D-12 added filtering to *usage tracking*, general process inventory had no filtering. "System Idle Process" (PID 0), "System" (PID 4), and kernel memory manager pseudo-processes were transmitted to the backend every cycle.
4. **Non-Deterministic Sort Order**: Previously, processes were sorted purely by `(item["cpu_percent"], item["memory_percent"])`. On machines with many 0% CPU processes, output ordering fluctuated based on arbitrary OS PID enumeration order.
5. **No Inventory Change Detection**: The client had no concept of an inventory fingerprint. A machine running for days would repeatedly upload the identical list of installed applications.

---

## 4. Process Cadence Design (E-01)
- **Configuration**:
  - `PROCESS_COLLECTION_INTERVAL = int(os.getenv("SLMS_PROCESS_INTERVAL", "120"))` (default 120s / 2 minutes, within the approved 1–5 minute range).
- **Two-Tier Protection**:
  1. **Runtime Decision Gating**: `AgentRuntime` tracks `_last_process_collection`. `due_for_process_collection(now)` returns `True` on the initial cycle, and thereafter only when 120 seconds have elapsed. On cycles 1–5 (t = 20s, 40s, 60s, 80s, 100s), `due_for_process_collection` returns `False`.
  2. **Collector Gating**: `collect_all_data(include_processes=due_proc)` skips `get_running_processes()` entirely when `due_proc` is `False`. `ProcessCache` (TTL=120s) caches results if called externally, preventing repeated `psutil.process_iter()` sweeps.
- **Upload Safety**: `upload_processes()` verifies `processes_entry is not None`. If processes were bypassed, it returns `False` immediately without creating outbox records or network requests.
- **Monitoring Cadence Integrity**: Hardware metrics, cumulative network byte counters, student usage sessions, and issue threshold evaluations execute every 20 seconds without delay.

---

## 5. Process Filtering Policy (E-02)
- **Filtered Targets**:
  - Kernel PIDs: `PID 0` (System Idle Process), `PID 4` (System / ntoskrnl).
  - Kernel Pseudo-Processes: `"System Idle Process"`, `"System"`, `"Registry"`, `"Memory Compression"`, `"Secure System"`, `"Idle"`, `"Interrupts"`.
  - These pseudo-processes have no user-mode image, cannot be terminated, and produce noise in lab inventory.
- **Preserved Targets**:
  - Legitimate Windows background services: `svchost.exe`, `lsass.exe`, `services.exe`, `csrss.exe`, etc.
  - Student / developer applications: `chrome.exe`, `code.exe`, `python.exe`, `cmd.exe`, `explorer.exe`, etc.
- **Function**: `modules.processes.is_system_process(pid, name) -> bool`. Deterministic, zero external dependencies, 100% testable.

---

## 6. Username and Privacy Handling (E-03)
- In `modules/processes.py`, process enumeration requests only `["pid", "name", "cpu_percent", "memory_percent", "status", "create_time"]`.
- `username` is **never requested** from `psutil`.
- Each dictionary sets `"user": None`.
- Serialized JSON payloads produce `"user": null`, matching backend schema `ProcessItem` where `user: str | None = None`.
- No Windows login name, active student username, or account identity is ever collected or transmitted.

---

## 7. Process Payload Limits (E-04)
- **Limits**:
  - `MAX_PROCESSES_INVENTORY = int(os.getenv("SLMS_MAX_PROCESSES", "500"))` (default 500).
  - `MAX_PROCESS_NAME_LENGTH = 255` (matches backend schema).
- **Deterministic Selection Policy**:
  1. Filter out kernel pseudo-processes first (`is_system_process`).
  2. Truncate process name: `clean_name = str(name).strip()[:MAX_PROCESS_NAME_LENGTH]`.
  3. Sort deterministically with resource prioritization:
     ```python
     processes.sort(
         key=lambda item: (
             -item["cpu_percent"],
             -item["memory_percent"],
             item["name"].casefold(),
             item["pid"],
         )
     )
     ```
     Resource hogs appear first; ties are broken by lowercase process name, then by PID.
  4. Truncate list to `MAX_PROCESSES_INVENTORY` (500 items).
- **Payload Size**: A saturated 500-process payload produces ~70–90 KB of JSON, orders of magnitude below the 20 MB outbox limit and well within FastAPI limits.

---

## 8. Software Cadence Design (E-05)
- **Configuration**:
  - `SOFTWARE_SCAN_INTERVAL = int(os.getenv("SLMS_SOFTWARE_INTERVAL", "900"))` (15 minutes, within approved 10–30 minute range).
- **Gating**:
  - `AgentRuntime.due_for_software_scan(now)` triggers on startup, then every 900 seconds.
  - On standard 20s cycles, `due_for_software_scan` is `False`.
  - `collect_all_data(include_software=due_sw)` bypasses software scanning when `due_sw` is `False`.
  - `SoftwareCache(ttl=900)` caches results so that even if `_collect_software()` is called directly, registry scanning only occurs upon TTL expiration.

---

## 9. Inventory Fingerprint & Delivery Semantics (E-06 Audit)
- **Algorithm**: `compute_software_fingerprint(software_list: list[dict]) -> str`:
  1. Normalizes fields: `name`, `version`, `publisher`, `install_date` (stripped of leading/trailing whitespace).
  2. Sorts items canonically by `(name.casefold(), version.casefold(), publisher.casefold(), install_date.casefold())`.
  3. Reordered equivalent lists produce identical canonical representations.
  4. Serializes to canonical JSON: `json.dumps(canonical_items, sort_keys=True, separators=(',', ':'))`.
  5. Computes SHA-256 hex digest.
  6. Empty list `[]` hashes deterministically to `sha256(b"[]")`.
- **Delivery Semantics (Semantic A - Last Successfully Delivered)**:
  - There is a strict, explicit distinction between:
    - `current_fingerprint`: Hash of currently scanned software on workstation.
    - `last_enqueued_fingerprint`: Hash of software placed into the Phase 3 outbox queue.
    - `last_delivered_fingerprint`: Hash of software successfully acknowledged/delivered by backend.
  - Stored persistent fingerprint represents **(A) last successfully acknowledged/delivered inventory**, NOT merely last enqueued inventory.
  - Calling an inventory "uploaded" merely because it was enqueued is strictly prohibited.
  - When enqueued, only `last_enqueued_fingerprint` is updated.
  - `last_delivered_fingerprint` is updated **only** when the outbox worker confirms delivery via `on_delivered` callback (HTTP 200 / 409 IDEMPOTENT_DUPLICATE) or upon direct upload HTTP 200.
  - **Dead-Letter Revival**: If network failure or backend downtime causes a software outbox record to reach `DEAD_LETTER` status, a subsequent software scan detects that the software is still present on the machine, invokes `outbox.requeue_dead_letter(record_id)` (resetting to PENDING with attempt_count 0), and ensures the inventory is never permanently suppressed.
  - **Pending Outbox Safety**: If a record is already `PENDING` or `PROCESSING` in the outbox, subsequent scans do not create duplicate outbox records; the existing record continues through the Phase 3 retry pipeline.
- **Persistence**:
  - Stored in `%PROGRAMDATA%\SLMS\data\software_state.json` (`SOFTWARE_STATE_FILE`).
  - Saved atomically via `tempfile.NamedTemporaryFile` + `os.replace` (crash-proof).
  - Corrupted or missing state file recovers cleanly without crashing.
  - Zero secrets/tokens are stored.

---

## 10. Software Upload Decision Flow
```
[Monitoring Loop (Every 20s)]
       │
       ▼
Is software scan due? (t - last_scan >= 900s)
       ├── NO  ──► Skip scan & skip upload (0 network/outbox traffic)
       └── YES ──► Scan Registry
                     │
                     ▼
             Scan Successful?
               ├── NO  ──► Preserve last delivered fingerprint; skip upload
               └── YES ──► Compute SHA-256 fingerprint
                             │
                             ▼
                     Fingerprint == last_delivered_fingerprint?
                       ├── YES ──► Inventory already delivered; skip upload
                       └── NO  ──► Changed or initial inventory
                                     │
                                     ▼
                           Outbox enabled?
                             ├── NO  ──► Direct upload HTTP POST
                             │             └── Success (200) ──► record_software_delivered()
                             │
                             └── YES ──► Check existing outbox record by idempotency key:
                                           ├── DELIVERED / None ──► Enqueue new record (PENDING)
                                           │                        record_software_enqueued()
                                           ├── PENDING/PROCESSING ─► Awaiting delivery; no duplicate
                                           └── DEAD_LETTER ───────► Requeue dead letter (PENDING)
                                                                    record_software_enqueued()
                                                                      │
                                                                      ▼
                                           [Outbox Worker Dispatches Event]
                                                                      │
                                                                      ▼
                                           Backend Ack / 200 OK / 409 Duplicate
                                                                      │
                                                                      ▼
                                           worker.on_delivered callback
                                                                      │
                                                                      ▼
                                           record_software_delivered()
                                           (Updates last_delivered_fingerprint)
```

---

## 11. Software Discovery Coverage (E-07)
- **Active Registry Sources**:
  - `HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall` (64-bit native applications).
  - `HKLM\SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall` (32-bit applications on 64-bit Windows).
- **Deduplication**: Case-insensitive identity matching on `(name, version)`.
- **Known Limitations**:
  1. *Per-User Installations*: Applications installed under `HKCU` (e.g. user-mode VS Code or Chrome) are not enumerated when running as `NT SERVICE\SLMSAgent` because user hives are unloaded when students are logged out.
  2. *Windows Store / MSIX / AppX Packages*: Packaged modern applications are managed via AppX APIs and are not registered in standard uninstall registry keys.
  3. *Portable Executables*: Standalone binaries that do not run an installer do not create registry entries.
- *Notice*: Registry scanning provides robust system-wide coverage for standard lab software, but is not claimed to provide 100% coverage of all modern package formats.

---

## 12. Outbox Compatibility
- Software outbox idempotency key: `f"software_{comp_id}_{fingerprint[:16]}"`. Stable across agent restarts and retries.
- Process outbox idempotency key: `f"processes_{comp_id}_{int(time.time())}"`.
- Outbox priority: `OutboxPriority.TELEMETRY` (FIFO queue with 5 attempts max).
- Outbox schema, migrations, retry policies, backpressure limits, and database transactions remain 100% intact.

---

## 13. Backend Compatibility
- No backend schema changes required.
- `ProcessUpload` (FastAPI / Pydantic) accepts `processes: list[ProcessItem]` with `max_length=5000` and `user: str | None = None`. Client sends <= 500 items with `user: None`.
- `SoftwareUpload` accepts `software: list[SoftwareItem]` with `max_length=2000`. Client sends normalized items matching the contract.
- All 23 backend tests pass without modification.

---

## 14. Files Changed
1. `client_agent/config.py`: Added `PROCESS_COLLECTION_INTERVAL`, `SOFTWARE_SCAN_INTERVAL`, `MAX_PROCESSES_INVENTORY`, `MAX_PROCESS_NAME_LENGTH`.
2. `client_agent/paths.py`: Added `SOFTWARE_STATE_FILE`, `USAGE_STATE_FILE`.
3. `client_agent/modules/processes.py`: Implemented system process filtering (`is_system_process`), payload limits, deterministic sorting, and privacy guarantees.
4. `client_agent/modules/software.py`: Added `compute_software_fingerprint`, atomic `load_software_state`, `save_software_state`, and coverage documentation.
5. `client_agent/core/collector.py`: Added `ProcessCache`, cadence parameters to `collect_all_data`, and cached process collection.
6. `client_agent/core/runtime.py`: Added cadence gating methods to `AgentRuntime`, fingerprint change detection in `upload_software`, and guarded process uploads.
7. `client_agent/main.py`: Delegated `upload_software` and `upload_processes` to `core.runtime`.

---

## 15. Files Created
1. `client_agent/tests/test_phase5_monitoring.py`: Dedicated 32-test test suite covering E-01 through E-07.
2. `docs/phases/PHASE_5_IMPLEMENTATION.md`: This comprehensive implementation report.

---

## 16. Files Deleted
- None.

---

## 17. Tests Added
32 new tests in `client_agent/tests/test_phase5_monitoring.py`:
- `TestProcessCadenceE01` (5 tests): Configuration validation, runtime cadence gating, non-suppression of other metrics, ProcessCache container mechanics, and collector cache reuse.
- `TestSystemProcessFilteringE02` (3 tests): System process identification, legitimate app retention, and `get_running_processes` output filtering.
- `TestProcessUsernamePrivacyE03` (2 tests): `user: None` in output dictionaries, `user: null` in JSON serialization.
- `TestProcessPayloadLimitsE04` (5 tests): Normal list retention, 500-process truncation, deterministic resource sorting, 255-char name truncation, and bounded payload size.
- `TestSoftwareCadenceE05` (3 tests): Configuration validation, runtime software cadence gating, and SoftwareCache reuse/expiration.
- `TestSoftwareDeliverySemanticsE06` (12 tests):
  1. First inventory: no previous fingerprint -> enqueue into outbox, records enqueued state.
  2. Same inventory after successful delivery -> skipped, zero outbox records added.
  3. Changed inventory -> enqueued to outbox.
  4. Changed inventory enqueued but delivery fails -> remains deliverable in outbox, never permanently suppressed.
  5. Changed inventory eventually delivered -> next identical scan skips.
  6. Agent restart with pending outbox event -> no permanent suppression, remains deliverable in outbox.
  7. Reordered equivalent inventory -> identical normalized SHA-256 fingerprint.
  8. Empty inventory -> valid 64-char SHA-256 fingerprint.
  9. Failed software scan -> does not modify last successfully delivered fingerprint.
  10. Exact Required Failure Scenario: inventory changes -> enqueued -> network failure -> DEAD_LETTER -> subsequent scan revives record to PENDING.
  11. Idempotency key stability across retries and restarts.
  12. Corrupted JSON state file safe recovery.
- `TestSoftwareDiscoveryCoverageE07` (2 tests): 64-bit and 32-bit registry path verification, and explicit documentation of known coverage limitations.

---

## 18. Full Regression Results
- **Client Agent Tests**: **174 passed** in 16.04s (Baseline: 142; +32 new tests).
- **Backend Tests**: **23 passed** in 1.33s.
- **Total Tests**: **197 passed, 0 failed**.
- **Alembic Status**: Sole head `a1b2c3d4e5f6 (head)`, 0 migrations added or modified.

---

## 19. Known Limitations
- Installed software discovery relies on HKEY_LOCAL_MACHINE uninstall registry keys. Modern AppX/MSIX packages and per-user HKCU applications are not currently captured from the Windows Service account.

---

## 20. Explicit Statement: Phase 6+ Scope Control
**Phase 6+ has NOT been started.**
Specifically:
- No issue lifecycle or hysteresis was implemented.
- No WebSocket redesign was performed.
- No logging retention or log rotation redesign was added.
- No broad testing framework or packaging was created.

---

## 21. Explicit Statement: Scheduler Refactor Deferral
**Full scheduler and worker architecture redesign is INTENTIONALLY DEFERRED to Phase 8.**
Phase 5 implemented the minimum necessary cadence gating inside the existing `AgentRuntime` loop using timestamp comparison methods (`due_for_process_collection` and `due_for_software_scan`). The runtime architecture remains clean, minimal, and fully recognizable.
