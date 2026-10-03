# SLMS Client Agent Credential Store Architecture & Installer Resolution Specification

## 1. Overview

The SLMS Client Agent securely stores sensitive machine-level identity credentials required for authentication with the SLMS central server:
- `client_id` / `agent_id`: Workstation client identifier.
- `client_secret`: High-entropy client secret key used for JWT access token acquisition.
- `computer_id`: Enrolled database primary key for the computer entity.
- `server_url`: Authoritative SLMS central server URL (HTTPS in production).

This document outlines the credential store architecture, storage mediums, resolution rules, enrollment persistence guarantees, and installer integration verification.

---

## 2. Credential Store Hierarchy

```
                    ┌─────────────────────────┐
                    │     CredentialStore     │ (Abstract Base)
                    │  (client_agent/core/    │
                    │      credentials.py)    │
                    └───────────┬─────────────┘
                                │
            ┌───────────────────┴───────────────────┐
            │                                       │
            ▼                                       ▼
┌───────────────────────────────┐       ┌───────────────────────────────┐
│     ServiceCredentialStore    │       │     KeyringCredentialStore    │
│  - Storage: DPAPI-encrypted   │       │  - Storage: Windows           │
│    file (%ProgramData%\SLMS\  │       │    Credential Manager         │
│    config\service_credentials │       │    (Interactive user desktop) │
│    .enc)                      │       │  - Target: Legacy/interactive │
│  - Scope: Machine (Session 0  │       │    manual dev runs only       │
│    Windows Service compatible)│       └───────────────────────────────┘
│  - Target: Production Windows │
│    Service & Installer Default│
└───────────────────────────────┘
```

### 2.1 ServiceCredentialStore (Primary / Default)
- **Path**: `%ProgramData%\SLMS\config\service_credentials.enc`
- **Encryption**: Windows DPAPI `CryptProtectData` with `CRYPTPROTECT_LOCAL_MACHINE` machine scope (`0x4`).
- **Access Scope**: Accessible by `NT SERVICE\SLMSService`, `LocalSystem`, and local Administrators in Session 0 and Session 1+.
- **File Permissions**: Protected under `%ProgramData%\SLMS` ACLs (Admin/SYSTEM full control, Users read/execute or restricted).

### 2.2 KeyringCredentialStore (Explicit Opt-In Only)
- **Backend**: Windows Credential Manager (`keyring.backends.Windows.WinVaultKeyring`).
- **Scope**: Current logged-in user account only (User DPAPI).
- **Session 0 Limitation**: Inaccessible from Windows Services running under `NT SERVICE\SLMSService` or `LocalSystem`.
- **Selection**: Strictly used only when `SLMS_USE_KEYRING=1` is explicitly specified in the environment AND `SLMS_SERVICE_MODE` is not active (`0`).

---

## 3. Resolution Matrix & Environment Flags

`get_credential_store()` determines the store instance according to strict priority rules:

| `SLMS_SERVICE_MODE` | `SLMS_USE_KEYRING` | `SLMS_DEV_MODE` | Target Credential Store | Rationale |
|:---:|:---:|:---:|:---|:---|
| `1` | Any | Any | `ServiceCredentialStore` | Windows Service strictly requires machine-scoped DPAPI storage. |
| `0` / unset | `1` | Any | `KeyringCredentialStore` | Explicit developer opt-in for interactive credential manager. |
| `0` / unset | `0` / unset | `1` | `ServiceCredentialStore` | `DEV_MODE=1` controls logging/HTTP allowances, NOT storage mechanism. |
| `0` / unset | `0` / unset | `0` / unset | `ServiceCredentialStore` | Production default. |

> **Key Fix**: `SLMS_DEV_MODE=1` is **completely decoupled** from credential store selection. Setting `SLMS_DEV_MODE=1` does **not** divert credentials into Windows Credential Manager.

---

## 4. Headless Enrollment Persistence Architecture

When the Windows installer executes `SLMS_Client_Agent.exe enroll` (or an administrator runs it from the CLI):

```
[Inno Setup Wizard / CLI]
           │
           │ (passes URL & Key via ephemeral stdin/temp file)
           ▼
[handle_enroll_cli()] in server/enroll.py
           │
           │ 1. Resolves target store explicitly: _get_target_store() -> ServiceCredentialStore
           │ 2. Queries is_enrolled() strictly on target store (ignores stale Keyring credentials)
           │ 3. Executes HTTPS enrollment handshake with backend /api/v1/enrollment/enroll
           │ 4. Receives client_id, client_secret, computer_id
           │
           ▼
[target_store.save_credentials(...)]
           │
           │ 5. Writes DPAPI-encrypted %ProgramData%\SLMS\config\service_credentials.enc
           │    - No silent exception swallowing (fail-fast RuntimeError on write error)
           │
           ▼
[Post-Persistence Readability & Integrity Verification]
           │
           │ 6. Immediately re-reads and validates service_credentials.enc
           │    - Checks client_id, client_secret, computer_id exist and match
           │    - If verification fails, removes corrupt file and exits with code 8 (ENROLLMENT_FAILURE)
           │
           ▼
[Exit Code 0: SUCCESS]
```

### 4.1 Exit Codes for Enrollment CLI

| Code | Name | Description |
|:---:|:---|:---|
| `0` | `SUCCESS` | Workstation successfully enrolled, credentials validated in `service_credentials.enc`. |
| `1` | `INVALID_ARGUMENTS` | Missing or invalid arguments (e.g. `--key` and `--stdin-key` both specified). |
| `2` | `INVALID_SERVER_URL` | Malformed URL or insecure HTTP URL without `SLMS_ALLOW_INSECURE_HTTP=1`. |
| `3` | `ALREADY_ENROLLED` | `service_credentials.enc` already exists and `--force` was not passed. |
| `4` | `INVALID_OR_EXPIRED_KEY` | Server returned HTTP 401 Unauthorized during enrollment handshake. |
| `5` | `DUPLICATE_COMPUTER` | Server returned HTTP 409 Conflict (computer name already registered). |
| `6` | `SERVER_UNREACHABLE` | Network timeout, connection error, or DNS failure. |
| `7` | `TLS_SECURITY_FAILURE` | HTTPS certificate validation failure or handshake abort. |
| `8` | `ENROLLMENT_FAILURE` | Credential persistence failure, DPAPI encryption failure, or corrupt save file. |
| `99` | `UNEXPECTED_ERROR` | Unhandled runtime exception. |

---

## 5. Installer Post-Enrollment Validation

In `installer/SLMS_Client_Agent_Setup.iss`:

1. **Step Execution**: Immediately after `SLMS_Client_Agent.exe enroll` returns exit code `0`, Inno Setup performs a filesystem check:
   ```pascal
   EncCredsPath := ExpandConstant('{commonappdata}\SLMS\config\service_credentials.enc');
   if not FileExists(EncCredsPath) then
   begin
     Log(Format('CRITICAL: Enrollment succeeded with exit code 0 but credentials file "%s" was not created!', [EncCredsPath]));
     SuppressibleMsgBox(
       'Workstation enrollment reported success, but service credentials file was not created.' + #13#10#13#10 +
       'The installation cannot proceed.',
       mbCriticalError, MB_OK, MB_OK
     );
     ExecWithLogging(AgentExePath, 'uninstall', '', SW_HIDE, True, ResultCode);
     RollbackFreshInstall();
     WizardForm.Close;
     Exit;
   end;
   ```
2. **Rollback Guarantee**: If `service_credentials.enc` is not present, the installer rolls back, uninstalls any registered service, cleans temporary files, and halts without leaving the machine in a broken or non-starting service state.

---

## 6. Security & Privacy Guarantees

1. **Zero Secret Logging**: Neither `client_secret` nor JWT tokens are ever printed to stdout, stderr, Windows Event Log, or `installer_trace.log`.
2. **Ephemeral Secret Transfer**: The installer transmits the enrollment key to the child agent process via a secure temporary file with restrictive ACLs, immediately shredded/deleted upon completion.
3. **Session 0 Isolation**: The Windows service strictly accesses machine DPAPI storage in `%ProgramData%\SLMS\config\service_credentials.enc` and never interacts with interactive desktop user vaults or GUI prompts.
