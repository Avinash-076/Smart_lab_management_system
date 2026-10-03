# SLMS Client Agent — Audit of Failed Real-World Installation

## Executive Summary

A real-world installation of the SLMS Client Agent was conducted with:
- `SLMS_DEV_MODE=1`
- `SLMS_ALLOW_INSECURE_HTTP=1`

The installer reached *"Verifying service health status..."*, failed after 30 seconds with *"SLMS Windows Service failed to reach RUNNING state within 30 seconds"*, rolled back cleanly, and left no `C:\ProgramData\SLMS\config\service_credentials.enc`.

A forensic investigation of the codebase, timestamps, git diffs, and binary artifacts has established the definitive root cause:

**PRIMARY ROOT CAUSE: THE INSTALLER EXECUTABLE PACKAGED AN OLD PRE-FIX BINARY (Classification B & E).**
The installer artifact `installer/output/SLMS_Client_Agent_Setup.exe` was compiled on **2026-10-03 at 15:39:19 UTC**. The credential-store code fixes were authored between **17:07 and 17:09 UTC**, and the updated PyInstaller executable `client_agent/dist/SLMS_Client_Agent.exe` was generated at **17:33:22 UTC**. The setup installer **was never recompiled** after the code fixes were made. Consequently, the user executed a setup binary containing the un-fixed agent executable from Phase 4/5, which still contained the bug where `SLMS_DEV_MODE=1` diverted credentials to `KeyringCredentialStore` and silently dropped `service_credentials.enc`.

---

## 1. Observed Real-World Evidence

| Observation | Implication |
|---|---|
| Installer reached *"Verifying service health status..."* | Headless enrollment returned exit code `0` (SUCCESS) to the installer wizard; service was installed (`sc.exe create`) and started (`sc.exe start`). |
| Installer failed with 30s timeout | `SLMSService` was started under SCM as `NT SERVICE\SLMSService` (Session 0), but exited or aborted because `service_credentials.enc` did not exist. |
| `C:\ProgramData\SLMS\config\service_credentials.enc` did NOT exist | Headless enrollment did not write the encrypted service credential file. |
| Credential Manager contained no SLMS entries | Confirms previous clean machine state. |
| Post-enrollment sanity check was NOT triggered | The setup script in the working tree contains a check: `if not FileExists(...service_credentials.enc) then RollbackFreshInstallAndAbort('Enrollment completed but encrypted service credentials file was not created on disk.')`. If this check had executed, the installer would have aborted **before** attempting service creation or health verification. The fact that service installation and health verification ran proves the running installer did **not** contain this check. |

---

## 2. Verification of Current Source Code

### 2.1 Credential Store Resolution (`client_agent/core/credentials.py`)

Current lines 515–536:
```python
def get_credential_store() -> BaseCredentialStore:
    global _store_instance
    if _store_instance is not None:
        return _store_instance

    use_keyring = os.environ.get("SLMS_USE_KEYRING", "0").lower() in ("1", "true", "yes")
    service_mode = os.environ.get("SLMS_SERVICE_MODE", "0").lower() in ("1", "true", "yes")

    if use_keyring and not service_mode:
        return KeyringCredentialStore()

    return ServiceCredentialStore()
```

- When `SLMS_DEV_MODE=1`, `SLMS_USE_KEYRING` is unset, and `SLMS_SERVICE_MODE` is unset:
  - `use_keyring` evaluates to `False`.
  - `get_credential_store()` returns **`ServiceCredentialStore()`**.
- `SLMS_DEV_MODE` has been completely decoupled from credential store resolution in the working tree.

### 2.2 Headless Enrollment Flow (`client_agent/server/enroll.py`)

Current lines 46–58, 125–150, 174–215:
- `handle_enroll_cli()` explicitly calls `target_store = _get_target_store(store)`.
- `_get_target_store()` unconditionally returns `ServiceCredentialStore()` when no override is set.
- `handle_enroll_cli()` passes `store=target_store` into `enroll(...)`.
- `enroll()` writes credentials directly to `target_store.save_enrolled_credentials(...)`.
- `except Exception: pass` has been **completely removed**.
- Persistence write is followed by an immediate readability and data-integrity verification step. Any failure raises `RuntimeError` and returns `EnrollmentExitCode.ENROLLMENT_FAILURE` (`8`).

---

## 3. Verification of File Paths & Data Directories (`client_agent/paths.py`)

In `client_agent/paths.py`, lines 25–35:
```python
def get_data_dir() -> str:
    env_dir = os.environ.get("SLMS_DATA_DIR")
    if env_dir:
        return env_dir

    dev_mode = os.environ.get("SLMS_DEV_MODE", "0").lower() in ("1", "true", "yes")
    if dev_mode and not getattr(sys, "frozen", False):
        return BASE_PATH

    program_data = os.environ.get("ProgramData", r"C:\ProgramData")
    return os.path.join(program_data, "SLMS")
```

- In frozen mode (`getattr(sys, "frozen", False)` is `True`):
  - `dev_mode and not getattr(sys, "frozen", False)` evaluates to `False`.
  - `get_data_dir()` returns `C:\ProgramData\SLMS`.
  - `ServiceCredentialStore` stores credentials at `C:\ProgramData\SLMS\config\service_credentials.enc`.
- In non-frozen mode (running Python script directly with `SLMS_DEV_MODE=1`):
  - Returns `BASE_PATH` (repository directory).
- This distinction confirms that in the frozen executable, the target path is always `%ProgramData%\SLMS\config\service_credentials.enc`.

---

## 4. Verification of Environment Inheritance

In `installer/SLMS_Client_Agent_Setup.iss`, lines 578–579:
```pascal
EnrollCmd := '/c ""' + AgentExePath + '" enroll --url "' + ConfiguredServerUrl + '" --key-file "' + TempKeyFile + '" > "' + TempOutFile + '" 2>&1"';
Exec('cmd.exe', EnrollCmd, '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
```
- Inno Setup `Exec('cmd.exe', ...)` inherits the full process environment of the installer.
- When the installer is executed in a terminal where `SLMS_DEV_MODE=1` and `SLMS_ALLOW_INSECURE_HTTP=1` are set, the child `SLMS_Client_Agent.exe enroll` process inherits both flags.
- The installer script does not alter or scrub any `SLMS_*` environment variables.

---

## 5. Artifact Verification & Timestamps (The Core Discrepancy)

Filesystem inspection of the workspace artifacts reveals the exact sequence of events:

| Artifact / Source File | Last Modified (UTC) | State / Content |
|---|:---:|---|
| `installer/output/SLMS_Client_Agent_Setup.exe` | **2026-10-03 15:39:19** | **STALE (Old pre-fix build)** |
| `client_agent/server/enroll.py` | 2026-10-03 17:07:05 | Code fix implemented |
| `installer/SLMS_Client_Agent_Setup.iss` | 2026-10-03 17:07:16 | Post-enrollment check added |
| `client_agent/core/credentials.py` | 2026-10-03 17:09:16 | Code fix implemented |
| `client_agent/dist/SLMS_Client_Agent.exe` | **2026-10-03 17:33:22** | **FRESH (Contains new code)** |

### Analysis of Timestamps:
1. `SLMS_Client_Agent_Setup.exe` was created at **15:39:19 UTC**.
2. The credential store code fixes were written at **17:07–17:09 UTC** (almost 1.5 hours later).
3. The standalone PyInstaller executable was built at **17:33:22 UTC** (almost 2 hours later).
4. **`SLMS_Client_Agent_Setup.exe` was NEVER recompiled after the PyInstaller build.**
5. When the user executed `SLMS_Client_Agent_Setup.exe`, it extracted the old embedded executable from 15:39:19 UTC into `C:\Program Files\SLMS\`.
6. That old executable contained the pre-fix code:
   ```python
   # Old pre-fix logic embedded inside the 15:39:19 installer
   if (dev_mode or use_keyring) and not service_mode:
       return KeyringCredentialStore()
   ```
7. Consequently, headless enrollment ran under `SLMS_DEV_MODE=1`, selected `KeyringCredentialStore`, silently failed to write `service_credentials.enc` due to `except Exception: pass`, and returned exit code 0.
8. Because the installer script itself was also the 15:39:19 version, it lacked the post-enrollment filesystem sanity check, proceeded to install `SLMSService`, attempted to start it, timed out after 30 seconds because `service_credentials.enc` was missing, and rolled back.

---

## 6. Test Suite Gap Analysis (Why 390 Tests Passed)

All 390 pytest tests passed because of test structure limitations:

1. **`test_installer_script.py`**:
   - Reads `SLMS_Client_Agent_Setup.iss` as text from disk.
   - Verified that the sanity check *text* exists in the `.iss` file.
   - `test_compiled_installer_binary_exists()` only asserted:
     ```python
     assert SETUP_EXE.is_file()
     assert SETUP_EXE.stat().st_size > 10 * 1024 * 1024
     ```
   - It did **not** check whether `SETUP_EXE` was newer than `client_agent/dist/SLMS_Client_Agent.exe` or `SLMS_Client_Agent_Setup.iss`.

2. **`test_installer_e2e_simulation.py`**:
   - Simulates lifecycle events by invoking in-memory Python classes.
   - Explicitly passed `store=fresh_service_store` to `handle_enroll_cli(..., store=fresh_service_store)` (e.g. line 351).
   - Mocked DPAPI using `SLMS_MOCK_DPAPI=1`.
   - Never executed the compiled `SLMS_Client_Agent_Setup.exe` installer or the compiled `dist\SLMS_Client_Agent.exe` binary.

3. **`test_enrollment_cli.py`**:
   - Tests `handle_enroll_cli()` against the in-memory Python working-tree modules.
   - Verified that the working-tree Python code is correct, but could not detect that the compiled installer was stale.

---

## 7. Root Cause Classification

### Primary Root Cause
**B. INSTALLER PACKAGED OLD EXE**
The installer executable `installer/output/SLMS_Client_Agent_Setup.exe` was never rebuilt after the code fixes were made and after PyInstaller was run. It contained the old binary with the original defects.

### Contributing Cause
**E. TESTS DO NOT ACTUALLY COVER THE REAL PATH / ARTIFACT FRESHNESS**
`test_compiled_installer_binary_exists()` did not validate artifact timestamp freshness relative to the compiled EXE or ISS source script.

---

## 8. Recommended Fix Direction (Non-Code Action Plan)

1. **Locate Inno Setup 6 Compiler (`ISCC.exe`)**:
   - Inno Setup 6 must be installed or located on the host. Common installation paths include:
     - `C:\Program Files (x86)\Inno Setup 6\ISCC.exe`
     - `C:\Program Files\Inno Setup 6\ISCC.exe`
     - User Local AppData path: `C:\Users\<user>\AppData\Local\Programs\Inno Setup 6\ISCC.exe`
2. **Recompile `SLMS_Client_Agent_Setup.iss`**:
   - Run `ISCC.exe "installer\SLMS_Client_Agent_Setup.iss"` to package the newly built `client_agent\dist\SLMS_Client_Agent.exe` (17:33:22 UTC) into a fresh `SLMS_Client_Agent_Setup.exe`.
3. **Enhance Test `test_compiled_installer_binary_exists`**:
   - Add a check asserting `SETUP_EXE.stat().st_mtime >= DIST_EXE.stat().st_mtime` to ensure stale installer packages fail automated test runs immediately.
