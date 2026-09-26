# Phase 0 Baseline Report: SLMS Client Agent Hardening

## Overview
This document establishes the verified architectural baseline for the Smart Lab Management System (SLMS) Client Agent. Every component, flow, and identified problem from A-01 through K-06 has been verified by direct static analysis of the client agent and backend source code, execution diagnostics, and configuration inspection.

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

### Architectural Deficiencies Identified
1. **Monolithic Procedural Loop**: `main.py` is responsible for enrollment UI launching, token lifecycle, sequential data collection, 5 sequential REST network calls, uncoordinated WebSocket instantiation, JSON file dumping, and terminal console printing.
2. **Absence of Service Layer**: The agent executes as a standard interactive user process relying on `%APPDATA%\...\Startup`. If no student logs into the Windows workstation, the agent does not run.
3. **Absence of Resilient Outbox**: All REST network transmissions are immediate and synchronous in-memory attempts. Any network interruption, transient backend error (5xx), or computer sleep causes immediate telemetry and issue data loss.
4. **Unthrottled Uploads**: Software inventory (up to 2,000 items) and running process snapshots (hundreds of processes) are transmitted every 20 seconds, causing full database table deletes and inserts on SQLite for every cycle across 40 clients.

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
   - **Flaw**: The `server_url` parameter is **not stored**. Subsequent calls fall back to `API_BASE_URL` in `config.py`.

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

### Critical Gaps in Enrollment
- Server URL is not persisted; agent relies on local environment or config default.
- No trust binding or TLS certificate pinning; any rogue server URL could be entered.
- Requires interactive desktop session (Tkinter dialog); fails completely in non-interactive Session 0 Windows Service mode.

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

### Critical Flaws in REST Flow
- **No Durable Outbox**: If any call fails, payload is dropped or retry fails permanently.
- **Silent Metric Corruption**: If hardware collector fails, `build_metric_payload` substitutes `0` for CPU/RAM/Disk.
- **Massive Inefficiency**: Full process list and unchanged software lists uploaded every 20 seconds.
- **Lack of Idempotency**: `/api/usage` creates duplicate records if network drops before HTTP response is received.

---

## WebSocket Communication

Handled by `AgentWebSocketClient` in `client_agent/server/communication.py` using `websocket-client` (`websocket.WebSocketApp`):

- **Target URL**: `{WS_BASE_URL}/{computer_id}?token={token}`
- **Security Vulnerability**: JWT token exposed as a URL query parameter (`?token=...`).
- **Heartbeat**: Background thread sends text `"ping"` every 20 seconds.
- **Backend Expectation**: `backend/app/websocket/timeout_checker.py` expects heartbeat within 75 seconds; marks computer offline if missing.
- **Command Handling**:
  - Receives JSON: `{"type": "command", "command_id": int, "command_type": str, "payload": str}`.
  - Passes to `server/command_handler.py::execute_command(command_type, payload)`.
  - Allowed commands: `message`, `lock`, `restart`, `shutdown`.
  - Dispatches result via HTTP `POST /api/commands/{command_id}/result`.
- **Bugs**:
  - Reconnect exponential backoff delay is never reset upon successful connection.
  - Interactive `MessageBoxW` used for `"message"` command (incompatible with Session 0 services).
  - Command execution result is not durable; lost if HTTP POST fails.

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
   - `upload_metrics()`
   - `upload_software()` (uploads cached software every 20s regardless of changes!)
   - `upload_processes()` (uploads full process table every 20s!)
   - `upload_usage()`
   - `upload_issues()`
3. **Telemetry Dump**:
   - `core/exporter.py`: Non-atomic file dump to `output/client_data.json` if `EXPORT_JSON=True`.
4. **Sleep**:
   - `time.sleep(20)` (actual loop cadence = 20s + ~1.5s execution time).

---

## Local Storage

1. **Windows Keyring**:
   - Stores `agent_id`, `client_secret`, `computer_id` under service `SLMS`.
   - Uses Windows Credential Manager.
2. **`paths.py` / Application Directory**:
   - `LOG_FOLDER`: `client_agent/logs/` (local to program directory).
   - `OUTPUT_FOLDER`: `client_agent/output/` (local to program directory).
   - `CREDENTIAL_FILE`: `client_agent/agent_credential.json` (legacy file path).
   - **Defect**: Violates Windows service design principles; a service in `C:\Program Files` cannot write to its install directory without elevated write permissions. Standard location is `%PROGRAMDATA%\SLMS`.

---

## Logging

- Implemented in `client_agent/core/logger.py`.
- Outputs to `client_agent/logs/client.log` via standard `logging.FileHandler`.
- **Defects**:
  - No log rotation (`RotatingFileHandler` or `TimedRotatingFileHandler` missing).
  - Log file will grow indefinitely.
  - No log retention policy.
  - Stored inside codebase working tree instead of `%PROGRAMDATA%\SLMS\logs`.

---

## Windows Startup & Service Handling

- **Current Implementation**: `client_agent/startup.py::add_to_startup()` copies script/exe to the user's Startup folder.
- **Defects**:
  - No Windows Service exists.
  - Does not run on computer boot; requires student/user login.
  - Terminates when user logs out.
  - No Windows Service Control Manager (SCM) integration, recovery actions, or service lifecycle commands.

---

## Packaging

- **Current Build Specs**:
  - `client_agent/main.spec`
  - `client_agent/SLMS_Client_Agent.spec`
- **Defects**:
  - Two redundant spec files.
  - Neither includes data files, runtime hooks, or hidden imports for win32/keyring.
  - PyInstaller is not listed in `pyproject.toml` or `requirements.txt`.
  - Dependencies are unpinned in `requirements.txt` and pinned in `uv.lock`.

---

## Test Status & Diagnostics

### Pre-Hardening Test Execution
1. **Running `python client_agent/tests/test_logger.py`**:
   - Result: **FAILED** (`ModuleNotFoundError: No module named 'client_agent'`).
   - Root Cause: Python package root not on `sys.path`.
2. **Running with `PYTHONPATH=.`**:
   - Result: **FAILED** (`ModuleNotFoundError: No module named 'config'`).
   - Root Cause: `logger.py` uses bare `from config import ...` instead of package relative or fully qualified imports.
3. **Running `unittest discover`**:
   - Result: `Ran 0 tests in 0.000s. NO TESTS RAN`.
   - Root Cause: No automated test cases exist in the repository; `test_logger.py` is merely an ad-hoc print script without assertions or test runners.
4. **Pytest Status**:
   - Not installed in virtual environment.
5. **Git Status & Working Tree**:
   - Tracked files include diagnostic telemetry `client_agent/output/client_data.json`.
   - Working tree had uncommitted `client_agent/uv.lock`. Dedicated branch `feature/client-agent-hardening` created.

---

## Problem Verification Matrix (A-01 through K-06)

Every problem has been mapped to concrete files and code locations and categorized:

| Code | Status | Description | File / Location | Evidence / Verification Notes |
| :--- | :--- | :--- | :--- | :--- |
| **A-01** | **CONFIRMED** | HTTP is allowed/default | `config.py:27` | Default `API_BASE_URL` is `http://127.0.0.1:8000`. No HTTPS enforcement. |
| **A-02** | **CONFIRMED** | WebSocket allows `ws://` | `config.py:112` | Default `WS_BASE_URL` is `ws://127.0.0.1:8000/ws/client`. No WSS requirement. |
| **A-03** | **CONFIRMED** | WS JWT passed in URL | `server/communication.py:84` | URL constructed as `f"{WS_BASE_URL}/{self.computer_id}?token={token}"`. |
| **A-04** | **CONFIRMED** | Enrollment accepts arbitrary URLs | `gui/enrollment_window.py:108` | Accepts any text in `server_entry` without validation, domain whitelist, or scheme check. |
| **A-05** | **CONFIRMED** | Server identity not persisted | `server/enroll.py:80-97` | Stores credentials in keyring but never persists `server_url`, CA pin, or server identity. |
| **A-06** | **CONFIRMED** | TLS trust strategy undefined | `server/*.py` | `requests` calls use default trust; no separation of dev/prod cert validation or custom CA. |
| **A-07** | **CONFIRMED** | No signed update/integrity | Project-wide | Zero update mechanisms or binary hash/integrity checks exist. |
| **A-08** | **CONFIRMED** | Sensitive local files unprotected | `paths.py:24-26` | Output, logs, credentials in application directory without DPAPI or ACL restrictions. |
| **A-09** | **CONFIRMED** | Personal username collected | `modules/system_info.py:64`, `modules/processes.py:32` | Collects `getpass.getuser()` and process owner usernames; violates SRS student privacy. |
| **A-10** | **CONFIRMED** | Legacy auth/registration code | `server/registration.py`, `config.py:126-130` | Incomplete dead file `registration.py` and unused legacy config variables. |
| **B-01** | **CONFIRMED** | No real Windows Service | Project-wide | Agent runs only as foreground script; no `win32service` or SCM service code exists. |
| **B-02** | **CONFIRMED** | `startup.py` uses Startup folder | `startup.py:15-21` | Targets `%APPDATA%\...\Startup`, which is user-session bound. |
| **B-03** | **CONFIRMED** | Depends on user login | `startup.py`, `gui/enrollment_window.py` | Cannot start or operate without an interactive user login session. |
| **B-04** | **CONFIRMED** | No service recovery policy | Project-wide | No SCM configuration or crash recovery mechanism defined. |
| **B-05** | **CONFIRMED** | No service lifecycle commands | Project-wide | Missing install, start, stop, restart, uninstall CLI handlers. |
| **B-06** | **CONFIRMED** | `MessageBoxW` in non-interactive | `server/command_handler.py:12` | `MessageBoxW(0, ...)` fails or hangs in Windows Session 0 (service session). |
| **B-07** | **CONFIRMED** | Privilege model undefined | Project-wide | Service account, required DACLs, and network rights are undocumented and unconstrained. |
| **C-01** | **CONFIRMED** | No durable upload queue | `server/sender.py` | Direct HTTP POST calls; payloads dropped on network/server failure. |
| **C-02** | **CONFIRMED** | Issue uploads need durable retry | `main.py:440-475` | If HTTP POST fails, issue is not queued for retry. |
| **C-03** | **CONFIRMED** | Usage events need durable retry | `main.py:350-410` | If usage upload fails, sessions are permanently lost. |
| **C-04** | **CONFIRMED** | Command results need retry | `server/communication.py:284` | If command result POST fails, result is discarded. |
| **C-05** | **CONFIRMED** | Monitoring state lost on restart| `modules/usage.py:27`, `modules/issues.py:23` | Active tracking state is stored exclusively in in-memory global dictionaries/sets. |
| **C-06** | **CONFIRMED** | Lack of idempotency | `server/sender.py`, Backend | Usage session retries create duplicate rows in backend `usage_sessions` table. |
| **C-07** | **CONFIRMED** | Need bounded queue / backpressure| Project-wide | No local storage mechanism; persistent queue must enforce storage limits and FIFO/drop policy. |
| **C-08** | **CONFIRMED** | No defined retry policy | `main.py` | Only immediate single 401 retry; lacks exponential backoff, priority, and dead-letter handling. |
| **D-01** | **CONFIRMED** | Failures become valid zeros | `server/sender.py:48-64` | `hardware.get("cpu_usage", 0)` silently converts missing/failed metrics to 0%. |
| **D-02** | **CONFIRMED** | `safe_run` error handling coarse | `core/health.py:6-18` | Swallows all exceptions, returns `None`, discards structured error context. |
| **D-03** | **CONFIRMED** | Network identity can be incorrect | `modules/network.py:37` | `uuid.getnode()` may return arbitrary virtual/random MAC; first non-127 IP is unreliable. |
| **D-04** | **CONFIRMED** | Network logic duplicated | `modules/network.py` & `system_info.py` | Both independently implement non-loopback IP and MAC address resolution. |
| **D-05** | **CONFIRMED** | MAC must identify active adapter| `modules/network.py:37`, `system_info.py:44`| Blindly uses `uuid.getnode()` instead of matching the active default route adapter. |
| **D-06** | **CONFIRMED** | Network counters cumulative | `modules/network.py:42`, `backend/models/system_metric.py:43` | `psutil.net_io_counters()` is cumulative since boot. Backend schema stores Float. Must retain contract. |
| **D-07** | **CONFIRMED** | Software cache broken on empty | `core/collector.py:41-47` | If scan returns `[]`, `if _cached_software` is False, triggering repeated scans and cache wipe. |
| **D-08** | **CONFIRMED** | CPU collection blocks 1 second | `modules/hardware.py:29` | `psutil.cpu_percent(interval=1)` synchronously blocks monitoring thread every cycle. |
| **D-09** | **CONFIRMED** | Usage tracking uses PID + name | `modules/usage.py:91` | Keyed by `(pid, name.casefold())`; vulnerable to PID reuse collisions. |
| **D-10** | **CONFIRMED** | Usage state only in memory | `modules/usage.py:27` | `_ACTIVE_SESSIONS` lost on process restart. |
| **D-11** | **CONFIRMED** | Transient drop creates stop event| `modules/usage.py:168` | Single scan omission immediately terminates session, creating false stop and restart. |
| **D-12** | **CONFIRMED** | Ambiguous process vs app tracking| `modules/usage.py` | Tracks all background system processes as user applications. |
| **E-01** | **CONFIRMED** | Full process list uploaded 20s | `main.py:530` | Sends full process inventory every 20 seconds, wiping and re-inserting DB rows. |
| **E-02** | **CONFIRMED** | System-process noise unfiltered | `modules/processes.py:11` | Emits background svchost, runtime brokers, system idle, etc. |
| **E-03** | **CONFIRMED** | Process username collected | `modules/processes.py:32` | Gathers process username; violates student privacy and degrades WMI performance. |
| **E-04** | **CONFIRMED** | Process payload size unconstrained| `modules/processes.py` | Transmits hundreds of unfiltered process dicts in a single request. |
| **E-05** | **CONFIRMED** | Software uploaded every 20s | `main.py:523` | Scanned every 10 min, but uploaded on every 20s loop iteration unconditionally. |
| **E-06** | **CONFIRMED** | Software not change-aware | `main.py:296` | Uploads without checking if software inventory hash changed. |
| **E-07** | **CONFIRMED** | Software discovery limitations | `modules/software.py` | Scans HKLM 32/64-bit uninstall keys; lacks HKCU user installs or Store app documentation. |
| **F-01** | **CONFIRMED** | Issue state not decoupled | `modules/issues.py:23` | Only has `_ACTIVE_ISSUES` set; lacks DETECTED, QUEUED, SENT, ACK, RECOVERED. |
| **F-02** | **CONFIRMED** | Failed issue upload suppresses | `modules/issues.py:99` | Added to `_ACTIVE_ISSUES` during detection; if upload fails, issue is permanently muted. |
| **F-03** | **CONFIRMED** | Issue rules overlap backend | `modules/issues.py:68` | RAM/Disk rules hardcoded on client; backend `alert_service.py` evaluates same metrics. |
| **F-04** | **CONFIRMED** | No hysteresis/debounce | `modules/issues.py` | Fluctuating metric across threshold generates rapid issue flapping. |
| **G-01** | **CONFIRMED** | WS JWT in URL | `server/communication.py:84` | Passed in URL query parameter `?token=...`. |
| **G-02** | **CONFIRMED** | WSS required in prod | `config.py:112` | Allows insecure `ws://`. |
| **G-03** | **CONFIRMED** | Reconnect delay not reset | `server/communication.py:133` | Delay variable in outer loop is never reset by `_on_open()`. |
| **G-04** | **CONFIRMED** | Token expiry coordination | `server/communication.py` | Uses static token lambda; doesn't trigger auth refresh on WS 4001 auth failure. |
| **G-05** | **CONFIRMED** | Command result not durable | `server/communication.py:284` | HTTP failure drops command result. |
| **G-06** | **CONFIRMED** | Missing observable WS states | `server/communication.py` | No state enum (CONNECTING, CONNECTED, AUTHENTICATING, etc.). |
| **H-01** | **CONFIRMED** | `main.py` overburdened | `main.py` | Single file handles UI, auth, scheduling, collectors, 5 uploads, export, console. |
| **H-02** | **CONFIRMED** | Sequential collection | `core/collector.py:53-118` | All collectors execute synchronously on main thread. |
| **H-03** | **CONFIRMED** | Sequential REST uploads | `main.py:516-545` | 5 HTTP requests executed back-to-back in loop. |
| **H-04** | **CONFIRMED** | Interval is `work + sleep(20)` | `main.py:575` | Loop drifts significantly; not fixed-interval target execution scheduling. |
| **H-05** | **CONFIRMED** | Unbounded workers/queues | `server/communication.py:140` | Spawns unmanaged daemon threads (`_ping_loop`). |
| **I-01** | **CONFIRMED** | No log rotation | `core/logger.py:14` | Plain `FileHandler`; will grow indefinitely. |
| **I-02** | **CONFIRMED** | No log retention | `core/logger.py` | No cleanup or retention limits. |
| **I-03** | **CONFIRMED** | Non-standard data directories | `paths.py:24-26` | Uses application directory instead of `%PROGRAMDATA%\SLMS`. |
| **I-04** | **CONFIRMED** | JSON export enabled by default | `config.py:95` | `EXPORT_JSON = True`. Writes disk telemetry every 20s. |
| **I-05** | **CONFIRMED** | JSON export not atomic | `core/exporter.py:14` | Standard `open("w")`; vulnerable to corruption. |
| **I-06** | **CONFIRMED** | Telemetry retention undefined | `core/exporter.py` | Overwrites single file, but diagnostics history has no retention policy. |
| **I-07** | **CONFIRMED** | Telemetry treated as source | `output/client_data.json` | Telemetry file tracked in git repository. |
| **J-01** | **CONFIRMED** | Almost no automated tests | `tests/` | Only `test_logger.py` exists (a 6-line print script). |
| **J-02** | **CONFIRMED** | Tests lack assertions | `tests/test_logger.py` | Contains zero assertions or TestCase classes. |
| **J-03** | **CONFIRMED** | Broken package/import structure| `core/logger.py`, `tests/` | Absolute imports fail when running tests from repo root or package root. |
| **J-04..14**| **CONFIRMED** | Missing test categories | Project-wide | Need suites for auth, outbox, collectors, WS, service, and 40-PC scenarios. |
| **K-01** | **CONFIRMED** | Multiple PyInstaller spec files | `main.spec`, `SLMS_Client_Agent.spec` | Two diverging, incomplete spec files. |
| **K-02** | **CONFIRMED** | Dependencies inconsistent | `requirements.txt`, `pyproject.toml`, `uv.lock` | Unpinned in requirements.txt, pinned in uv.lock, PyInstaller missing. |
| **K-03** | **CONFIRMED** | Package/version inconsistencies| `client_agent/` | Version mismatch (0.1.0 vs 1.0.0). |
| **K-04** | **CONFIRMED** | `.gitignore` incomplete | `.gitignore`, `client_agent/.gitignore`| Fails to exclude logs, outbox database, and telemetry files. |
| **K-05** | **CONFIRMED** | Obsolete `data/agent.json` | `data/agent.json` | Verified unused anywhere in the codebase. |
| **K-06** | **CONFIRMED** | Obsolete modules exist | `server/registration.py` | Truncated, unreferenced module. |

---

## File-by-File Change Map

| File | Current Role | Target Phase | Planned Modifications |
| :--- | :--- | :--- | :--- |
| `config.py` | Configuration constants | Phase 1, 8, 9 | Enforce HTTPS/WSS in production, add trusted server validation, configurable data paths, disable debug JSON export by default. |
| `paths.py` | Path resolution | Phase 1, 2, 9 | Move data, logs, cache, outbox database to `%PROGRAMDATA%\SLMS\` with secure DACLs. |
| `startup.py` | Startup folder deployment | Phase 2 | Deprecate user Startup folder; replace with Windows Service installer/controller. |
| `service.py` *(New)* | Windows Service | Phase 2 | `win32serviceutil` implementation for background non-interactive execution with restart recovery. |
| `storage/outbox.py` *(New)* | Durable local store | Phase 3 | SQLite-backed persistent priority outbox with deduplication, retry policy, backpressure, and TTL. |
| `core/health.py` | Result wrapper | Phase 4 | Introduce `CollectorResult` (SUCCESS, UNKNOWN, FAILED) with explicit error diagnostics. |
| `modules/hardware.py` | Hardware metrics | Phase 4 | Remove blocking `psutil.cpu_percent(interval=1)` (use non-blocking delta sampling). |
| `modules/network.py` | Network identity/metrics| Phase 4 | Canonicalize network identity, accurately bind to active default interface MAC/IP. Preserve cumulative counters contract. |
| `modules/system_info.py` | System metadata | Phase 4, 9 | Remove duplicated network logic; remove Windows username collection (privacy). |
| `modules/processes.py` | Process inventory | Phase 5, 9 | Remove process owner username collection; filter system noise; limit payload size. |
| `modules/software.py` | Software inventory | Phase 5 | Fix empty scan cache bug; document registry limits. |
| `modules/usage.py` | App usage tracking | Phase 4, 5 | Robust process identity (`pid` + `create_time`), persist active state across restarts, debounce transient process drops. |
| `modules/issues.py` | Issue detection | Phase 6 | Decouple detection from delivery, introduce full state lifecycle, add hysteresis debounce. |
| `server/communication.py` | WebSocket client | Phase 1, 7 | Remove JWT from URL (compatible migration), add observable connection state machine, fix reconnect delay reset, durable command execution results. |
| `server/command_handler.py`| Remote commands | Phase 2, 7 | Replace interactive `MessageBoxW` with `WTSSendMessage` for Session 0 compatibility. |
| `server/enroll.py` | Enrollment | Phase 1 | Bind and persist server identity, enforce HTTPS, validate server certificates. |
| `server/auth.py` | Token authentication | Phase 1 | Enforce HTTPS, manage token lifecycle, integrate with Outbox retry. |
| `server/sender.py` | REST transmission | Phase 1, 3, 5 | Route uploads through durable outbox; prevent zero-metric coercion; software hash change detection. |
| `server/registration.py` | Legacy registration | Phase 1 | Safely decommission after confirming zero active references. |
| `data/agent.json` | Legacy file | Phase 11 | Safely decommission. |
| `core/logger.py` | Logging | Phase 9 | Implement `RotatingFileHandler` with configurable size/retention in `%PROGRAMDATA%\SLMS\logs`. |
| `core/exporter.py` | JSON export | Phase 9 | Implement atomic write (`.tmp` + `os.replace`), disable by default. |
| `main.py` | Main orchestrator | Phase 8 | Refactor into modular architecture: `RuntimeManager`, `Scheduler`, `CollectorManager`, `UploadManager`, `WebSocketManager`, `TokenManager`, `OutboxManager`, `ShutdownManager`. |
| `main.spec` / `SLMS_Client_Agent.spec` | PyInstaller build | Phase 11 | Unify into single canonical spec file with all required dependencies, hidden imports, and metadata. |
| `pyproject.toml` / `requirements.txt` | Dependencies | Phase 1, 10, 11 | Align dependencies, add `pytest`, `pytest-mock`, `pywin32`. |

---

## Backend Dependencies & Backward Compatibility

1. **WebSocket Token Handshake (`A-03`, `G-01`)**:
   - Backend `backend/app/routes/websocket_router.py`:
     ```python
     @router.websocket("/ws/client/{computer_id}")
     async def client_websocket(websocket: WebSocket, computer_id: int, token: str = Query(...)):
     ```
   - **Contract Risk**: Backend strictly requires `token` as a URL query parameter (`Query(...)`). If the client omits `?token=...`, FastAPI rejects the WebSocket handshake before connection.
   - **Strategy**: Phase 1 foundation will prepare secure token transport. If backend change is coordinated, update backend `websocket_router.py` to accept token via either header `Authorization: Bearer <token>` or first-message handshake `{"type": "auth", "token": "..."}`, while keeping query parameter support as a backward-compatible fallback.
2. **Cumulative Network Bytes (`D-06`)**:
   - Backend `MetricUpload` schema requires `network_sent: float | None` and `network_received: float | None`.
   - The database stores these as raw cumulative floats without computing delta rates on backend. The client must continue sending cumulative bytes to preserve existing behavior.
3. **Usage Session Deduplication (`C-06`)**:
   - Backend `UsageSessionCreate` does not currently require a client session UUID or idempotency key.
   - Client will track uploaded sessions in local SQLite store to ensure it never uploads the same session twice, ensuring client-side idempotency without breaking backend schema.
4. **Command Execution Result (`C-04`, `C-06`)**:
   - Backend returns `HTTP 409 Conflict` if a command result is resubmitted.
   - The client Outbox will treat HTTP 409 on command result submission as an acknowledgement that the server already has the result, successfully resolving the retry.

---

## Identified Risks & Mitigations

1. **Windows Session 0 Isolation**:
   - *Risk*: Running as a Windows Service isolates the process from the user's interactive desktop. `MessageBoxW` and Tkinter enrollment will fail.
   - *Mitigation*: Separate enrollment into an administrative setup tool / CLI command (`slms-agent enroll ...`), and replace `MessageBoxW` with Windows Terminal Services API (`wtsapi32.dll` `WTSSendMessage`) to broadcast messages to active user sessions.
2. **Keyring Access in Windows Service Context**:
   - *Risk*: `keyring` (Windows Credential Manager) behavior differs when running under `LocalSystem` vs a dedicated user account.
   - *Mitigation*: Verify Windows Credential Manager behavior under the service account; provide DPAPI-encrypted file fallback in `%PROGRAMDATA%\SLMS\credentials\` if Keyring is inaccessible in Session 0.
3. **High Database Write Load with 40 PCs**:
   - *Risk*: 40 PCs uploading full process lists and software lists every 20s overwhelms SQLite backend with concurrent table locks.
   - *Mitigation*: Hash-based software change detection (upload only on change or hourly heartbeat), and filter processes to top resource consumers, dramatically reducing payload and DB churn.

---

## Phase 1 Implementation Plan: Security and Transport Foundation

### Goals
Harden communication security and local credential/identity storage without breaking existing working functionality:
1. **Enforce HTTPS / WSS in Production**:
   - Add scheme validation in `config.py` and `server/enroll.py`.
   - Disallow plaintext HTTP/WS unless an explicit `SLMS_DEV_INSECURE=1` or `SLMS_ALLOW_HTTP=1` environment flag is present for local test environments.
2. **Controlled Trusted Server Configuration (`A-04`, `A-05`)**:
   - Persist the validated server URL and server identity upon enrollment.
   - Store server configuration in secure configuration store rather than falling back to defaults.
3. **TLS Validation & Trust Strategy (`A-06`)**:
   - Enforce strict TLS certificate verification.
   - Support optional custom CA certificate bundle path (`SLMS_CA_BUNDLE`) for lab enterprise root CAs.
   - Explicitly forbid `verify=False`.
4. **Local Data Directory & Permission Hardening (`A-08`, `I-03`)**:
   - Update `paths.py` to route production logs, data, and cache to `%PROGRAMDATA%\SLMS`.
   - Implement restrictive Windows ACLs (SYSTEM and Administrators only).
5. **Privacy Hardening (`A-09`, `E-03`)**:
   - Remove student Windows username collection from `modules/system_info.py`.
   - Remove process username collection from `modules/processes.py`.
6. **Decommission Obsolete Code (`A-10`, `K-05`)**:
   - Remove `client_agent/server/registration.py` and legacy config keys.
   - Remove unused `client_agent/data/agent.json`.
7. **Package & Import Structure Fix (`J-03`)**:
   - Standardize package imports so the agent can be executed both as an installed package and as standalone scripts.
8. **Automated Security & Transport Tests (`J-04`, `J-05`)**:
   - Introduce pytest suite testing TLS enforcement, URL validation, credential storage, and privacy stripping.
