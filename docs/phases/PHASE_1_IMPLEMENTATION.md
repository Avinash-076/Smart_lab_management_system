# Phase 1 Implementation & Verification Report: Security and Transport Foundation

## Overview
Phase 1 establishes the hardened security and transport foundation for the SLMS Client Agent. All changes have been implemented with strict backward compatibility, without altering existing backend database schemas, without premature credential migration to non-interactive accounts, and without breaking development workflows.

---

## 1. Verified Fixes & Architecture Changes

### A. Authoritative Server URL Binding (`client_agent/config.py`)
- **Production Precedence**: When an agent is enrolled, the persisted enrolled server URL stored in the credential store is strictly authoritative in production (`is_insecure_http_allowed() == False`).
- **Protection Against Silent Redirection**: If `SLMS_API_URL` is set in production and conflicts with the persisted enrolled server URL, `get_api_base_url()` raises a `RuntimeError` to prevent silent redirection or rogue server hijacking.
- **Explicit Development Override**: In development mode (`SLMS_DEV_MODE=1` or `SLMS_ALLOW_INSECURE_HTTP=1`), explicit `SLMS_API_URL` overrides are permitted for developer testing.
- **WebSocket Endpoint Protection**: In production, `get_ws_base_url()` derives the `wss://` endpoint directly from the authoritative REST base URL and rejects conflicting `SLMS_WS_URL` overrides.
- **Regression Tests**: Added `TestServerUrlBinding` in `client_agent/tests/test_security.py` proving that enrolled production agents cannot be overridden or hijacked.

### B. WebSocket Authentication Migration (`backend/app/routes/websocket_router.py`)
- **Target Production Architecture**: WebSocket client connects to `/ws/client/{computer_id}` without any JWT or query string parameters. Token is transmitted exclusively via `Authorization: Bearer <token>` in the HTTP Upgrade handshake header.
- **Header Parsing**: Route inspects `websocket.headers.get("authorization")`, safely parsing case-insensitive `Bearer ` tokens.
- **Query Parameter Fallback**: The query token parameter is optional (`token: str | None = Query(default=None)`), serving strictly as a temporary backward-compatible fallback for older clients during migration. A header-only connection reaches authentication without requiring query parameters.

### C. Real Network WebSocket Handshake Verification
- **Real Library & Network Handshake**: Verified using the actual `websocket-client` library (v1.9.2) connecting over standard TCP sockets to a live Uvicorn/FastAPI backend server in `backend/tests/test_websocket_real_handshake.py`.
- **Verified Invariants**:
  - Connection URL strictly contains no JWT and no `?token=` query parameter (`assert "?token=" not in url`).
  - `Authorization: Bearer <token>` is sent in handshake headers and accepted by backend (HTTP 101 Switching Protocols).
  - Missing token is rejected with HTTP 403 Forbidden.
  - Invalid token is rejected with HTTP 403 Forbidden.
  - Legacy `?token=` query parameter connects during transitional migration.
  - `websocket-client` TLS configuration (`sslopt={"ca_certs": ...}`) enforces `cert_reqs: ssl.CERT_REQUIRED` and `check_hostname: True`.

### D. Comprehensive TLS Security Scan
- Exhaustive ripgrep audit across `client_agent/`:
  - `verify=False`: **Zero occurrences** found.
  - `ssl.CERT_NONE` / `CERT_NONE`: **Zero occurrences** found.
  - `check_hostname=False`: **Zero occurrences** found.
  - Insecure SSL contexts: **Zero occurrences** found.
- Strict certificate validation is enforced by default (`get_tls_verify_parameter()` returns `True` or the explicit enterprise CA path).
- Enterprise CA root bundles can be configured via `SLMS_CA_BUNDLE` (with validation that the file exists).
- No certificate pinning was introduced.

### E. Telemetry Contract & Student Privacy
- **Student Privacy**:
  - `client_agent/modules/system_info.py`: Personal Windows username (`getpass.getuser()`) is not collected.
  - `client_agent/modules/processes.py`: Process owner username resolution is removed, explicitly setting `"user": None`.
- **Backend Schema Verification**:
  - `ComputerCreate` schema does not require or define any personal username field.
  - `ProcessItem` schema defines `user: str | None = Field(default=None)` and SQLite `processes.user` column is nullable.
  - End-to-end telemetry tests in `backend/tests/test_telemetry_contract.py` verify that `POST /api/processes` accepts `user: None` payloads.
  - Cumulative network byte counters (`network_sent`, `network_received`) retain their exact counter semantics without modification.

### F. Credential Store Abstraction (`client_agent/core/credentials.py`)
- Created `BaseCredentialStore` abstract interface (`get_credential`, `set_credential`, `delete_credential`, `is_enrolled`, `get_enrolled_credentials`, `save_enrolled_credentials`, `get_server_url`, `set_server_url`).
- Preserved `KeyringCredentialStore` backed by Windows Credential Manager for interactive operation, with configuration fallback to `%PROGRAMDATA%\SLMS\config\server_config.json`.
- Machine-level DPAPI storage and service account credential architecture are deferred to Phase 2.

### G. ProgramData Path Layout (`client_agent/paths.py`)
- Production paths standardized to `%PROGRAMDATA%\SLMS\` (`logs`, `output`, `config`, `cache`).
- In development mode (`SLMS_DEV_MODE=1`), paths fall back cleanly to the project root directory.
- Tests can override the location cleanly via `SLMS_DATA_DIR`.
- Complete Windows ACL and service deployment models deferred to Phase 2.

### H. Legacy Code & File Preservation
- `client_agent/server/registration.py` and `client_agent/data/agent.json` are retained with explicit deprecation docstrings and metadata. Zero files deleted.

---

## 2. Test Execution & Verification Results

### Client Test Suite (`client_agent/tests/`)
Ran via `client_agent\.venv\Scripts\python.exe -m pytest client_agent/tests -v`:
- `test_smoke.py`: 3 passed (Environment operational, config and paths importable)
- `test_credentials.py`: 5 passed (Store interface, save/retrieve credentials, persistence, fallback)
- `test_enroll_auth.py`: 4 passed (Enrollment server URL persistence, HTTPS enforcement, auth token acquisition)
- `test_security.py`: 20 passed:
  - HTTPS enforced; HTTP rejected in production
  - Dev mode / `SLMS_ALLOW_INSECURE_HTTP=1` permits local HTTP
  - Production WSS derivation from HTTPS
  - WebSocket URL contains no token query parameter
  - WebSocket handshake header contains `Authorization: Bearer <token>`
  - Strict TLS verify parameter (`True` or CA path, never `False`)
  - Enterprise CA bundle path validation and missing file errors
  - Student Windows username excluded from `get_system_info()`
  - Process owner username set to `None` in `get_running_processes()`
  - Enrolled server URL authoritative in production
  - Silent production `SLMS_API_URL` override rejected with `RuntimeError`
  - Enrolled server matching env URL accepted
  - Enrolled server dev mode override permitted
  - Conflicting `SLMS_WS_URL` override rejected in production

**Client Results**: **32 passed in 4.99s** (100% pass rate).

### Backend Test Suite (`backend/tests/`)
Ran via `backend\.venv\Scripts\python.exe -m pytest backend/tests -v`:
- `test_telemetry_contract.py`: 4 passed (Process schema accepts null user, POST `/api/processes` accepts null user, network counters preserved, `ComputerCreate` has no username)
- `test_websocket_auth.py`: 4 passed (Header auth, legacy query fallback, missing token rejection, invalid token rejection)
- `test_websocket_real_handshake.py`: 5 passed:
  - Real `websocket-client` TCP handshake with `Authorization: Bearer <token>` header (no query param, no JWT in URL)
  - Missing token rejected during handshake (HTTP 403)
  - Invalid token rejected during handshake (HTTP 403)
  - Backward-compatible query fallback connects over real socket
  - `websocket-client` TLS `sslopt` configuration enforces `CERT_REQUIRED` and `check_hostname`

**Backend Results**: **13 passed in 0.78s** (100% pass rate).

### Import & Compilation Checks
- Client modules: `config`, `paths`, `core.security`, `core.credentials`, `server.enroll`, `server.auth`, `server.sender`, `server.communication`, `modules.system_info`, `modules.processes`, `modules.network` compile and import cleanly.
- Backend modules: `app.main`, `app.routes.websocket_router`, `app.routes.process_router`, `app.schemas.process_schema`, `app.schemas.metric_schema`, `app.schemas.computer_schema` compile and import cleanly.

---

## 3. Exact Remaining Limitations (Deferred to Subsequent Phases)

1. **Machine-Level Credential Storage**:
   - `KeyringCredentialStore` relies on interactive Windows Credential Manager. Non-interactive Windows Service execution (Session 0) under `LocalSystem` / service account requires DPAPI machine-level credential vault, which is intentionally deferred to Phase 2.
2. **Temporary Query-String WebSocket Auth Fallback**:
   - Backend route `/ws/client/{computer_id}` retains `?token=...` support to prevent breaking legacy clients. Complete decommission is scheduled for the later WebSocket hardening phase once all agents are updated.
3. **Windows Service & ACL Model**:
   - Directory structures are mapped to `%PROGRAMDATA%\SLMS`, but full Windows Security Identifiers (SID) ACL hardening (restricting write access to Administrators/SYSTEM) is deferred to Phase 2 deployment scripts.
4. **Offline Resilience & Outbox**:
   - Failed metric and process transmissions do not yet persist to a durable disk outbox (scheduled for Phase 3).

---

## 4. Git Status & Commit State

- **Branch**: `feature/client-agent-hardening`
- **Latest Commit**: `2c70b30` (`phase0: revise baseline with defect classifications and Phase 1 constraints`)
- **Phase 1 Commit Status**: **Uncommitted** (all changes remain in the local working tree awaiting final user review and approval).
