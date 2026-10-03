# SLMS Client Agent - Windows Installer Lifecycle & Operations Manual

This document details the architecture, state classification, operational modes, upgrade safety, rollback policies, and uninstallation behavior of the Smart Lab Management System (SLMS) Windows Client Agent installer (`SLMS_Client_Agent_Setup.exe`).

---

## 1. Architectural Principles

1. **Strict Runtime Separation**:
   * **Program Files (`C:\Program Files\SLMS`)**: Contains only static executable binaries (`SLMS_Client_Agent.exe`) and the Inno Setup uninstaller.
   * **ProgramData (`C:\ProgramData\SLMS`)**: Contains all dynamic runtime state, encrypted credentials (`config\service_credentials.enc`), offline outbox database (`data\outbox\outbox.db`), cache, and diagnostic logs (`logs\client.log`).
2. **Delegated Service Ownership**:
   * The installer never replicates complex Windows Service Control Manager (SCM) or Access Control List (ACL) logic in Pascal Script.
   * Service configuration, SCM recovery actions, and `%ProgramData%\SLMS` permissions are always executed by `SLMS_Client_Agent.exe install`.
3. **Zero Plaintext Secret Exposure**:
   * Enrollment keys are never accepted on or passed via process command-line arguments.
   * Secret transport uses temporary admin-protected files that are shredded and deleted immediately after use.

---

## 2. Installation State Classification

The installer deterministically probes the system during `InitializeSetup()` to classify the workstation state into one of four states:

| State Code | Name | Criteria | Associated Mode |
| :---: | :--- | :--- | :--- |
| **0** | `STATE_CLEAN` | No `{app}\SLMS_Client_Agent.exe`, no `%ProgramData%\SLMS\config\service_credentials.enc`, and no `SLMSService` registered in SCM. | `MODE_FRESH_INSTALL` |
| **1** | `STATE_VALID_INSTALL` | Installed executable exists, valid service credentials exist, and `SLMSService` is registered in SCM. | `MODE_UPGRADE` |
| **2** | `STATE_BROKEN_SERVICE` | Executable and service credentials exist, but `SLMSService` is missing or stopped/broken. | `MODE_REPAIR` |
| **3** | `STATE_PARTIAL_INSTALL` | Inconsistent or partial artifacts detected (e.g., credentials exist without binary, or binary exists without credentials). | Dynamic Resolution (Upgrade / Fresh) |

---

## 3. Operational Lifecycle Modes

### A. Fresh Installation (`MODE_FRESH_INSTALL`)
Triggered when the system is clean or requires complete provisioning.

1. **Wizard Pages**: Displays Welcome -> Server Configuration (`https://...`) -> Workstation Enrollment (`PasswordChar := '*'`) -> Ready Summary.
2. **File Extraction**: Extracts `SLMS_Client_Agent.exe` to `{autopf}\SLMS` (`C:\Program Files\SLMS`).
3. **Headless Enrollment**:
   * Writes the enrollment key to `{tmp}\slms_enroll.key`.
   * Executes:
     ```cmd
     SLMS_Client_Agent.exe enroll --url "<SERVER_URL>" --key-file "{tmp}\slms_enroll.key"
     ```
   * Overwrites `{tmp}\slms_enroll.key` with zeros and deletes it immediately.
   * Clears key from memory.
4. **Service Installation**: Invokes `SLMS_Client_Agent.exe install` to register `SLMSService`, grant `NT SERVICE\SLMSService` permissions on `%ProgramData%\SLMS`, and set recovery actions.
5. **Service Start & Verification**: Invokes `SLMS_Client_Agent.exe start` and polls `sc.exe query SLMSService` every second for up to 30 seconds until `RUNNING` is confirmed.

---

### B. In-Place Upgrade (`MODE_UPGRADE`)
Triggered when a valid existing installation is detected.

1. **Page Skipping**: Automatically skips Server URL and Enrollment Key wizard pages.
2. **Credential & Data Preservation**: **Never** calls `enroll`, **never** passes `--force`, and **never** modifies or deletes `%ProgramData%\SLMS\config\service_credentials.enc` or `outbox.db`.
3. **Pre-Replacement Binary Backup**:
   * Stops `SLMSService`.
   * Copies existing `SLMS_Client_Agent.exe` to `{tmp}\SLMS_Client_Agent.exe.bak`.
4. **Binary Replacement**: Safely overwrites `{app}\SLMS_Client_Agent.exe` with the new version.
5. **Service Reconciliation**: Runs `SLMS_Client_Agent.exe install` to apply any new service flags or account permissions.
6. **Service Restart & Health Polling**: Starts `SLMSService` and verifies `RUNNING` within 30 seconds.
7. **Cleanup**: Deletes `{tmp}\SLMS_Client_Agent.exe.bak` upon confirmed success.

---

### C. Repair & Service Re-registration (`MODE_REPAIR`)
Triggered when the executable and credentials exist but `SLMSService` is missing or in an invalid state.

1. **No Re-enrollment**: Uses existing machine DPAPI credentials.
2. **Service Reconciliation**: Executes `SLMS_Client_Agent.exe install` to recreate the SCM registration, restore recovery flags, and verify folder permissions.
3. **Service Start & Verification**: Starts the service and verifies `RUNNING` state.

---

### D. Partial Installation Resolution
* **Credentials Present, Binary Missing**: Treated as an Upgrade / Binary Restore. Replaces application files and reconciles the service without prompting for a new enrollment key.
* **Binary Present, Credentials Missing**: Treated as a Fresh Install. Prompts for Server URL and Enrollment Key to complete initial provisioning.
* **Orphaned Service Only**: Treated as a Fresh Install. Stops and cleans up orphaned service before completing provisioning.

---

## 4. Rollback & Failure Recovery Policies

### Fresh Install Rollback (`RollbackFreshInstallAndAbort`)
If any post-installation step fails during a fresh install:
1. Stops and deletes `SLMSService`.
2. Deletes freshly created `service_credentials.enc`.
3. Deletes installed `SLMS_Client_Agent.exe`.
4. Cleans up all temporary logs and key files.
5. Alerts the administrator with the exact failure reason and aborts setup cleanly without leaving orphaned artifacts.

### Upgrade Rollback (`RollbackUpgradeAndAbort`)
If an upgrade or service restart fails:
1. Stops the service.
2. Restores the previous `SLMS_Client_Agent.exe` from `{tmp}\SLMS_Client_Agent.exe.bak`.
3. Re-runs `SLMS_Client_Agent.exe install` and restarts the previous version.
4. Preserves all `%ProgramData%\SLMS` data and existing credentials.
5. Alerts the administrator that the upgrade failed and the previous version was restored.

---

## 5. Uninstallation Behavior & Data Retention

When uninstalled via Windows Add/Remove Programs:
1. **Service Removal**: Uninstaller executes `SLMS_Client_Agent.exe uninstall` (with `sc.exe delete SLMSService` fallback) to stop and remove `SLMSService`.
2. **Program Files Removal**: Deletes `C:\Program Files\SLMS` and uninstaller registry keys.
3. **ProgramData Retention Policy**:
   * `%ProgramData%\SLMS` (containing `service_credentials.enc`, telemetry outbox databases, state caches, and diagnostic logs) is **strictly retained by default**.
   * This ensures accidental uninstallation does not destroy machine identity or unsent offline telemetry.

---

## 6. Security Audit Summary

* **Zero Command-Line Secret Leakage**: Verified. `--key` is never passed to child processes.
* **Temporary Secret File Cleanup**: Ephemeral key files are overwritten with zeros and deleted immediately.
* **Memory Scrubbing**: Enrollment key strings are cleared from installer memory immediately after invocation.
* **Password Masking**: UI input uses masked password characters (`*`).
* **Transport Security**: Plaintext HTTP is rejected in production mode.
