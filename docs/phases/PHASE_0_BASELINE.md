# Phase 0 Baseline Report: SLMS Client Agent Hardening

## Overview
This document establishes the verified architectural baseline for the Smart Lab Management System (SLMS) Client Agent. Every component, flow, and identified problem from A-01 through K-06 has been verified by direct inspection of the client agent and backend source code, execution diagnostics, and configuration inspection.

---

## Current Architecture

The client agent is currently a standalone desktop Python script designed to monitor Windows lab workstations and communicate with the SLMS FastAPI backend.

```
+-------------------------------------------------------------------------------+
|                               SLMS Client Agent                               |
|                                                                               |
|  +--------------------+    +--------------------+    +---------------------+  |
|  |     main.py        |--->|  core/collector.py |    |  server/            |  |
|  |  - Sequential Loop |    |  - 7 modules       |    |  communication.py   |  |
|  |  - Auth & Refresh  |    |  - safe_run()      |    |  - WebSocket Client |  |
|  +---------+----------+    +---------+----------+    +----------+----------+  |
|            |                         |                          |             |
|            v                         v                          v             |
|  +--------------------+    +--------------------+    +---------------------+  |
|  |   server/sender.py |    |  core/exporter.py  |    |  server/            |  |
|  |   - REST Uploads   |    |  - JSON Dump       |    |  command_handler.py |  |
|  +---------+----------+    +---------+----------+    +---------------------+  |
|            |                                                                  |
|            v                                                                  |
|  +--------------------+                                                       |
|  | Windows Keyring    |                                                       |
|  | - Credentials only |                                                       |
|  +--------------------+                                                       |
+------------|----------------------------------------------------|-------------+
             | REST (HTTP)                                        | WS (ws://)
             v                                                    v
+-------------------------------------------------------------------------------+
|                            SLMS FastAPI Backend                               |
|                                                                               |
|  - REST Routers: /api/agent, /api/metrics, /api/processes,                    |
|                  /api/software, /api/usage, /api/issues, /api/commands        |
|  - WebSocket Router: /ws/client/{computer_id}?token={token}                   |
|  - Database: SQLite (slms.db via SQLAlchemy)                                  |
+-------------------------------------------------------------------------------+
```

### Architectural Characteristics Identified
1. **Monolithic Procedural Loop**: `main.py` handles enrollment UI launching, token lifecycle, sequential data collection, 5 sequential REST network calls, uncoordinated WebSocket instantiation, JSON file dumping, and terminal console printing.
2. **Absence of Service Layer**: The agent executes as a standard interactive user process relying on `%APPDATA%\...\Startup`. If no student logs into the Windows workstation, the agent does not run.
3. **Absence of Resilient Outbox**: All REST network transmissions are immediate and synchronous in-memory attempts. Any network interruption, transient backend error (5xx), or computer sleep causes immediate telemetry and issue data loss.
4. **Unthrottled Uploads**: Software inventory (up to 2,000 items) and running process snapshots (hundreds of processes) are transmitted every 20 seconds, causing full database table deletes and inserts on SQLite for every cycle.

---

## Entry Points

1. **`main.py`**
   - **Type**: Interactive desktop CLI / GUI entry point.
   - **Execution**: `python main.py` or PyInstaller packaged binary `main.exe` / `SLMS_Client_Agent.exe`.
   - **Responsibilities**: Checks `is_enrolled()`. If false, launches Tkinter `show_enrollment_window()`. Authenticates via `authenticate()`, acquires `computer_id`, spawns background thread for `AgentWebSocketClient`, and enters `while True` loop with `time.sleep(20)`.

2. **`startup.py`**
   - **Type**: Helper script.
   - **Function**: `add_to_startup(exe_path=None)` copies the agent binary to the logged-in user's Windows Startup folder:
     `%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup`.

3. **`gui/enrollment_window.py`**
   - **Type**: Tkinter GUI dialog.
   - **Function**: `show_enrollment_window()` prompts the user for Server URL (pre-populated with `API_BASE_URL`) and Enrollment Key. Triggers `enroll()`.

---

## Authentication Flow

1. **Enrollment Phase**:
   - `gui/enrollment_window.py` captures `server_url` and `enrollment_key`.
   - Calls `server/enroll.py::enroll(enrollment_key, server_url)`.
   - Makes `POST {base_url}/api/agent/register` with device info (hostname, IP, MAC, OS name, OS version).
   - Backend validates enrollment key in database, binds/creates `Computer` and `AgentCredential`, generates a random `client_secret` (SHA-256 hashed in database), and returns:
     `{"computer_id": int, "agent_id": str, "client_secret": str}`.
   - Client stores `agent_id`, `client_secret`, and `computer_id` in Windows Credential Locker using the Python `keyring` library under service name `"SLMS"`.
   - **Gap**: The `server_url` parameter is **not persisted**. Subsequent calls fall back to `API_BASE_URL` in `config.py`.

2. **Runtime Authentication Phase**:
   - `server/auth.py::get_access_token()` reads `agent_id` and `client_secret` from `keyring`.
   - Makes `POST {API_BASE_URL}/api/agent/auth` with `{"agent_id": agent_id, "client_secret": client_secret}`.
   - Backend verifies secret via `secrets.compare_digest(hash_secret(value), hashed)`.
   - Backend issues a signed JWT (`type="agent"`, `sub=agent_id`, `computer_id=computer_id`) valid for 15 minutes (`expires_in: 900`).
   - Client caches this token in memory in `TokenHolder(access_token)`.
   - In `main.py`, the token is refreshed proactively every 12 minutes (`TOKEN_REFRESH_INTERVAL = 12 * 60`).
   - If an upload receives HTTP 401, `main.py` invokes `authenticate()` to renew the token and retries once.

---

## Enrollment Flow

```
[Administrator] ──> Generates Enrollment Key (e.g. SLMS-XXXX-XXXX-XXXX-XXXX)
       │
[Student PC / Agent]
       │
       ├──> is_enrolled() checks keyring: agent_id, client_secret, computer_id
       │
       ├── If missing ──> show_enrollment_window() (Tkinter GUI)
       │                    User inputs: Server URL & Key
       │                    POST /api/agent/register
       │                    Backend returns credentials
       │                    Saved to keyring (SERVER_NAME="SLMS")
       │
       └── If present ──> Proceed to Runtime Authentication
```

---

## REST Communication

All REST communication is handled via `requests` in `client_agent/server/sender.py` with `Authorization: Bearer <access_token>` headers:

| Endpoint | Method | Payload Data | Timeout | Client Call Site | Backend Service |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `/api/agent/register` | `POST` | `{"enrollment_key": str, "device": ComputerCreate}` | 10s | `server/enroll.py` | `agent_service.py` |
| `/api/agent/auth` | `POST` | `{"agent_id": str, "client_secret": str}` | 10s | `server/auth.py` | `agent_service.py` |
| `/api/metrics` | `POST` | `cpu_usage, ram_usage, disk_usage, network_sent, network_received` | 10s | `sender.py::send_metrics` | `metric_service.py` |
| `/api/software` | `POST` | `{"software": [SoftwareItem]}` (max 2000) | 30s | `sender.py::send_software_inventory` | `software_service.py` |
| `/api/processes` | `POST` | `{"processes": [ProcessItem]}` (max 5000) | 30s | `sender.py::send_process_inventory` | `process_service.py` |
| `/api/usage` | `POST` | `{"sessions": [UsageSessionCreate]}` (max 2000) | 30s | `sender.py::send_usage_sessions` | `usage_service.py` |
| `/api/issues/agent` | `POST` | `{"title": str, "description": str, "severity": str}` | 15s | `sender.py::send_issue` | `issue_service.py` |
| `/api/commands/{id}/result`| `POST` | `{"success": bool, "message": str}` | 10s | `communication.py::_send_command_result`| `command_service.py` |

---

## WebSocket Communication

Handled by `AgentWebSocketClient` in `client_agent/server/communication.py` using `websocket-client` (`websocket.WebSocketApp`):

- **Target URL**: `{WS_BASE_URL}/{computer_id}?token={token}`
- **Security & Contract Finding**: The JWT token is currently passed as a URL query parameter (`?token=...`). Backend `websocket_router.py` explicitly declares `token: str = Query(...)`. Removing the query parameter client-side only will break WebSocket connection. Migration requires coordinated backend support for header-based auth (`Authorization: Bearer <token>`) with backward-compatible query parameter fallback.
- **Heartbeat**: Background thread sends text `"ping"` every 20 seconds.
- **Backend Expectation**: `backend/app/websocket/timeout_checker.py` expects heartbeat within 75 seconds; marks computer offline if missing.
- **Command Handling**:
  - Receives JSON: `{"type": "command", "command_id": int, "command_type": str, "payload": str}`.
  - Allowed commands: `message`, `lock`, `restart`, `shutdown`.
  - Dispatches result via HTTP `POST /api/commands/{command_id}/result`.

---

## Monitoring Flow

Executed synchronously inside `main.py::main()` every 20 seconds:

1. **`core/collector.py::collect_all_data()`**:
   - `modules/system_info.py`: Reads OS, hostname, IP, MAC, username.
   - `modules/hardware.py`: Queries CPU (`interval=1` blocking 1 sec!), RAM, Disk, Boot time.
   - `modules/software.py`: Scans registry every 10 min, returns cache.
   - `modules/processes.py`: Iterates `psutil.process_iter()`, extracts PID, name, user, CPU, RAM.
   - `modules/usage.py`: Compares active process identities `(pid, name)` against `_ACTIVE_SESSIONS`. Completed processes emitted as sessions.
   - `modules/network.py`: Finds first non-127 IP, `uuid.getnode()` MAC, cumulative bytes sent/recv.
   - `modules/issues.py`: Evaluates RAM > 85%, Disk > 90%. Emits new issues.
2. **Sequential Uploads**:
   - `upload_metrics()`, `upload_software()`, `upload_processes()`, `upload_usage()`, `upload_issues()`.
3. **Telemetry Dump**:
   - `core/exporter.py`: Non-atomic file dump to `output/client_data.json` if `EXPORT_JSON=True`.
4. **Sleep**:
   - `time.sleep(20)`.

---

## Local Storage & Credential Architecture Considerations

1. **Windows Keyring Context Issue**:
   - The current agent runs in an interactive user session and stores credentials via `keyring` in the interactive user's Windows Credential Locker.
   - In Phase 2, a production Windows Service runs in Session 0 under `NT AUTHORITY\SYSTEM` or a dedicated Virtual Service Account (`NT SERVICE\SLMSService`).
   - Windows Credential Manager stores credentials on a per-user basis. Credentials saved by an interactive admin will not automatically be accessible to `LocalSystem` or the service account without explicit machine-scoped storage (e.g. DPAPI with `CRYPTPROTECT_LOCAL_MACHINE` or machine-level credential vault).
   - **Conclusion**: Phase 1 must not bind permanently to a user-scoped keyring path without preparing the machine-level abstraction needed by Phase 2.
2. **Directory Structure**:
   - Current: Files stored in `BASE_PATH` (application directory). In production, an installed application in `C:\Program Files\SLMS` cannot write logs or local state without administrator elevation.
   - Windows Standard: `%PROGRAMDATA%\SLMS\` (`logs\`, `data\`, `cache\`) protected with restrictive DACLs (SYSTEM and Administrators only).

---

## Logging

- Implemented in `client_agent/core/logger.py`.
- Outputs to `client_agent/logs/client.log` via standard `logging.FileHandler`.
- Lacks rotation and retention policies; logs grow unbounded.

---

## Windows Startup & Service Handling

- Currently relies on `client_agent/startup.py::add_to_startup()` copying the executable into `%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup`.
- Fails to start on boot without student login; halts on logout.

---

## Packaging

- Redundant spec files: `main.spec` and `SLMS_Client_Agent.spec`.
- PyInstaller unlisted in dependencies; lack of hidden imports for Windows services and security packages.

---

## Test Status & Diagnostics

### Pre-Hardening Test Status
1. `client_agent/tests/test_logger.py` had no assertions and failed to run due to unconfigured package import structure.
2. Pytest and pytest-mock have now been installed via `uv`.
3. A test harness configuration ([`client_agent/tests/conftest.py`](file:///d:/PC/slms1/Smart_lab_management_system/client_agent/tests/conftest.py)) was established, adding both workspace root and `client_agent` to `sys.path`.
4. A minimal smoke test suite ([`client_agent/tests/test_smoke.py`](file:///d:/PC/slms1/Smart_lab_management_system/client_agent/tests/test_smoke.py)) was created and executed:
   - **Result**: `3 passed in 0.06s` under `pytest 9.1.1`.
   - The test infrastructure is now operational.

---

## Problem Classification Matrix (A-01 through K-06)

Problems are classified into four precise categories:
- **CONFIRMED DEFECT**: Verifiable bug, crash, logic failure, or silent data loss in active code.
- **CONFIRMED REQUIREMENT GAP**: Missing feature or capability required for production compliance.
- **ARCHITECTURAL RECOMMENDATION**: Design enhancement for maintainability, modularity, or resilience.
- **PRODUCT DECISION REQUIRED**: Strategy requiring lab/stakeholder definition or contract choice.

| Code | Classification | Description | File / Location | Evidence / Verification Notes |
| :--- | :--- | :--- | :--- | :--- |
| **A-01** | **CONFIRMED REQUIREMENT GAP** | HTTP is allowed/default | `config.py:27` | Default `API_BASE_URL` is `http://127.0.0.1:8000`. Production must require HTTPS. |
| **A-02** | **CONFIRMED REQUIREMENT GAP** | WebSocket allows `ws://` | `config.py:112` | Default `WS_BASE_URL` is `ws://127.0.0.1:8000/ws/client`. Production must require WSS. |
| **A-03** | **CONFIRMED DEFECT** | WS JWT passed in URL | `server/communication.py:84` | URL constructed as `?token={token}`. Backend currently requires query param; requires coordinated migration. |
| **A-04** | **CONFIRMED REQUIREMENT GAP** | Enrollment accepts arbitrary URLs | `gui/enrollment_window.py:108` | Accepts arbitrary server URL without validation or enterprise domain whitelist. |
| **A-05** | **CONFIRMED DEFECT** | Server identity not persisted | `server/enroll.py:80-97` | Stores credentials in keyring but never persists `server_url`, causing agent to fall back to `API_BASE_URL`. |
| **A-06** | **CONFIRMED REQUIREMENT GAP** | TLS trust strategy undefined | `server/*.py` | Standard requests validation; needs enterprise CA configuration (`SLMS_CA_BUNDLE`) without verify=False. |
| **A-07** | **PRODUCT DECISION REQUIRED** | Signed update / integrity | Architecture | Determine whether agent needs self-update integrity checks or relies on enterprise distribution (SCCM/GPO/Intune). |
| **A-08** | **CONFIRMED REQUIREMENT GAP** | Sensitive local files unprotected | `paths.py:24-26` | Files stored in program directory without DPAPI protection or restrictive NTFS DACLs. |
| **A-09** | **CONFIRMED REQUIREMENT GAP** | Personal username collected | `system_info.py:64`, `processes.py:32` | Collects `getpass.getuser()` and process usernames; violates SRS student privacy constraint. |
| **A-10** | **CONFIRMED DEFECT** | Legacy auth/registration code | `server/registration.py`, `config.py:126`| Dead, truncated file `registration.py` and unused legacy config keys. Marked for deprecation. |
| **B-01** | **CONFIRMED REQUIREMENT GAP** | No real Windows Service | Project-wide | Agent runs only as foreground script; lacks Windows SCM integration. |
| **B-02** | **CONFIRMED DEFECT** | `startup.py` uses Startup folder | `startup.py:15-21` | Copies binary to user-specific `%APPDATA%\...\Startup`. |
| **B-03** | **CONFIRMED REQUIREMENT GAP** | Depends on user login | `startup.py`, `gui/enrollment_window.py` | Cannot start or operate without an interactive desktop user session. |
| **B-04** | **CONFIRMED REQUIREMENT GAP** | No service recovery policy | Project-wide | Lacks automatic restart-on-failure configuration. |
| **B-05** | **CONFIRMED REQUIREMENT GAP** | No service lifecycle commands | Project-wide | Missing install, start, stop, restart, uninstall CLI handlers. |
| **B-06** | **CONFIRMED DEFECT** | `MessageBoxW` in non-interactive | `server/command_handler.py:12` | `MessageBoxW(0, ...)` fails or hangs indefinitely in Windows Session 0. |
| **B-07** | **CONFIRMED REQUIREMENT GAP** | Privilege model undefined | Project-wide | Service account, required DACLs, and network rights are unconstrained. |
| **C-01** | **CONFIRMED REQUIREMENT GAP** | No durable upload queue | `server/sender.py` | Direct HTTP POST calls; payloads dropped on network/server failure. |
| **C-02** | **CONFIRMED DEFECT** | Issue uploads need durable retry | `main.py:440-475` | If HTTP POST fails, issue is permanently dropped from queue. |
| **C-03** | **CONFIRMED DEFECT** | Usage events need durable retry | `main.py:350-410` | If usage upload fails, sessions are permanently lost. |
| **C-04** | **CONFIRMED DEFECT** | Command results need retry | `server/communication.py:284` | If command result POST fails, result is discarded. |
| **C-05** | **CONFIRMED DEFECT** | Monitoring state lost on restart| `modules/usage.py:27`, `modules/issues.py:23` | Active tracking state is stored exclusively in in-memory global dictionaries/sets. |
| **C-06** | **CONFIRMED DEFECT** | Lack of idempotency | `server/sender.py`, Backend | Usage session retries create duplicate rows in backend `usage_sessions` table. |
| **C-07** | **CONFIRMED REQUIREMENT GAP** | Need bounded queue / backpressure| Project-wide | Outbox queue must enforce size limits and drop policy to protect disk. |
| **C-08** | **CONFIRMED REQUIREMENT GAP** | No defined retry policy | `main.py` | Lacks exponential backoff, priority levels (HIGH/MED/LOW), and dead-letter handling. |
| **D-01** | **CONFIRMED DEFECT** | Failures become valid zeros | `server/sender.py:48-64` | `hardware.get("cpu_usage", 0)` silently converts missing/failed metrics to 0%. |
| **D-02** | **ARCHITECTURAL RECOMMENDATION** | `safe_run` error handling coarse | `core/health.py:6-18` | Swallows all exceptions, returns `None`, discards structured error context. |
| **D-03** | **CONFIRMED DEFECT** | Network identity can be incorrect | `modules/network.py:37` | `uuid.getnode()` may return arbitrary virtual/random MAC; first non-127 IP is unreliable. |
| **D-04** | **CONFIRMED DEFECT** | Network logic duplicated | `modules/network.py` & `system_info.py` | Both independently implement non-loopback IP and MAC address resolution. |
| **D-05** | **CONFIRMED DEFECT** | MAC must identify active adapter| `modules/network.py:37`, `system_info.py:44`| Blindly uses `uuid.getnode()` instead of matching the active default route adapter. |
| **D-06** | **PRODUCT DECISION REQUIRED** | Network counters cumulative vs rate| `modules/network.py:42`, `system_metric.py:43`| Current contract sends cumulative bytes since boot. Clarify whether backend expects rate or cumulative. |
| **D-07** | **CONFIRMED DEFECT** | Software cache broken on empty | `core/collector.py:41-47` | If scan returns `[]`, `if _cached_software` is False, triggering repeated scans and cache wipe. |
| **D-08** | **CONFIRMED DEFECT** | CPU collection blocks 1 second | `modules/hardware.py:29` | `psutil.cpu_percent(interval=1)` synchronously blocks monitoring thread every cycle. |
| **D-09** | **CONFIRMED DEFECT** | Usage tracking uses PID + name | `modules/usage.py:91` | Keyed by `(pid, name.casefold())`; vulnerable to PID reuse collisions. |
| **D-10** | **CONFIRMED DEFECT** | Usage state only in memory | `modules/usage.py:27` | `_ACTIVE_SESSIONS` lost on process restart. |
| **D-11** | **CONFIRMED DEFECT** | Transient drop creates stop event| `modules/usage.py:168` | Single scan omission immediately terminates session, creating false stop and restart. |
| **D-12** | **PRODUCT DECISION REQUIRED** | Process vs Application tracking | `modules/usage.py` | Clarify whether usage should track all system processes or only interactive applications. |
| **E-01** | **CONFIRMED DEFECT** | Full process list uploaded 20s | `main.py:530` | Sends full process inventory every 20 seconds, wiping and re-inserting DB rows. |
| **E-02** | **PRODUCT DECISION REQUIRED** | System-process filtering rules | `modules/processes.py:11` | Establish approved whitelist/blacklist for system noise (svchost, idle, etc.). |
| **E-03** | **CONFIRMED REQUIREMENT GAP** | Process username collected | `modules/processes.py:32` | Gathers process username; violates student privacy and degrades WMI performance. |
| **E-04** | **PRODUCT DECISION REQUIRED** | Process payload limits | `modules/processes.py` | Define policy: top N by CPU/RAM, delta reporting, or hard limit (e.g. 50 processes). |
| **E-05** | **CONFIRMED DEFECT** | Software uploaded every 20s | `main.py:523` | Scanned every 10 min, but uploaded on every 20s loop iteration unconditionally. |
| **E-06** | **CONFIRMED REQUIREMENT GAP** | Software not change-aware | `main.py:296` | Uploads without checking if software inventory hash changed. |
| **E-07** | **PRODUCT DECISION REQUIRED** | Software discovery scope | `modules/software.py` | Scans HKLM 32/64-bit uninstall keys; decide whether HKCU user-level software is required. |
| **F-01** | **CONFIRMED REQUIREMENT GAP** | Issue state not decoupled | `modules/issues.py:23` | Only has `_ACTIVE_ISSUES` set; lacks DETECTED, QUEUED, SENT, ACK, RECOVERED. |
| **F-02** | **CONFIRMED DEFECT** | Failed issue upload suppresses | `modules/issues.py:99` | Added to `_ACTIVE_ISSUES` during detection; if upload fails, issue is permanently muted. |
| **F-03** | **PRODUCT DECISION REQUIRED** | Issue rules overlap backend | `modules/issues.py:68` | RAM/Disk rules hardcoded on client; backend `alert_service.py` evaluates same metrics. Decide rule authority. |
| **F-04** | **PRODUCT DECISION REQUIRED** | Debounce / hysteresis limits | `modules/issues.py` | Define threshold buffer (e.g. 2% hysteresis) and time debounce to prevent flapping. |
| **G-01** | **CONFIRMED DEFECT** | WS JWT in URL | `server/communication.py:84` | Passed in URL query parameter `?token=...`. |
| **G-02** | **CONFIRMED REQUIREMENT GAP** | WSS required in prod | `config.py:112` | Allows insecure `ws://`. |
| **G-03** | **CONFIRMED DEFECT** | Reconnect delay not reset | `server/communication.py:133` | Delay variable in outer loop is never reset by `_on_open()`. |
| **G-04** | **CONFIRMED DEFECT** | Token expiry coordination | `server/communication.py` | Uses static token lambda; doesn't trigger auth refresh on WS 4001 auth failure. |
| **G-05** | **CONFIRMED DEFECT** | Command result not durable | `server/communication.py:284` | HTTP failure drops command result. |
| **G-06** | **CONFIRMED REQUIREMENT GAP** | Missing observable WS states | `server/communication.py` | No state enum (CONNECTING, CONNECTED, AUTHENTICATING, etc.). |
| **H-01** | **ARCHITECTURAL RECOMMENDATION** | `main.py` overburdened | `main.py` | Decompose into RuntimeManager, Scheduler, CollectorManager, UploadManager, WebSocketManager, TokenManager, OutboxManager, ShutdownManager. |
| **H-02** | **ARCHITECTURAL RECOMMENDATION** | Sequential collection | `core/collector.py:53-118` | Decouple long-running collectors from fast system metrics. |
| **H-03** | **ARCHITECTURAL RECOMMENDATION** | Sequential REST uploads | `main.py:516-545` | Batch or decouple uploads via Outbox worker. |
| **H-04** | **CONFIRMED DEFECT** | Interval is `work + sleep(20)` | `main.py:575` | Loop drifts significantly; not fixed-interval target execution scheduling. |
| **H-05** | **ARCHITECTURAL RECOMMENDATION** | Unbounded workers/queues | `server/communication.py:140` | Use bounded thread pool for auxiliary tasks. |
| **I-01** | **CONFIRMED DEFECT** | No log rotation | `core/logger.py:14` | Plain `FileHandler`; will grow indefinitely. |
| **I-02** | **CONFIRMED REQUIREMENT GAP** | No log retention | `core/logger.py` | Missing retention limits (e.g. 5 files x 10MB). |
| **I-03** | **CONFIRMED REQUIREMENT GAP** | Non-standard data directories | `paths.py:24-26` | Uses application directory instead of `%PROGRAMDATA%\SLMS`. |
| **I-04** | **CONFIRMED REQUIREMENT GAP** | JSON export enabled by default | `config.py:95` | `EXPORT_JSON = True`. Should be opt-in diagnostic tool. |
| **I-05** | **CONFIRMED DEFECT** | JSON export not atomic | `core/exporter.py:14` | Standard `open("w")`; vulnerable to corruption. |
| **I-06** | **CONFIRMED REQUIREMENT GAP** | Telemetry retention undefined | `core/exporter.py` | Diagnostics history has no cleanup policy. |
| **I-07** | **CONFIRMED DEFECT** | Telemetry treated as source | `output/client_data.json` | Telemetry file tracked in git repository. |
| **J-01** | **CONFIRMED DEFECT** | Almost no automated tests | `tests/` | Only `test_logger.py` existed (ad-hoc print script). |
| **J-02** | **CONFIRMED DEFECT** | Tests lack assertions | `tests/test_logger.py` | Contained zero assertions. |
| **J-03** | **CONFIRMED DEFECT** | Broken package/import structure| `core/logger.py`, `tests/` | Resolved with `conftest.py` test harness setup. |
| **J-04..14**| **CONFIRMED REQUIREMENT GAP** | Missing test categories | Project-wide | Need suites for auth, outbox, collectors, WS, service, and load. |
| **K-01** | **CONFIRMED DEFECT** | Multiple PyInstaller spec files | `main.spec`, `SLMS_Client_Agent.spec` | Two diverging, incomplete spec files. |
| **K-02** | **ARCHITECTURAL RECOMMENDATION** | Dependencies inconsistent | `requirements.txt`, `pyproject.toml`, `uv.lock` | Define authoritative dependency source. |
| **K-03** | **ARCHITECTURAL RECOMMENDATION** | Package/version inconsistencies| `client_agent/` | Version mismatch (0.1.0 vs 1.0.0). |
| **K-04** | **CONFIRMED REQUIREMENT GAP** | `.gitignore` incomplete | `.gitignore`, `client_agent/.gitignore`| Fails to exclude logs, outbox database, and telemetry files. |
| **K-05** | **ARCHITECTURAL RECOMMENDATION** | Obsolete `data/agent.json` | `data/agent.json` | Verified unused. Deprecation documented. |
| **K-06** | **ARCHITECTURAL RECOMMENDATION** | Obsolete modules exist | `server/registration.py` | Truncated, unreferenced module. Deprecation documented. |

---

## File-by-File Change Map

| File | Current Role | Target Phase | Planned Modifications |
| :--- | :--- | :--- | :--- |
| `config.py` | Configuration constants | Phase 1, 8, 9 | Enforce HTTPS/WSS in production, add trusted server validation, add development bypass flag (`SLMS_ALLOW_INSECURE_HTTP`), support enterprise CA bundle (`SLMS_CA_BUNDLE`). |
| `paths.py` | Path resolution | Phase 1, 2, 9 | Define standard `%PROGRAMDATA%\SLMS\` paths (`logs`, `data`, `cache`) while preserving backward-compatible development fallback. |
| `startup.py` | Startup folder deployment | Phase 2 | Deprecate user Startup folder; replace with Windows Service installer/controller. |
| `service.py` *(New)* | Windows Service | Phase 2 | Background service architecture for non-interactive execution with restart recovery. |
| `storage/outbox.py` *(New)* | Durable local store | Phase 3 | SQLite-backed persistent priority outbox with deduplication, retry policy, backpressure, and TTL. |
| `core/health.py` | Result wrapper | Phase 4 | Introduce `CollectorResult` (SUCCESS, UNKNOWN, FAILED) with explicit error diagnostics. |
| `modules/hardware.py` | Hardware metrics | Phase 4 | Remove blocking `psutil.cpu_percent(interval=1)` (use non-blocking delta sampling). |
| `modules/network.py` | Network identity/metrics| Phase 4 | Canonicalize network identity, accurately bind to active default interface MAC/IP. Preserve cumulative counters contract. |
| `modules/system_info.py` | System metadata | Phase 1, 4 | Remove student Windows username collection (`A-09`). Remove duplicate network identity logic. |
| `modules/processes.py` | Process inventory | Phase 1, 5 | Remove process owner username collection (`A-09`, `E-03`). Filter system noise; limit payload size. |
| `modules/software.py` | Software inventory | Phase 5 | Fix empty scan cache bug; document registry limits. |
| `modules/usage.py` | App usage tracking | Phase 4, 5 | Robust process identity (`pid` + `create_time`), persist active state across restarts, debounce transient process drops. |
| `modules/issues.py` | Issue detection | Phase 6 | Decouple detection from delivery, introduce full state lifecycle, add hysteresis debounce. |
| `server/communication.py` | WebSocket client | Phase 1, 7 | Coordinated WebSocket auth migration (header with query param fallback), reconnect delay reset fix, durable command execution results. |
| `backend/app/routes/websocket_router.py` | Backend WS endpoint | Phase 1, 7 | Accept `Authorization: Bearer <token>` header with backward-compatible query param fallback. |
| `server/command_handler.py`| Remote commands | Phase 2, 7 | Replace interactive `MessageBoxW` with `WTSSendMessage` for Session 0 compatibility. |
| `server/enroll.py` | Enrollment | Phase 1 | Bind and persist server identity, enforce HTTPS, validate server certificates against enterprise CA or system trust store. |
| `server/auth.py` | Token authentication | Phase 1 | Enforce HTTPS, manage token lifecycle, integrate with Outbox retry. |
| `server/sender.py` | REST transmission | Phase 1, 3, 5 | Route uploads through durable outbox; prevent zero-metric coercion; software hash change detection. |
| `server/registration.py` | Legacy registration | Phase 1, 11 | Document deprecation and prove zero references. Do not delete until replacement is verified. |
| `data/agent.json` | Legacy file | Phase 1, 11 | Document deprecation. Do not delete until replacement is verified. |
| `core/logger.py` | Logging | Phase 9 | Implement `RotatingFileHandler` with configurable size/retention. |
| `core/exporter.py` | JSON export | Phase 9 | Implement atomic write (`.tmp` + `os.replace`), disable by default. |
| `main.py` | Main orchestrator | Phase 8 | Refactor into modular architecture: `RuntimeManager`, `Scheduler`, `CollectorManager`, `UploadManager`, `WebSocketManager`, `TokenManager`, `OutboxManager`, `ShutdownManager`. |
| `main.spec` / `SLMS_Client_Agent.spec` | PyInstaller build | Phase 11 | Unify into single canonical spec file with all required dependencies, hidden imports, and metadata. |
| `pyproject.toml` / `requirements.txt` | Dependencies | Phase 1, 10, 11 | Align dependencies, add `pytest`, `pytest-mock`, `pywin32`. |

---

## Backend Dependencies & Backward Compatibility Strategy

1. **WebSocket Authentication Coordinated Migration (`A-03`, `G-01`)**:
   - Current backend requirement: `token: str = Query(...)` in `backend/app/routes/websocket_router.py`.
   - Migration Strategy:
     1. Modify backend `websocket_router.py` to accept `token: str | None = Query(default=None)` and check `websocket.headers.get("authorization")` for `Bearer <token>`. If the header is missing, fall back to the query parameter `token`.
     2. Update client `server/communication.py` to send `Authorization: Bearer <token>` in WebSocket headers.
     3. Keep query parameter fallback during transition so older clients/scripts continue working without interruption.
     4. Write automated integration tests for both header-based and query-based WebSocket handshakes.
2. **Cumulative Network Bytes (`D-06`)**:
   - Backend `MetricUpload` schema requires `network_sent: float | None` and `network_received: float | None`.
   - The database stores these as raw cumulative floats without computing delta rates on backend. The client must continue sending cumulative bytes to preserve existing contract.
3. **Usage Session Deduplication (`C-06`)**:
   - Backend `UsageSessionCreate` does not currently require a client session UUID or idempotency key.
   - Client will track uploaded sessions in local SQLite store to ensure it never uploads the same session twice, ensuring client-side idempotency without breaking backend schema.
4. **Command Execution Result (`C-04`, `C-06`)**:
   - Backend returns `HTTP 409 Conflict` if a command result is resubmitted.
   - The client Outbox will treat HTTP 409 on command result submission as an acknowledgement that the server already has the result, successfully resolving the retry.

---

## 40-PC Scale & Performance Considerations

- **Measurable Performance Target**: Support for 40 concurrent client agents communicating with a single FastAPI + SQLite backend is an operational performance target.
- **Verification Strategy**: Rather than relying on static estimates, full verification of the 40-PC scale will be conducted via realistic automated load tests in **Phase 11**.
- Key metrics to measure in Phase 11:
  - Database lock contention on SQLite during concurrent metric, process, and usage writes.
  - WebSocket connection stability and memory footprint with 40 simultaneous persistent connections.
  - Heartbeat processing overhead and offline timeout checker CPU utilization.
  - Network bandwidth reduction achieved through change-aware software scanning and filtered process uploads.

---

## Identified Risks & Mitigations

1. **Windows Security Context Differences (Interactive vs Service)**:
   - *Risk*: Running as a Windows Service isolates the process from the user's interactive desktop. Credentials stored in the interactive user's Keyring vault are inaccessible to `LocalSystem` or a virtual service account.
   - *Mitigation*: Design an abstracted `CredentialStore` interface in Phase 1 that supports both interactive Keyring and machine-level storage (DPAPI with `CRYPTPROTECT_LOCAL_MACHINE`), deferring credential storage finalization until Phase 2 Windows Service architecture is established.
2. **TLS Certificate Trust in Lab Environments**:
   - *Risk*: Educational labs often use private internal PKI / self-signed root certificates. Strict TLS without custom CA configuration will fail in enterprise lab environments.
   - *Mitigation*: Support standard system CA trust store and provide an explicit `SLMS_CA_BUNDLE` setting for lab private root CAs. Never use `verify=False`.
