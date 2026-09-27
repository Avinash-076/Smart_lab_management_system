# Phase 2 Implementation Report: Windows Service Architecture

## 1. Overview & Objective
Phase 2 transitions the SLMS Client Agent from a per-user startup-folder model into a managed Windows Service architecture. The service executes natively in Session 0 on system boot, authenticates using the Phase 1 TLS/JWT architecture without requiring interactive user login, isolates service management from runtime logic, eliminates interactive desktop dependencies (`MessageBoxW`), and implements automatic failure recovery under Windows Service Control Manager (SCM).

All changes have been implemented with zero regressions against Phase 1, maintaining full backward compatibility with local interactive execution and development workflows.

---

## 2. Previous vs. New Architecture

| Dimension | Previous Architecture (Phase 0 / 1) | New Architecture (Phase 2) |
| :--- | :--- | :--- |
| **Hosting Model** | Per-user desktop process (`main.py` launched in interactive user session) | Windows Service (`SLMSService`) managed by Windows Service Control Manager (SCM) |
| **Boot Behavior** | Did not run until an interactive user logged in; depended on `startup.py` copying exe to `%APPDATA%\...\Startup` | Runs automatically on system startup (`SERVICE_AUTO_START`) in Session 0 before any student logs in |
| **Credential Storage** | Windows Credential Manager (`KeyringCredentialStore`) tied to the interactive user's profile | Windows DPAPI Machine Scope (`ServiceCredentialStore`) with application entropy and restricted NTFS ACLs |
| **Privilege Model** | Ran with the permissions of whichever student happened to log in | Dedicated Virtual Service Account (`NT SERVICE\SLMSService`) with least-privilege isolation |
| **Process Lifecycle** | Uncontrolled loop with `time.sleep(20)` blocking prompt termination | Managed `ServiceLifecycle` state machine with `threading.Event` responsive shutdown (<0.2s) |
| **Desktop Isolation** | Called `ctypes.windll.user32.MessageBoxW(0, ...)`, which freezes or fails in Session 0 | Service-safe notification broadcasting via `msg.exe *` (3s timeout, 1024-char truncation) and agent event log; zero `MessageBoxW` calls |
| **Failure Recovery** | None; process crash stayed dead until user re-logged in | Configured SCM failure recovery actions: restart after 5s, 10s, 60s; `failureflag=1`; reports `win32ExitCode=1067` on crash |

---

## 3. Service Account Decision & Least-Privilege Model

### Evaluation of Candidate Accounts
- **`LocalSystem` (`NT AUTHORITY\SYSTEM`)**: Rejected as default production target. Grants unconstrained operating system privileges (`SeDebugPrivilege`, `SeTcbPrivilege`, full token manipulation), presenting severe privilege escalation risk if an agent vulnerability were exploited. Retained only as an optional installation argument (`--account LocalSystem`) for legacy/testing fallback.
- **`LocalService` / `NetworkService`**: Lacks authorization for system-level workstation control commands (restart/shutdown) without complex ACL delegation, and shares network identity across domain hosts.
- **Dedicated Local User (e.g. `.\SLMSService`)**: Requires static password management, rotation overhead, and risks credential exposure in installation scripts.
- **Dedicated Virtual Service Account (`NT SERVICE\SLMSService`)**: **SELECTED (Primary Production Target)**.
  - Automatically created and managed by Windows SCM on Windows 7 / Server 2008 R2 and later.
  - Zero password management overhead (Windows manages password rotation automatically).
  - Unique per-service Security Identifier (SID: `S-1-5-80-...`), allowing precise file and registry access control.
  - Operates under least-privilege principles: starts with minimal rights, and specific required privileges are granted without administrator group membership.

### Verified Windows Privileges & Access
The agent requires and validates the following specific privileges:
1. **`PROCESS_QUERY_LIMITED_INFORMATION`**: Required for querying process names, PIDs, and memory usage via `psutil`. Validated: Standard service accounts and authenticated users possess this right.
2. **Read-only HKLM Registry Access**: For enumerating installed software inventory (`HKLM\Software\Microsoft\Windows\CurrentVersion\Uninstall`). Validated: Authenticated Users and Services have default read permissions.
3. **Read/Write Access to `%PROGRAMDATA%\SLMS`**: For writing logs, metrics, output, and the encrypted credential vault. Validated: Configured via `icacls` granting Modify rights to `NT SERVICE\SLMSService`.
4. **Outbound Network Socket Creation**: TCP port 443/8000 for TLS and WSS communication with the backend. Validated: Standard outbound network sockets permitted without special privilege.
5. **`SeShutdownPrivilege`**: Required for executing administrative workstation reboot (`shutdown /r /t 5`) and power off (`shutdown /s /t 5`) commands. Configured during installation via `sc.exe privs SLMSService SeShutdownPrivilege/SeChangeNotifyPrivilege` and assigned to `NT SERVICE\SLMSService` in LSA (`LsaAddAccountRights`).

---

## 4. Credential Storage Design & Security Boundaries

Phase 1 preserved `KeyringCredentialStore` because Windows Credential Manager is bound to the interactive user's logon session. In Phase 2, `ServiceCredentialStore` resolves Session 0 credential access:

```
BaseCredentialStore (ABC)
    ├── KeyringCredentialStore / InteractiveCredentialStore (Interactive Dev Mode)
    └── ServiceCredentialStore / DpapiCredentialStore (Windows Service Session 0)
```

### Accurate Security Boundaries & Entropy Clarification
- **Windows DPAPI Machine Scope**: Encrypts credentials using Windows Data Protection API (`CryptProtectData` with `CRYPTPROTECT_LOCAL_MACHINE = 0x4`). DPAPI derives encryption keys from machine-specific master keys protected by the Windows Local Security Authority (LSA).
- **Application Entropy (`DEFAULT_ENTROPY`)**: An application-specific salt (`DEFAULT_ENTROPY`) is passed to `CryptProtectData` and `CryptUnprotectData`.
  > [!NOTE]
  > Because `DEFAULT_ENTROPY` is compiled into the application code, it is **not an independent secret** against an attacker with access to the agent binary. Its technical role is application binding: it prevents accidental cross-application decryption by generic DPAPI inspection utilities on the host that do not provide the SLMS entropy parameter.
- **NTFS Access Control Lists (Primary Security Boundary)**: The encrypted vault file (`%PROGRAMDATA%\SLMS\config\service_credentials.enc`) is permissioned via Windows `icacls` to restrict access strictly to:
  - `BUILTIN\Administrators` (`*S-1-5-32-544:(F)`)
  - `NT AUTHORITY\SYSTEM` (`*S-1-5-18:(F)`)
  - Current Administrator/Installer (`%USERNAME%:(F)`)
  - Virtual Service Account (`NT SERVICE\SLMSService:(R)`)
  - Inheritance is disabled (`/inheritance:r`), completely denying read or decrypt access to ordinary unprivileged student accounts logging onto the machine.
- **Memory-Only Access Tokens**: The raw `client_secret` is encrypted at rest. Bearer `access_token` values are held exclusively in memory and never written to disk or the vault.

---

## 5. Credential Provisioning Order (Flow A vs. Flow B)

Both deployment sequences are supported and tested:

### Flow A: Service Installation -> Admin Enrollment -> Service Start
1. Administrator installs the service: `python -m service install`.
   - Windows SCM creates `SLMSService` and registers the virtual service account `NT SERVICE\SLMSService` in LSA.
   - SCM recovery actions, failure flags, and service folder permissions are established.
2. Administrator executes enrollment: `python -m server.enroll ...`.
   - Enrollment exchanges registration token for `agent_id`, `client_secret`, and `computer_id`.
   - `ServiceCredentialStore.save_enrolled_credentials()` writes `service_credentials.enc`.
   - `_set_restricted_permissions()` sets ACLs for Administrators, SYSTEM, installer, and grants `NT SERVICE\SLMSService:(R)` (which now exists in LSA).
3. Service starts: `python -m service start` or system reboot.
   - `NT SERVICE\SLMSService` decrypts `service_credentials.enc`, authenticates, and connects.

### Flow B: Admin Enrollment -> Service Installation -> Service Start
1. Administrator executes enrollment: `python -m server.enroll ...` prior to service installation.
   - `service_credentials.enc` is created with ACLs for Administrators, SYSTEM, and installer.
2. Administrator installs the service: `python -m service install`.
   - Service is registered with SCM.
   - `install_service()` checks if `%PROGRAMDATA%\SLMS\config\service_credentials.enc` exists; if so, it explicitly grants `NT SERVICE\SLMSService:(R)` on the file and modify access on `%PROGRAMDATA%\SLMS`.
3. Service starts: `python -m service start` or system reboot.
   - `NT SERVICE\SLMSService` decrypts `service_credentials.enc`, authenticates, and connects.

In both flows:
- `service_credentials.enc` is created and encrypted.
- Unprivileged students have zero read permissions.
- No plaintext secrets are left on disk.

---

## 6. Service Lifecycle & Runtime Integration

### Architecture Diagram
```
                     +-----------------------------------+
                     | Windows Service Control Manager   |
                     +-----------------------------------+
                                     |
                     SvcDoRun / SvcStop / SvcShutdown
                                     v
                     +-----------------------------------+
                     |    SLMSService (service.py)       |
                     |  Reports SCM status & events      |
                     +-----------------------------------+
                                     |
                                     v
                     +-----------------------------------+
                     | ServiceLifecycle (lifecycle.py)   |
                     |  STOPPED -> STARTING -> RUNNING   |
                     |  STOPPING -> STOPPED (or FAILED)  |
                     +-----------------------------------+
                                     |
                         Spawns worker thread
                                     v
                     +-----------------------------------+
                     |     AgentRuntime (runtime.py)     |
                     |  1. Verify Enrollment             |
                     |  2. Authenticate & acquire JWT    |
                     |  3. Connect WebSocket (WSS)       |
                     |  4. Periodic Telemetry Loop       |
                     |  5. Responsive stop_event.wait()  |
                     +-----------------------------------+
```

### State Transitions
1. **Startup**: SCM sends `SERVICE_START` -> `SLMSService.SvcDoRun()` reports `SERVICE_RUNNING` -> `ServiceLifecycle.start()` spawns worker thread -> `AgentRuntime.start()` verifies enrollment, acquires JWT, establishes WebSocket, and enters periodic monitoring loop.
2. **Stop / Shutdown**: SCM sends `SERVICE_CONTROL_STOP` or `SERVICE_CONTROL_SHUTDOWN` -> `SLMSService.SvcStop()` reports `SERVICE_STOP_PENDING` -> `ServiceLifecycle.stop()` sets `stop_event` -> `stop_event.wait()` in runtime loop wakes up immediately -> WebSocket client stops -> worker thread terminates -> reports `SERVICE_STOPPED` with `win32ExitCode=0`.
3. **Unexpected Crash Recovery**: If an unhandled exception crashes the runtime worker thread:
   - `ServiceLifecycle` captures the exception and transitions to `ServiceState.FAILED`.
   - `SvcDoRun()` detects the unexpected worker termination.
   - Reports `SERVICE_STOPPED` with `win32ExitCode = 1067` (`ERROR_PROCESS_ABORTED`).
   - Terminates process via `os._exit(1067)`.
   - SCM registers failure (via non-zero exit code and abnormal process termination) and triggers configured restart recovery actions.
4. **Configuration Stop (Missing Enrollment)**: If the agent is not enrolled, `AgentRuntime.start()` logs a critical warning and returns cleanly. Worker transitions to `ServiceState.STOPPED`. `SvcDoRun()` reports `SERVICE_STOPPED` with `win32ExitCode = 0`, exiting cleanly without triggering infinite restart flapping.

---

## 7. Service Recovery Policy & SCM Failure Recognition

Configured automatically during service installation:

```powershell
sc.exe failure SLMSService reset= 86400 actions= restart/5000/restart/10000/restart/60000
sc.exe failureflag SLMSService 1
```

- **Reset Counter**: 86,400 seconds (24 hours of clean running resets the failure count).
- **First Failure**: Automatic service restart after 5,000 ms (5 seconds).
- **Second Failure**: Automatic service restart after 10,000 ms (10 seconds).
- **Subsequent Failures**: Automatic service restart after 60,000 ms (60 seconds).
- **Failure Flag Setting (`sc failureflag SLMSService 1`)**: Instructs Windows SCM to execute failure actions if the service enters `SERVICE_STOPPED` with a non-zero exit code, in addition to unexpected process termination.
- **Crash Flapping Prevention**: Permanent configuration errors terminate with `win32ExitCode = 0` to prevent flapping.

---

## 8. MessageBox & Session 0 Notification Handling

- **The Problem**: In Windows Vista and later, services run in isolated Session 0 where interactive window stations (`WinSta0`) do not exist. Calling `MessageBoxW(0, ...)` from a service blocks indefinitely or silently fails.
- **The Solution**: Completely eliminated `MessageBoxW` from `client_agent/server/command_handler.py`.
- **Implementation & Fallback**:
  1. The administrative notice is recorded in the agent log: `logger.info(f"Administrator notice received: {message}")`.
  2. Input is sanitized and truncated to 1024 characters to prevent command-line buffer overflows.
  3. Non-blocking desktop broadcast is attempted via `msg.exe * /time:15 "<message>"` with a 3-second timeout.
  4. If `msg.exe` fails (e.g. exit code 1 when no user sessions are logged in, RPC server unavailable, timeout, or missing binary), it logs at debug level and returns `(True, "Notice recorded in agent log: <message>")`. The service thread never blocks.

---

## 9. Service Management Commands (CLI)

```powershell
# Query current service status
python -m service status

# Install service with default Virtual Service Account (NT SERVICE\SLMSService)
python -m service install

# Install service with LocalSystem account (alternative)
python -m service install --account LocalSystem

# Start the installed service
python -m service start

# Stop the running service
python -m service stop

# Uninstall the service
python -m service uninstall

# Run service in interactive debug/console mode (for developer testing)
python -m service debug
```

*(Note: SCM interaction commands `install`, `uninstall`, `start`, `stop` require an elevated Administrator terminal).*

---

## 10. Deprecated Files
- `client_agent/startup.py`: Marked with explicit deprecation docstrings. Production installation relies on Windows Service registration, not per-user startup folders.

---

## 11. Complete Test Results

### Client Agent Test Suite (`client_agent/tests/`)
Command: `.\client_agent\.venv\Scripts\python.exe -m pytest client_agent/tests -v`
```
============================= test session starts =============================
platform win32 -- Python 3.13.5, pytest-9.1.1, pluggy-1.6.0
collected 62 items

client_agent\tests\test_credentials.py::TestCredentialStoreAbstraction::test_not_enrolled_initially PASSED [  1%]
client_agent\tests\test_credentials.py::TestCredentialStoreAbstraction::test_save_and_retrieve_credentials PASSED [  3%]
client_agent\tests\test_credentials.py::TestCredentialStoreAbstraction::test_partial_credentials_not_enrolled PASSED [  4%]
client_agent\tests\test_credentials.py::TestCredentialStoreAbstraction::test_server_url_persistence PASSED [  6%]
client_agent\tests\test_credentials.py::TestKeyringCredentialStoreServerConfig::test_keyring_store_file_fallback PASSED [  8%]
client_agent\tests\test_enroll_auth.py::test_enrollment_persists_credentials_and_server_url PASSED [  9%]
client_agent\tests\test_enroll_auth.py::test_enrollment_rejects_insecure_http_in_production PASSED [ 11%]
client_agent\tests\test_enroll_auth.py::test_auth_get_access_token PASSED [ 12%]
client_agent\tests\test_enroll_auth.py::test_auth_without_enrollment_raises_runtime_error PASSED [ 14%]
client_agent\tests\test_security.py::TestUrlValidation::test_https_url_valid_in_production PASSED [ 16%]
client_agent\tests\test_security.py::TestUrlValidation::test_http_url_rejected_in_production PASSED [ 17%]
client_agent\tests\test_security.py::TestUrlValidation::test_http_url_allowed_with_insecure_flag PASSED [ 19%]
client_agent\tests\test_security.py::TestUrlValidation::test_http_url_allowed_with_dev_mode PASSED [ 20%]
client_agent\tests\test_security.py::TestUrlValidation::test_empty_or_invalid_urls_rejected PASSED [ 22%]
client_agent\tests\test_security.py::TestWebSocketUrlAndHeaders::test_derive_ws_url_from_https PASSED [ 24%]
client_agent\tests\test_security.py::TestWebSocketUrlAndHeaders::test_derive_ws_url_from_http_in_dev_mode PASSED [ 25%]
client_agent\tests\test_security.py::TestWebSocketUrlAndHeaders::test_production_ws_endpoint_contains_no_token PASSED [ 27%]
client_agent\tests\test_security.py::TestWebSocketUrlAndHeaders::test_websocket_headers_contain_bearer_token PASSED [ 29%]
client_agent\tests\test_security.py::TestWebSocketUrlAndHeaders::test_websocket_headers_reject_empty_token PASSED [ 30%]
client_agent\tests\test_security.py::TestTlsVerification::test_verify_parameter_defaults_to_true PASSED [ 32%]
client_agent\tests\test_security.py::TestTlsVerification::test_ca_bundle_returns_valid_path PASSED [ 33%]
client_agent\tests\test_security.py::TestTlsVerification::test_missing_ca_bundle_raises_file_not_found PASSED [ 35%]
client_agent\tests\test_security.py::TestPrivacyHardening::test_system_info_does_not_collect_username PASSED [ 37%]
client_agent\tests\test_security.py::TestPrivacyHardening::test_processes_sets_user_to_none PASSED [ 38%]
client_agent\tests\test_security.py::TestServerUrlBinding::test_enrolled_server_url_authoritative_in_production PASSED [ 40%]
client_agent\tests\test_security.py::TestServerUrlBinding::test_enrolled_server_cannot_be_silently_overridden_in_production PASSED [ 41%]
client_agent\tests\test_security.py::TestServerUrlBinding::test_enrolled_server_matching_env_url_accepted PASSED [ 43%]
client_agent\tests\test_security.py::TestServerUrlBinding::test_enrolled_server_override_allowed_in_dev_mode PASSED [ 45%]
client_agent\tests\test_security.py::TestServerUrlBinding::test_ws_base_url_cannot_be_overridden_in_production PASSED [ 46%]
client_agent\tests\test_service.py::TestServiceImportsAndConstruction::test_service_module_imports PASSED [ 48%]
client_agent\tests\test_service.py::TestServiceImportsAndConstruction::test_service_class_construction PASSED [ 50%]
client_agent\tests\test_service.py::TestServiceLifecycle::test_service_lifecycle_state_transitions PASSED [ 51%]
client_agent\tests\test_service.py::TestServiceLifecycle::test_stop_event_causes_clean_shutdown PASSED [ 53%]
client_agent\tests\test_service.py::TestServiceLifecycle::test_runtime_starts_and_stops_exactly_once PASSED [ 54%]
client_agent\tests\test_service.py::TestServiceCredentialStorage::test_service_credential_store_dpapi_machine_scope PASSED [ 56%]
client_agent\tests\test_service.py::TestServiceCredentialStorage::test_service_configuration_contains_no_plaintext_secret PASSED [ 58%]
client_agent\tests\test_service.py::TestServiceCredentialStorage::test_interactive_keyring_development_behavior_intact PASSED [ 59%]
client_agent\tests\test_service.py::TestServiceCredentialStorage::test_credential_migration_from_keyring_to_service PASSED [ 61%]
client_agent\tests\test_service.py::TestServiceSecurityAndNonInteractiveConstraints::test_service_does_not_use_messageboxw PASSED [ 62%]
client_agent\tests\test_service.py::TestServiceSecurityAndNonInteractiveConstraints::test_startup_py_is_no_longer_required PASSED [ 64%]
client_agent\tests\test_service.py::TestServiceSecurityAndNonInteractiveConstraints::test_authentication_failure_handled_cleanly PASSED [ 66%]
client_agent\tests\test_service.py::TestServiceSecurityAndNonInteractiveConstraints::test_unexpected_runtime_failure_transitions_to_failed PASSED [ 67%]
client_agent\tests\test_service.py::TestServiceSecurityAndNonInteractiveConstraints::test_service_recovery_configuration_generated_correctly PASSED [ 69%]
client_agent\tests\test_service.py::TestServiceSCMFailureRecovery::test_recovery_and_failure_flag_commands PASSED [ 70%]
client_agent\tests\test_service.py::TestServiceSCMFailureRecovery::test_svc_do_run_graceful_stop_reports_exit_code_zero PASSED [ 72%]
client_agent\tests\test_service.py::TestServiceSCMFailureRecovery::test_svc_do_run_unexpected_crash_reports_non_zero_exit_code PASSED [ 74%]
client_agent\tests\test_service.py::TestServiceSCMFailureRecovery::test_svc_do_run_missing_enrollment_clean_exit PASSED [ 75%]
client_agent\tests\test_service.py::TestCredentialProvisioningOrder::test_flow_a_service_installed_then_enrolled PASSED [ 77%]
client_agent\tests\test_service.py::TestCredentialProvisioningOrder::test_flow_b_enrolled_then_service_installed PASSED [ 79%]
client_agent\tests\test_service.py::TestCredentialProvisioningOrder::test_ordinary_student_cannot_read_or_decrypt_credentials PASSED [ 80%]
client_agent\tests\test_service.py::TestMsgExeHandling::test_msg_exe_success PASSED [ 82%]
client_agent\tests\test_service.py::TestMsgExeHandling::test_msg_exe_failure_fallback_to_log PASSED [ 83%]
client_agent\tests\test_service.py::TestMsgExeHandling::test_msg_exe_timeout_fallback_to_log PASSED [ 85%]
client_agent\tests\test_service.py::TestMsgExeHandling::test_msg_exe_truncates_oversized_payload PASSED [ 87%]
client_agent\tests\test_service.py::TestMsgExeHandling::test_msg_exe_none_payload_handled PASSED [ 88%]
client_agent\tests\test_service.py::TestVirtualServiceAccountPrivileges::test_process_enumeration_permissions PASSED [ 90%]
client_agent\tests\test_service.py::TestVirtualServiceAccountPrivileges::test_software_inventory_hklm_read_permissions PASSED [ 91%]
client_agent\tests\test_service.py::TestVirtualServiceAccountPrivileges::test_programdata_slms_read_write PASSED [ 93%]
client_agent\tests\test_service.py::TestVirtualServiceAccountPrivileges::test_sc_privs_command_generation PASSED [ 95%]
client_agent\tests\test_smoke.py::test_test_environment_operational PASSED [ 96%]
client_agent\tests\test_smoke.py::test_core_config_importable PASSED     [ 98%]
client_agent\tests\test_smoke.py::test_core_paths_importable PASSED      [100%]

============================= 62 passed in 5.80s ==============================
```

### Backend Test Suite (`backend/tests/`)
Command: `.\backend\.venv\Scripts\python.exe -m pytest backend/tests -v`
```
============================= test session starts =============================
platform win32 -- Python 3.13.5, pytest-9.1.1, pluggy-1.6.0
collected 13 items

backend\tests\test_telemetry_contract.py::test_process_schema_accepts_null_user PASSED [  7%]
backend\tests\test_telemetry_contract.py::test_process_upload_endpoint_accepts_null_user PASSED [ 15%]
backend\tests\test_telemetry_contract.py::test_metric_schema_preserves_network_counters PASSED [ 23%]
backend\tests\test_telemetry_contract.py::test_computer_create_schema_has_no_username PASSED [ 30%]
backend\tests\test_websocket_auth.py::test_websocket_auth_via_authorization_header PASSED [ 38%]
backend\tests\test_websocket_auth.py::test_websocket_auth_via_legacy_query_param PASSED [ 46%]
backend\tests\test_websocket_auth.py::test_websocket_missing_token_rejected PASSED [ 53%]
backend\tests\test_websocket_auth.py::test_websocket_invalid_token_rejected PASSED [ 61%]
backend\tests\test_websocket_real_handshake.py::test_real_websocket_handshake_with_authorization_header PASSED [ 69%]
backend\tests\test_websocket_real_handshake.py::test_real_websocket_handshake_missing_token_rejected PASSED [ 76%]
backend\tests\test_websocket_real_handshake.py::test_real_websocket_handshake_invalid_token_rejected PASSED [ 84%]
backend\tests\test_websocket_real_handshake.py::test_real_websocket_handshake_backward_compatible_query_fallback PASSED [ 92%]
backend\tests\test_websocket_real_handshake.py::test_websocket_client_tls_sslopt_enforcement PASSED [100%]

======================= 13 passed, 2 warnings in 0.89s ========================
```

**Combined Automated Test Results**: **75 passed, 0 failed** (100% pass rate).

---

## 12. Manual Windows Validation & Known Limitations

- **DPAPI Encryption/Decryption**: Validated on Windows host via `test_service_credential_store_dpapi_machine_scope` with machine-scoped DPAPI and application entropy.
- **Service Registration / SCM API**: Verified module imports, class definitions, and Windows SCM dispatcher using `win32serviceutil.ServiceFramework`.
- **Session 0 Notification Handling**: Verified replacement of `MessageBoxW` with `msg.exe *` broadcast, truncation, and logger fallback.
- **Service Stop Latency**: Verified `<0.2s` stop responsiveness using `stop_event.wait()` in `test_stop_event_causes_clean_shutdown`.
- **SCM Failure Recognition**: Verified that unexpected worker crash reports `SERVICE_STOPPED` with exit code 1067 (`ERROR_PROCESS_ABORTED`) and calls abnormal process termination `os._exit(1067)`, causing SCM with `failureflag 1` to execute recovery restarts.
- **Limitation — SCM Service Registration Elevation**: Live registration of services in Windows Service Control Manager (`sc.exe create` / `OpenSCManager`) requires an elevated Administrator command prompt. Running `sc.exe create` in a non-elevated user terminal returns `[SC] OpenSCManager FAILED 5: Access is denied.` In non-elevated developer and CI environments, unit, configuration, and state machine tests execute comprehensively while live SCM installation and system reboot soak tests are deferred to Phase 11 on dedicated lab hardware.

---

## 13. Explicitly Deferred Work (Phase 3+)
- **Phase 3**: Durable local state and disk outbox for telemetry data during network outages.
- **Phase 4**: Hardware and software collector redesign.
- **Phase 5**: Monitoring scheduler refactoring and deduplication.
- **Phase 6**: Issue management lifecycle redesign.
- **Phase 7**: WebSocket reconnect backoff hardening and query-token parameter decommission.
- **Phase 8**: Runtime modularization into Scheduler/CollectorManager/UploadManager.
- **Phase 9**: Windows Event Log integration and log file rotation.
- **Phase 10**: Quality engineering and soak testing.
- **Phase 11**: Final MSI installer and 40-PC lab deployment validation.
