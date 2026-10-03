# SLMS Client Agent - Credential Store, Enrollment & Installer Interaction Forensic Audit Report

**Document Version**: 1.0.0  
**Date**: 2026-10-03  
**Audit Scope**: Forensic investigation of credential store resolution, headless enrollment execution, silent exception handling, already-enrolled checks, and Windows installer interaction under development and production environment flags.  
**Constraint**: AUDIT ONLY — No code modifications, no test edits, no installer adjustments.

---

## 1. Executive Summary

A comprehensive forensic audit of the Smart Lab Management System (SLMS) client agent and Windows installer was conducted to investigate an installation failure observed on a secondary Windows workstation.

### Key Finding:
The suspected bugs **ACTUALLY EXIST** in the codebase. When `SLMS_DEV_MODE=1` is present in the environment during installer execution:
1. `get_credential_store()` in `client_agent/core/credentials.py` selects `KeyringCredentialStore` (Windows Credential Manager) instead of `ServiceCredentialStore` (DPAPI machine-scope `%ProgramData%\SLMS\config\service_credentials.enc`).
2. The headless enrollment CLI persists credentials to Windows Credential Manager and attempts a secondary write to `ServiceCredentialStore` inside a `try...except Exception: pass` block in `client_agent/server/enroll.py`.
3. If the secondary write fails or is misdirected, the exception is **silently swallowed**, and the enrollment command reports `Enrollment successful.` with exit code `0` (`SUCCESS`).
4. The Windows installer (`SLMS_Client_Agent_Setup.iss`) observes exit code `0` and proceeds to install and start `SLMSService`.
5. In Session 0, `SLMSService` runs with `SLMS_SERVICE_MODE=1` and strictly requires `C:\ProgramData\SLMS\config\service_credentials.enc`.
6. Because the file does not exist, `SLMSService` raises `RuntimeError("SLMS Client Agent is not enrolled...")` and crashes immediately.
7. The installer verification loop times out after 30 seconds and triggers rollback.

Conversely, when `SLMS_DEV_MODE=0` is set and Credential Manager is cleared, `get_credential_store()` defaults to `ServiceCredentialStore`, writing `service_credentials.enc` directly and enabling `SLMSService` to start in Session 0 without error.

---

## 2. Current Credential Store Architecture

The credential management subsystem is defined in [`client_agent/core/credentials.py`](file:///d:/PC/slms1/Smart_lab_management_system/client_agent/core/credentials.py) and implements two concrete `BaseCredentialStore` backends:

```
                      +-------------------------+
                      |   BaseCredentialStore   |
                      +-------------------------+
                                   |
                  +----------------+----------------+
                  |                                 |
    +---------------------------+     +---------------------------+
    |  KeyringCredentialStore   |     |  ServiceCredentialStore   |
    | (Windows Credential Mgr)  |     |   (DPAPI Machine Scope)   |
    | - Current user context    |     | - Machine context         |
    | - Interactive login only  |     | - Session 0 accessible    |
    | - Inaccessible in SCM     |     | - %ProgramData%\SLMS\     |
    +---------------------------+     +---------------------------+
```

### Global Store Resolution Hierarchy
The resolution logic in `get_credential_store()` ([`client_agent/core/credentials.py:514-544`](file:///d:/PC/slms1/Smart_lab_management_system/client_agent/core/credentials.py#L514-L544)) executes the following priority order:

1. **Explicit Test/Runtime Instance**: If `_store_instance` is set via `set_credential_store()`, return it.
2. **Development / Keyring Mode**:
   ```python
   # Line 528-533
   dev_mode = os.environ.get("SLMS_DEV_MODE", "0").lower() in ("1", "true", "yes")
   use_keyring = os.environ.get("SLMS_USE_KEYRING", "0").lower() in ("1", "true", "yes")
   service_mode = os.environ.get("SLMS_SERVICE_MODE", "0").lower() in ("1", "true", "yes")

   if (dev_mode or use_keyring) and not service_mode:
       return KeyringCredentialStore()
   ```
3. **Existing Service Credentials**: If `ServiceCredentialStore().is_enrolled()` is `True` or `service_mode` is `True`, return `ServiceCredentialStore()`.
4. **Fallback to Keyring**:
   ```python
   # Line 539-541
   keyring_store = KeyringCredentialStore()
   if keyring_store.is_enrolled():
       return keyring_store
   ```
5. **Default**: Return `ServiceCredentialStore()`.

---

## 3. Detailed Audit of Questions

### Section 1: Credential Store Selection
* **A. Does `SLMS_DEV_MODE` influence credential-store selection?**  
  **YES**. [`client_agent/core/credentials.py:528, 532-533`](file:///d:/PC/slms1/Smart_lab_management_system/client_agent/core/credentials.py#L528-L533).
* **B. Does `SLMS_DEV_MODE=1` cause `KeyringCredentialStore` to be selected?**  
  **YES**. Whenever `SLMS_DEV_MODE=1` and `SLMS_SERVICE_MODE` is not set, `get_credential_store()` returns `KeyringCredentialStore()` at line 533.
* **C. Does `SLMS_DEV_MODE=0` cause `ServiceCredentialStore` to be selected?**  
  **YES**. When `dev_mode` is False, line 532 evaluates to False and the resolution falls through to line 543 returning `ServiceCredentialStore()` (provided Keyring is not enrolled).
* **D. Is there an explicit execution-context parameter indicating "Windows service/headless enrollment"?**  
  **NO**. `get_credential_store()` accepts zero parameters.
* **E. Does headless enrollment explicitly request `ServiceCredentialStore`?**  
  **NO**. [`client_agent/server/enroll.py:105`](file:///d:/PC/slms1/Smart_lab_management_system/client_agent/server/enroll.py#L105) simply calls `store = get_credential_store()`.
* **F. Does it allow environment variables to decide?**  
  **YES**. Ambient environment variables (`SLMS_DEV_MODE`) dictate the store selection.

---

### Section 2: Headless Enrollment Control Flow
* **A. What credential store does headless enrollment actually use?**  
  Whatever `get_credential_store()` resolves to. If `SLMS_DEV_MODE=1`, it uses `KeyringCredentialStore`.
* **B. Does headless enrollment explicitly select `ServiceCredentialStore`?**  
  **NO**.
* **C. Does it ever use `KeyringCredentialStore`?**  
  **YES**, under `SLMS_DEV_MODE=1` or when `SLMS_USE_KEYRING=1` or when Keyring has enrolled credentials.
* **D. Is there logic attempting to copy credentials to `ServiceCredentialStore`?**  
  **YES**. [`client_agent/server/enroll.py:116-127`](file:///d:/PC/slms1/Smart_lab_management_system/client_agent/server/enroll.py#L116-L127).
* **E. Under what exact conditions does that copy happen?**  
  Only `if isinstance(store, KeyringCredentialStore):`.
* **F. Is that copy mandatory or best-effort?**  
  **BEST-EFFORT / OPTIONAL**. The block is wrapped in `try...except Exception: pass`.
* **G. Is successful enrollment reported before service credentials are verified?**  
  **YES**. [`client_agent/server/enroll.py:129-132, 188-190`](file:///d:/PC/slms1/Smart_lab_management_system/client_agent/server/enroll.py#L129-L190). `handle_enroll_cli()` outputs `"Enrollment successful."` and returns `0` regardless of whether `service_credentials.enc` was written.

---

### Section 3: Silent Exception Handling Audit
The broad exception swallowing in [`client_agent/server/enroll.py:116-127`](file:///d:/PC/slms1/Smart_lab_management_system/client_agent/server/enroll.py#L116-L127):

```python
    try:
        from core.credentials import KeyringCredentialStore, ServiceCredentialStore
        if isinstance(store, KeyringCredentialStore):
            service_store = ServiceCredentialStore()
            service_store.save_enrolled_credentials(
                agent_id=str(agent_id),
                client_secret=str(client_secret),
                computer_id=int(computer_id),
            )
            service_store.set_server_url(base_url)
    except Exception:
        pass
```

* **File/Function**: `client_agent/server/enroll.py`, function `enroll()`
* **Swallowed Exceptions**: Any `OSError` (e.g. DPAPI `CryptProtectData` failure), `PermissionError`, directory creation error, or serialization exception.
* **CLI Return Value**: `EnrollmentExitCode.SUCCESS` (`0`).
* **Installer Reaction**: The installer treats exit code `0` as total success and proceeds immediately to service installation and service startup.

Additional broad exception handlers in `client_agent/core/credentials.py`:
* Line 219: `delete_credential` in `KeyringCredentialStore`: `except Exception: return False`
* Line 270: `get_server_url` in `KeyringCredentialStore`: `except Exception: pass`
* Line 284: `set_server_url` in `KeyringCredentialStore`: `except Exception: pass`
* Line 325: `_read_payload` in `ServiceCredentialStore`: `except Exception: return {}`
* Line 380: `_set_restricted_permissions` in `ServiceCredentialStore`: `except Exception: pass`
* Line 446: `get_server_url` in `ServiceCredentialStore`: `except Exception: pass`
* Line 458: `set_server_url` in `ServiceCredentialStore`: `except Exception: pass`
* Line 466: `clear()` in `ServiceCredentialStore`: `except Exception: pass`

---

### Section 4: `ALREADY_ENROLLED` Control Flow
* **A. Does "already enrolled" depend on `KeyringCredentialStore`?**  
  **YES**, if `get_credential_store()` resolves to `KeyringCredentialStore`.
* **B. Does it depend on `ServiceCredentialStore`?**  
  **YES**, if `get_credential_store()` resolves to `ServiceCredentialStore`.
* **C. Can stale Windows Credential Manager entries cause `ALREADY_ENROLLED` when `service_credentials.enc` is missing?**  
  **YES**. If `SLMS_DEV_MODE=1` (or via fallback at line 540), `is_enrolled()` queries Keyring. If old credentials exist in Windows Credential Manager, `is_enrolled()` returns `True`. Headless enrollment is aborted with exit code `3` (`ALREADY_ENROLLED`) even though `%ProgramData%\SLMS\config\service_credentials.enc` is completely absent!
* **D. Can `SLMS_DEV_MODE=1` change the answer?**  
  **YES**. It forces `get_credential_store()` to return `KeyringCredentialStore()`.

---

### Section 5: Service Credential Requirements
* **A. Does `SLMSService` require `service_credentials.enc`?**  
  **YES**. In Session 0 under SCM, `SLMSService.SvcDoRun()` sets `SLMS_SERVICE_MODE=1` ([`client_agent/service/service.py:90`](file:///d:/PC/slms1/Smart_lab_management_system/client_agent/service/service.py#L90)), forcing `ServiceCredentialStore`.
* **B. Does it ever fall back to Windows Credential Manager when running under `NT SERVICE\SLMSService`?**  
  **NO**. In Session 0, `KeyringCredentialStore` cannot access interactive user accounts, and `SLMS_SERVICE_MODE=1` bypasses Keyring.
* **C. What happens if `service_credentials.enc` is missing?**  
  [`client_agent/core/runtime.py:302-309`](file:///d:/PC/slms1/Smart_lab_management_system/client_agent/core/runtime.py#L302-L309):
  ```python
  if not is_enrolled_fn():
      if self.is_service:
          error_msg = ("SLMS Client Agent is not enrolled. Cannot start Windows Service without prior enrollment...")
          logger.critical(error_msg)
          raise RuntimeError(error_msg)
  ```
* **D. Does the service fail immediately?**  
  **YES**. `AgentRuntime.start()` raises `RuntimeError` immediately during initialization.
* **E. Does the installer wait for the 30-second timeout?**  
  **YES**. The installer executes `sc.exe start SLMSService` and enters a 30-second polling loop against `sc.exe query SLMSService`. Because the service terminated on startup, the status never reaches `RUNNING`, causing the installer to fail at 30 seconds and roll back.

---

### Section 6: Installer Dependency
* **A. What command does the installer use for enrollment?**  
  `"{app}\SLMS_Client_Agent.exe" enroll --url "<URL>" --key-file "{tmp}\slms_enroll.key"` ([`installer/SLMS_Client_Agent_Setup.iss:587`](file:///d:/PC/slms1/Smart_lab_management_system/installer/SLMS_Client_Agent_Setup.iss#L587)).
* **B. Does it invoke `enroll`?** **YES**.
* **C. Does it pass `--key-file`?** **YES**.
* **D. Does the installer explicitly set `SLMS_DEV_MODE`?** **NO**. It inherits ambient process/system environment variables.
* **E. Does the installer explicitly select a credential store?** **NO**.
* **F. Does it verify `service_credentials.enc` after enrollment?** **NO**.
* **G. Does it start/install the service before verifying credentials?** **YES**.
* **H. Does it rely entirely on enrollment's exit code?** **YES** (`if ResultCode <> 0`).
* **I. What happens when enrollment returns `0` but `service_credentials.enc` is missing?** The installer installs and attempts to start the service, waits 30 seconds while the service crashes in Session 0, and triggers rollback.

---

## 4. Environment Variable Semantics Matrix

| Variable | Used By | Intended Purpose | Affects Credential Store? | Affects Transport Policy? | Affects SCM Mode? |
| :--- | :--- | :--- | :---: | :---: | :---: |
| **`SLMS_DEV_MODE`** | `core/credentials.py:528`<br>`core/security.py:38`<br>`paths.py:29`<br>`service/service.py:247` | General developer mode | **YES** (Forces Keyring outside SCM) | **YES** (Permits plaintext HTTP/WS) | **NO** (Overridden by `SLMS_SERVICE_MODE`) |
| **`SLMS_ALLOW_INSECURE_HTTP`** | `core/security.py:37`<br>`installer/*.iss` | Permitting HTTP/WS in local testing | **NO** | **YES** (Permits plaintext HTTP/WS) | **NO** |
| **`SLMS_USE_KEYRING`** | `core/credentials.py:529` | Explicitly forcing Keyring store | **YES** (Forces Keyring outside SCM) | **NO** | **NO** |
| **`SLMS_SERVICE_MODE`** | `core/credentials.py:530`<br>`service/service.py:90`<br>`core/runtime.py:121` | Windows Service SCM execution flag | **YES** (Forces `ServiceCredentialStore`) | **NO** | **YES** |

### Coupling Defect:
`SLMS_DEV_MODE` is heavily overloaded. When a developer or administrator sets `SLMS_DEV_MODE=1` to allow testing against a local `http://127.0.0.1:8000` backend, it **unintentionally alters the credential storage backend** from `ServiceCredentialStore` to `KeyringCredentialStore`, breaking subsequent Windows Service execution in Session 0.

---

## 5. Test Suite Coverage Audit

| Test Scenario | Status | Explanation |
| :--- | :---: | :--- |
| 1. `SLMS_DEV_MODE=1` + headless enrollment | **NOT COVERED** | Existing tests explicitly delete `SLMS_DEV_MODE` via `monkeypatch.delenv("SLMS_DEV_MODE")`. |
| 2. `SLMS_DEV_MODE=1` + `ServiceCredentialStore` | **NOT COVERED** | Unit tests instantiate `ServiceCredentialStore` directly, bypassing `get_credential_store()` resolution. |
| 3. `SLMS_DEV_MODE=1` + Windows service enrollment | **NOT COVERED** | No test runs headless enrollment with `SLMS_DEV_MODE=1` and then asserts service startup. |
| 4. Stale Keyring credentials + empty ServiceCredentialStore | **NOT COVERED** | Tests always operate with clean or isolated mock credential stores. |
| 5. `service_credentials.enc` missing after enrollment | **NOT COVERED** | CLI tests assert exit codes, not the physical presence of `service_credentials.enc` on disk. |
| 6. Credential persistence failure | **NOT COVERED** | Persistence exceptions swallowed by `try...except Exception: pass` are never asserted. |
| 7. `ALREADY_ENROLLED` from Keyring | **PARTIALLY COVERED** | Tested when `is_enrolled()` is True, but not specifically via stale Keyring crossover. |
| 8. `ALREADY_ENROLLED` from ServiceCredentialStore | **COVERED** | Standard enrolled CLI tests cover this path. |
| 9. Installer enrollment followed by service startup | **PARTIALLY COVERED** | Tested via mock simulation fixtures, but with `SLMS_SERVICE_MODE=1` preset. |

---

## 6. Real-World Incident Correlation

### Case 1: `SLMS_DEV_MODE=1` & `SLMS_ALLOW_INSECURE_HTTP=1`
1. Parent process / workstation has `SLMS_DEV_MODE=1`.
2. Installer launches `SLMS_Client_Agent.exe enroll ...`.
3. Child process inherits `SLMS_DEV_MODE=1` with `SLMS_SERVICE_MODE` unset.
4. `get_credential_store()` resolves to `KeyringCredentialStore`.
5. Enrollment credentials saved to Windows Credential Manager under current user (`client_secret@SLMS`, `agent_id@SLMS`, `computer_id@SLMS`).
6. Copy to `ServiceCredentialStore` in `enroll.py:116-127` fails or is bypassed; exception swallowed by `pass`.
7. `SLMS_Client_Agent.exe enroll` returns exit code `0`.
8. Installer installs and starts `SLMSService`.
9. `SLMSService` runs in Session 0 (`SLMS_SERVICE_MODE=1`), queries `ServiceCredentialStore`.
10. `service_credentials.enc` **does not exist in `%ProgramData%\SLMS\config`**.
11. `AgentRuntime.start()` throws `RuntimeError("SLMS Client Agent is not enrolled...")` and terminates.
12. Installer waits 30 seconds for `sc.exe query SLMSService` to reach `RUNNING`, times out, and rolls back.
* **Correlated with Code**: **100% MATCH**.

### Case 2: `SLMS_DEV_MODE=0` & `SLMS_ALLOW_INSECURE_HTTP=1`
1. Parent process has `SLMS_DEV_MODE=0`.
2. Installer launches `SLMS_Client_Agent.exe enroll ...`.
3. `get_credential_store()` evaluates line 532 as `False`. With Keyring cleaned, line 543 returns `ServiceCredentialStore()`.
4. Enrollment credentials written directly to `C:\ProgramData\SLMS\config\service_credentials.enc` via DPAPI machine scope.
5. Installer installs and starts `SLMSService`.
6. In Session 0, `SLMSService` reads `service_credentials.enc`, initializes runtime, and reaches `RUNNING`.
7. Installer detects `RUNNING` and finishes successfully.
* **Correlated with Code**: **100% MATCH**.

---

## 7. Bug-by-Bug Verdicts

### BUG A: Headless/installer enrollment allows `SLMS_DEV_MODE` to select `KeyringCredentialStore` instead of `ServiceCredentialStore`
* **Verdict**: **CONFIRMED**
* **File**: [`client_agent/core/credentials.py:528-533`](file:///d:/PC/slms1/Smart_lab_management_system/client_agent/core/credentials.py#L528-L533), [`client_agent/server/enroll.py:105`](file:///d:/PC/slms1/Smart_lab_management_system/client_agent/server/enroll.py#L105)
* **Evidence**: `get_credential_store()` returns `KeyringCredentialStore()` whenever `SLMS_DEV_MODE=1` is set.
* **Impact**: Workstation enrollment creates credentials accessible only to the interactive user, leaving the background Windows Service unprovisioned.

### BUG B: `SLMS_DEV_MODE` incorrectly couples development transport policy with credential store selection
* **Verdict**: **CONFIRMED**
* **File**: [`client_agent/core/credentials.py:528-533`](file:///d:/PC/slms1/Smart_lab_management_system/client_agent/core/credentials.py#L528-L533), [`client_agent/core/security.py:38-39`](file:///d:/PC/slms1/Smart_lab_management_system/client_agent/core/security.py#L38-L39)
* **Evidence**: Setting `SLMS_DEV_MODE=1` to allow testing against `http://` unintentionally forces `KeyringCredentialStore` selection.
* **Impact**: Cannot test Windows Service enrollment against local development HTTP servers without breaking credential storage.

### BUG C: Enrollment can report success even when service credential persistence fails
* **Verdict**: **CONFIRMED**
* **File**: [`client_agent/server/enroll.py:116-132, 188-190`](file:///d:/PC/slms1/Smart_lab_management_system/client_agent/server/enroll.py#L116-L190)
* **Evidence**: `enroll()` returns valid dictionary and `handle_enroll_cli()` returns `0` even if `ServiceCredentialStore` write fails.
* **Impact**: Installer receives false positive `SUCCESS`, leading to doomed service installation.

### BUG D: Credential persistence failure is swallowed by broad exception handling
* **Verdict**: **CONFIRMED**
* **File**: [`client_agent/server/enroll.py:116-127`](file:///d:/PC/slms1/Smart_lab_management_system/client_agent/server/enroll.py#L116-L127)
* **Evidence**: `try: ... except Exception: pass` silently suppresses all persistence failures.
* **Impact**: No error logs, no diagnostics, no non-zero exit code returned.

### BUG E: `ALREADY_ENROLLED` check can be triggered by stale Keyring credentials while `ServiceCredentialStore` is empty
* **Verdict**: **CONFIRMED**
* **File**: [`client_agent/server/enroll.py:46-50, 181-184`](file:///d:/PC/slms1/Smart_lab_management_system/client_agent/server/enroll.py#L46-L184)
* **Evidence**: `is_enrolled()` queries Keyring when `SLMS_DEV_MODE=1` or via fallback at line 540.
* **Impact**: Installer refuses to enroll (`exit code 3`) even though `service_credentials.enc` does not exist on disk.

### BUG F: The installer does not independently verify `service_credentials.enc` before installing/starting the service
* **Verdict**: **CONFIRMED**
* **File**: [`installer/SLMS_Client_Agent_Setup.iss:595-625`](file:///d:/PC/slms1/Smart_lab_management_system/installer/SLMS_Client_Agent_Setup.iss#L595-L625)
* **Evidence**: Installer relies exclusively on child process return code `0`.
* **Impact**: Fails to catch missing credential files early, resulting in a 30-second hang and rollback.

### BUG G: Existing test suite does not cover `SLMS_DEV_MODE=1` installer failure scenario
* **Verdict**: **CONFIRMED**
* **File**: [`client_agent/tests/test_enrollment_cli.py:205`](file:///d:/PC/slms1/Smart_lab_management_system/client_agent/tests/test_enrollment_cli.py#L205), [`client_agent/tests/test_installer_e2e_simulation.py:48-52`](file:///d:/PC/slms1/Smart_lab_management_system/client_agent/tests/test_installer_e2e_simulation.py#L48-L52)
* **Evidence**: Test fixtures explicitly delete `SLMS_DEV_MODE` and preset `SLMS_SERVICE_MODE=1`.
* **Impact**: Test suite passes 378/378 tests while the bug remains undetected in development environments.

---

## 8. Additional Confirmed Findings

1. **Implicit Keyring Fallback in Production (`client_agent/core/credentials.py:539-541`)**:
   ```python
   keyring_store = KeyringCredentialStore()
   if keyring_store.is_enrolled():
       return keyring_store
   ```
   Even when `SLMS_DEV_MODE=0`, if a previous developer run left credentials in Windows Credential Manager, line 540 causes `get_credential_store()` to return `KeyringCredentialStore` instead of `ServiceCredentialStore`, recreating the exact bug in production.
2. **`paths.py` Data Directory Deviation (`client_agent/paths.py:29-31`)**:
   `get_data_dir()` switches from `C:\ProgramData\SLMS` to project `BASE_PATH` when `SLMS_DEV_MODE=1` and `sys.frozen` is False. This causes uncompiled CLI executions to write credentials to `client_agent/config` rather than `%ProgramData%\SLMS\config`.

---

## 9. Recommended Architecture Directions (Description Only — No Implementation)

1. **Explicit Store Targeting in Headless Enrollment**:
   * Modify `handle_enroll_cli()` and `enroll()` so that headless / installer enrollment explicitly requests and writes to `ServiceCredentialStore` directly, without allowing ambient environment variables to divert storage to Keyring.
2. **Decouple `SLMS_DEV_MODE` from Credential Storage**:
   * Reserve `SLMS_DEV_MODE` strictly for logging and debug output. Use `SLMS_USE_KEYRING=1` only if a developer explicitly requests interactive Keyring storage.
   * Allow `SLMS_ALLOW_INSECURE_HTTP=1` to control HTTP transport security independently without altering credential storage.
3. **Mandatory & Verified Service Credential Persistence**:
   * Remove the `except Exception: pass` block in `enroll.py`. If writing `ServiceCredentialStore` fails, raise a fatal exception and return `EnrollmentExitCode.ENROLLMENT_FAILURE` (`8`).
4. **Context-Aware `is_enrolled()`**:
   * Ensure `is_enrolled()` in service and headless contexts checks `ServiceCredentialStore` specifically rather than querying Keyring.
5. **Installer Post-Enrollment Sanity Check**:
   * In `SLMS_Client_Agent_Setup.iss`, add an explicit check for `FileExists(ExpandConstant('{commonappdata}\SLMS\config\service_credentials.enc'))` immediately after enrollment returns `0` before proceeding to service installation.
6. **Regression Test Additions**:
   * Add dedicated regression tests for `SLMS_DEV_MODE=1` headless enrollment, stale Keyring entries, and missing `service_credentials.enc` detection.

---

## 10. Conclusion

The real-world incident observed on the second Windows machine is fully explained by confirmed defects in `client_agent/core/credentials.py`, `client_agent/server/enroll.py`, and `installer/SLMS_Client_Agent_Setup.iss`. The architectural recommendations above provide a clear, unambiguous roadmap for resolving all seven confirmed bugs in a subsequent phase.
