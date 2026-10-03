# SLMS Client Agent - Headless Enrollment CLI

This developer document specifies the non-interactive/headless enrollment CLI interface implemented in Phase 1 of the Windows installer project.

---

## 1. Overview & Purpose

The headless enrollment interface allows automated provisioning tools (such as Inno Setup installers, Active Directory GPO scripts, or SCCM/Intune deployment tasks) to register a workstation with the SLMS backend without requiring interactive console input or launching the Tkinter GUI.

---

## 2. CLI Syntax & Supported Arguments

```cmd
SLMS_Client_Agent.exe enroll [-h] [--url URL] [--key KEY | --stdin-key | --key-file KEY_FILE] [--force]
```

### Arguments:
| Flag | Description | Mandatory / Optional |
| :--- | :--- | :--- |
| `--url <URL>` | Target SLMS server base URL (e.g. `https://slms.lab.university.edu:8000`). If omitted, falls back to `SLMS_API_URL` environment variable or standard production default. | Optional |
| `--key <KEY>` | Direct enrollment key string. | One of `--key`, `--stdin-key`, or `--key-file` is required |
| `--stdin-key`, `--key-stdin` | Instructs the agent to read the enrollment key from standard input (`sys.stdin`). Useful for zero command-line process exposure. | One of `--key`, `--stdin-key`, or `--key-file` is required |
| `--key-file <PATH>` | Path to a file containing the enrollment key. The key is read, trimmed, and never retained on disk. | One of `--key`, `--stdin-key`, or `--key-file` is required |
| `--force` | Force overwrite existing enrollment credentials in the DPAPI machine credential store. | Optional (Default: `False`) |

---

## 3. Security Design

1. **Process Inspection Protection**:
   - For environments where process command lines can be queried via WMI or Task Manager, the installer can pass the key via `--stdin-key` (piped stream) or `--key-file` (ephemeral admin-protected file).
2. **Zero-Secret Invariant**:
   - The enrollment key, `client_secret`, and JWT access tokens are **never** logged to `client.log`, stdout, or stderr.
   - Exception handling strictly sanitizes error descriptions and excludes request bodies or header dumps.
3. **Transport Security**:
   - Enforces strict HTTPS/WSS in production mode. Plaintext HTTP is rejected with exit code `2` (`INVALID_SERVER_URL`) unless `SLMS_ALLOW_INSECURE_HTTP=1` is explicitly set for development/testing.

---

## 4. Exit Codes

Predictable numeric exit codes returned to the calling installer or script:

| Code | Name | Meaning | Actionable Resolution |
| :---: | :--- | :--- | :--- |
| **0** | `SUCCESS` | Workstation enrolled successfully. | Proceed to service installation/startup. |
| **1** | `INVALID_ARGUMENT` | Missing or empty key, invalid argument combination, or missing key file. | Verify command line syntax. |
| **2** | `INVALID_SERVER_URL` | Malformed URL or insecure `http://` scheme in production. | Check Server URL format; ensure `https://` is used. |
| **3** | `ALREADY_ENROLLED` | Workstation is already enrolled and `--force` was not specified. | Use `--force` if deliberate re-enrollment is intended. |
| **4** | `INVALID_OR_EXPIRED_KEY` | Backend rejected key (`401 Unauthorized`). | Check enrollment key validity in SLMS Admin Portal. |
| **5** | `DUPLICATE_COMPUTER` | Hostname or MAC address already registered (`409 Conflict`). | Decommission old computer record in Admin Portal or rename host. |
| **6** | `SERVER_UNREACHABLE` | Connection timeout, DNS failure, network down, or HTTP 5xx error. | Verify server status, firewall, and LAN reachability. |
| **7** | `TLS_SECURITY_FAILURE` | SSL/TLS certificate verification failed (`SSLError`). | Verify valid TLS certificate on server or configure `SLMS_CA_BUNDLE`. |
| **8** | `ENROLLMENT_FAILURE` | Other HTTP 4xx errors or malformed backend JSON payload. | Check backend server logs and API compatibility. |
| **9** | `UNEXPECTED_ERROR` | Unhandled runtime exception or OS error. | Inspect Windows Event Log / application diagnostics. |

---

## 5. Already-Enrolled & Force Behavior

- **Default (`--force` omitted)**:
  - If `is_enrolled()` is `True`, enrollment immediately terminates without contacting the server or altering credentials.
  - Stderr: `"Enrollment rejected: Workstation is already enrolled. Use --force to overwrite existing enrollment credentials."`
  - Exit code: `3`.
- **Force Re-enrollment (`--force` present)**:
  - Contacts backend with new key.
  - Existing DPAPI credentials are only replaced upon receiving a successful `201 Created` response from the backend, ensuring a failed re-enrollment never leaves the workstation in a half-configured state.

---

## 6. Examples

### Successful Direct Invocation:
```cmd
"C:\Program Files\SLMS\SLMS_Client_Agent.exe" enroll --url "https://slms.lab.edu:8000" --key "SLMS-7K9A-4B2X-99PQ"
```
Output:
```
Enrollment successful.
Computer ID: 42
```
Exit code: `0`

### Successful Piped Stdin Invocation:
```powershell
"SLMS-7K9A-4B2X-99PQ" | & "C:\Program Files\SLMS\SLMS_Client_Agent.exe" enroll --url "https://slms.lab.edu:8000" --stdin-key
```
Output:
```
Enrollment successful.
Computer ID: 42
```
Exit code: `0`

### Expired Key Failure:
```cmd
"C:\Program Files\SLMS\SLMS_Client_Agent.exe" enroll --url "https://slms.lab.edu:8000" --key "SLMS-EXPIRED-KEY"
```
Stderr:
```
Enrollment failed.
Reason: Enrollment key is invalid, expired, or already used.
```
Exit code: `4`
