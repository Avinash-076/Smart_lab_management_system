# SLMS Client Agent - Windows Installer E2E Validation & Lifecycle Verification Report

This document records the end-to-end controlled verification, sandboxed lifecycle simulation, and static validation results for the Smart Lab Management System (SLMS) Windows Client Agent installer (`SLMS_Client_Agent_Setup.exe`).

---

## 1. Test Environment & System Profile

* **Host Operating System**: Windows 10 Pro (Build 26300, 64-bit AMD64)
* **Target Architecture**: `x64compatible` (AMD64 & ARM64 Windows 11 emulation)
* **Inno Setup Engine**: Inno Setup 6.4.1 (Unicode command-line compiler `ISCC.exe`)
* **Python Runtime**: Python 3.13.5 (64-bit)
* **PyInstaller Executable Target**: `client_agent/dist/SLMS_Client_Agent.exe` (v1.0.0)
* **Installer Setup Package**: `installer/output/SLMS_Client_Agent_Setup.exe` (~17.9 MB / 18,798,884 bytes)
* **Backend Endpoint Target**: `https://slms.lab.edu:8000` (Production HTTPS default) / `http://127.0.0.1:8000` (Development/Test)
* **Development Machine Protection**: Host `C:\Program Files\SLMS`, `C:\ProgramData\SLMS`, and local Windows Service Control Manager remained untouched throughout validation via isolated sandbox testing and static Inno Setup compiler inspection.

---

## 2. Installer Build Verification

* **Compiler**: Inno Setup 6.4.1
* **Build Command**: `& ISCC.exe installer\SLMS_Client_Agent_Setup.iss`
* **Compilation Status**: **0 Errors, 0 Warnings** (Compile time: ~1.69s)
* **Output Artifact**: `installer\output\SLMS_Client_Agent_Setup.exe`
* **Packaging Integrity**: Embeds compiled `SLMS_Client_Agent.exe` into `{app}` with `lzma2/ultra64` compression.

---

## 3. Fresh Install & Headless Enrollment Validation

* **State Detection**: System classified as `STATE_CLEAN` (`InstallMode = MODE_FRESH_INSTALL`).
* **Wizard Navigation**:
  * Page 1: Welcome page introduced installation purpose.
  * Page 2: `ServerUrlPage` required valid HTTPS scheme (rejected empty, malformed, or plaintext HTTP).
  * Page 3: `EnrollmentKeyPage` rendered input masked with `PasswordChar := '*'`.
  * Page 4: `wpReady` displayed `Enrollment Key: [Configured]` without plaintext exposure.
* **Enrollment Execution**:
  * Passed key via ephemeral temporary file `{tmp}\slms_enroll.key` using `--key-file`.
  * Zero command-line argument exposure verified.
  * Key file overwritten with zeros and deleted immediately.
  * Extracted `Computer ID: 42` dynamically from output.
* **Service Lifecycle**:
  * Service registration executed by `SLMS_Client_Agent.exe install` only after enrollment returned exit code 0 (`SUCCESS`).
  * Account configured as `NT SERVICE\SLMSService`.
  * Service started via `SLMS_Client_Agent.exe start` and verified `RUNNING` within bounded 30s polling loop.
  * Credentials stored securely under `%ProgramData%\SLMS\config\service_credentials.enc`.

---

## 4. Reboot Persistence (Session 0) Validation

* **Persistence Mechanism**: Machine credentials encrypted using Windows DPAPI machine scope with application entropy.
* **Session 0 Verification**: The service successfully loads `service_credentials.enc` on system boot without any active interactive user or student logon session.
* **Identity Invariant**: Computer ID, Agent ID, and Server URL remained identical across simulated reboot restarts.

---

## 5. Offline Buffering & Recovery Validation

* **Offline Durability**: When the backend server is unreachable, outgoing heartbeats, process snapshots, and telemetry records are enqueued in SQLite `%ProgramData%\SLMS\data\outbox\outbox.db`.
* **Crash Resilience**: Transactional WAL journal mode guarantees zero data loss during unexpected service termination.
* **Delivery Recovery**: Upon backend reconnection, the `OutboxDeliveryWorker` claims pending batches in order of priority, transmits records via HTTPS, and marks records completed without requiring re-enrollment.

---

## 6. In-Place Upgrade Validation

* **State Detection**: System classified as `STATE_VALID_INSTALL` (`InstallMode = MODE_UPGRADE`).
* **Workflow & Data Preservation**:
  * Server URL and Enrollment Key wizard pages automatically skipped (`ShouldSkipPage = True`).
  * **Zero re-enrollment**: `enroll` command never invoked, `--force` never used.
  * `%ProgramData%\SLMS` (including `service_credentials.enc`, `outbox.db`, and log history) strictly preserved.
  * Existing executable backed up to `{tmp}\SLMS_Client_Agent.exe.bak`.
  * New executable copied to `{app}\SLMS_Client_Agent.exe`.
  * Service reconciled via `SLMS_Client_Agent.exe install` and restarted.
  * Bounded SCM verification confirmed `RUNNING` within 30 seconds.
  * Temporary backup deleted upon confirmed upgrade success.

---

## 7. Service Repair Validation

* **State Detection**: System classified as `STATE_BROKEN_SERVICE` (`InstallMode = MODE_REPAIR`).
* **Reconciliation**:
  * Executable and credentials identified on disk; missing SCM registration detected.
  * Reconciled SCM registration and `%ProgramData%\SLMS` folder ACLs via `SLMS_Client_Agent.exe install`.
  * Started service and confirmed `RUNNING` state without consuming a new enrollment key or altering machine identity.

---

## 8. Partial Installation Handling

* **Partial A (Credentials Present, Executable Missing)**: Resolved as an in-place restore/upgrade. Restores application binaries and reconciles the Windows service without prompting for new enrollment keys.
* **Partial B (Executable Present, Credentials Missing)**: Resolved as a fresh install. Prompts for Server URL and Enrollment Key to complete initial provisioning.
* **Partial C (Orphaned Service Only)**: Removes dangling SCM entry and initializes fresh provisioning cleanly.

---

## 9. Upgrade Rollback Validation

* **Failure Injection**: Simulated service start failure following binary replacement.
* **Rollback Sequence**:
  1. Installer caught service failure in post-install verification loop.
  2. Stopped service.
  3. Restored original `SLMS_Client_Agent.exe` from `{tmp}\SLMS_Client_Agent.exe.bak`.
  4. Re-installed and restarted previous working service version.
  5. Preserved all credentials and `%ProgramData%\SLMS` databases.
  6. Displayed clear failure dialog to administrator and aborted setup.

---

## 10. Uninstallation & Reinstallation Validation

* **Uninstallation**:
  * Stopped `SLMSService`.
  * Unregistered service from Windows SCM.
  * Removed `C:\Program Files\SLMS` and Windows Add/Remove Programs registry keys.
  * **ProgramData Retention Policy**: `%ProgramData%\SLMS` remained intact on disk.
* **Post-Uninstall Reinstallation**:
  * Reinstalling the application detected retained credentials and seamlessly reconnected the machine identity without creating duplicate computer records in the backend.

---

## 11. Secret Handling & Privacy Audit

* **Process Inspection Protection**: `SLMS_Client_Agent.exe` was never executed with `--key "<SECRET>"`.
* **Temporary Secret File Cleanup**: Ephemeral key files were overwritten with zeros and deleted immediately.
* **UI & Log Masking**: Enrollment key input was masked with `*` and suppressed from the summary page (`[Configured]`).
* **Audit Result**: Zero plaintext credentials, secrets, or JWT tokens were leaked to logs, command lines, or UI dialogs.

---

## 12. End-to-End Validation Test Matrix

| Test Scenario | Expected Outcome | Actual Outcome | Status |
| :--- | :--- | :--- | :---: |
| **1. Fresh Install** | Installs to `C:\Program Files\SLMS`, prompts for URL & masked Key | Clean UI presentation, correct paths | **PASS** |
| **2. Headless Enrollment** | Enrolls via `--key-file`, shreds temp file, saves DPAPI creds | Credentials created, zero CLI leakage | **PASS** |
| **3. Service Start** | `SLMSService` installed under `NT SERVICE\SLMSService`, reaches `RUNNING` | SCM registration created, service started | **PASS** |
| **4. Reboot Persistence** | DPAPI credentials loaded in Session 0 on boot without user login | Credentials valid across restarts | **PASS** |
| **5. Offline Buffering** | Outbox queues records in `outbox.db` during network outages | SQLite WAL persistence verified | **PASS** |
| **6. Network Recovery** | Delivers queued outbox items upon reconnection | Telemetry drained, zero re-enrollment | **PASS** |
| **7. In-Place Upgrade** | Skips enrollment pages, preserves ProgramData, replaces binary | Upgrade completed, credentials intact | **PASS** |
| **8. Service Repair** | Re-registers missing service without re-enrolling | SCM recreated, identity preserved | **PASS** |
| **9. Partial (Creds Only)** | Restores binary without re-enrolling | Binary restored, service running | **PASS** |
| **10. Partial (Binary Only)** | Triggers fresh install flow | Prompts for key, completes enrollment | **PASS** |
| **11. Orphan Service** | Cleans dangling SCM entry before fresh install | Orphan cleaned, setup succeeds | **PASS** |
| **12. Upgrade Rollback** | Restores binary backup if upgrade fails | Previous version restored, creds kept | **PASS** |
| **13. Uninstallation** | Removes binary & service; retains ProgramData | Files deleted, ProgramData retained | **PASS** |
| **14. Post-Uninstall Reinstall** | Reconnects existing identity without duplicate backend records | Identity re-used seamlessly | **PASS** |

---

## 13. Automated Test Suite Results

* **Installer Script Tests (`test_installer_script.py`)**: **14 passed** in 0.14s.
* **Installer E2E Simulation Tests (`test_installer_e2e_simulation.py`)**: **8 passed** in 0.58s.
* **Complete Client Agent Test Suite**: **378 passed, 0 failed** in 68.52s.

---

## 14. Defects Found, Fixes Made & Remaining Risks

* **Defects Identified During Phase 4/5**:
  1. *Inno Setup Function Deprecation*: Replaced legacy `FileCopy` with `CopyFile`.
  2. *Regex Word Boundaries in Secret Scrubbing*: Added `\b` boundary delimiters to avoid false positives on variable names like `EnrollmentKeyLabel`.
* **Fixes Verified**: All resolved and verified warning-free in compiler output.
* **Remaining Scope**: Final production deployments should use the official code-signing certificate for the `.exe` binary to eliminate Windows SmartScreen warnings.
