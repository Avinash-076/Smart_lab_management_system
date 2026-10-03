# Phase 10 — Physical 40-Workstation Lab Validation Protocol

> **STATUS:** AWAITING PHYSICAL LAB EXECUTION  
> **Target Scope:** 40 Physical Lab PCs + Dedicated Lab Server  
> **Reference:** Phase 10 Testing & Quality Implementation (Requirement J-12)

---

## 1. Executive Summary & Purpose

This protocol specifies the standard operating procedure (SOP) for validating the Smart Lab Management System (SLMS) Client Agent across 40 physical Windows workstations in an authentic educational laboratory environment.

While automated test suites (J-01 through J-10) and the headless 40-client simulator (`testing_scripts/load_40_clients.py` / J-11) validate code logic and synthetic protocol concurrency, physical validation verifies real-world hardware variance, physical network contention, Windows Session 0 boot-time behavior, and power-cycle events.

**IMPORTANT:** This document represents the official validation protocol. Physical lab execution is conducted on-site on physical hardware and is documented in the final lab sign-off report.

---

## 2. Prerequisites

### 2.1 Hardware Requirements
- **Workstations (40 PCs):** Standard lab desktop PCs running Windows 10/11 Enterprise or Pro (x64).
- **Server (1 Machine):** Dedicated physical or VM host (minimum 4 vCPUs, 8 GB RAM, 100 GB SSD).
- **Network Switch:** 48-port Gigabit managed switch connecting all 40 PCs and the server on a dedicated lab VLAN.

### 2.2 Software & Network Requirements
- Static IP allocation or DHCP reservation for all 40 PCs.
- DNS resolution or hosts entry resolving `slms.lab.internal` to the server IP.
- TLS 1.3 / HTTPS certificate trusted by all workstations (Internal CA root installed).
- Python 3.13+ runtime environment or packaged SLMS Agent executable deployed to `%ProgramFiles%\SLMS`.
- Local Administrator access on all 40 workstations.

---

## 3. Server Setup & Preparation

1. **Database Initialization:**
   ```bash
   cd backend
   alembic upgrade head
   ```
2. **Server Launch:**
   Run the production FastAPI service with Uvicorn behind Nginx/Caddy with TLS:
   ```bash
   uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
   ```
3. **Generate Multi-Use Enrollment Key:**
   Log in to the SLMS Administrative Dashboard or execute CLI:
   - Create key with `max_uses = 50`, `expires_at = NOW + 24 hours`.
   - Record the plaintext key: `SLMS-LAB40-XXXX-YYYY-ZZZZ`.

---

## 4. Workstation Deployment & Enrollment

1. **Deploy Files to Workstation:**
   Copy agent distribution to `C:\Program Files\SLMS\client_agent`.
2. **Enroll Agent:**
   Execute enrollment under Administrator context:
   ```powershell
   python.exe -m server.enroll --key SLMS-LAB40-XXXX-YYYY-ZZZZ --server https://slms.lab.internal
   ```
3. **Verify Credential Migration to DPAPI Machine Store:**
   Ensure credentials are saved in `%PROGRAMDATA%\SLMS\config\credentials.json.enc` protected with machine-scope DPAPI.
4. **Install and Start Windows Service:**
   ```powershell
   python.exe service\service.py install
   python.exe service\service.py start
   ```

---

## 5. Verification Test Cases

| Test ID | Procedure | Expected Result | Pass/Fail | Evidence |
|---|---|---|---|---|
| **TC-01: Service Registration** | Check SCM status on each PC: `sc.exe query SLMSService` | State = `RUNNING`, StartType = `AUTO_START`, Account = `NT SERVICE\SLMSService` | [ ] | Screenshot / PowerShell output |
| **TC-02: Initial Telemetry** | Inspect Dashboard `/computers` page | All 40 PCs appear with status `Online`, reporting CPU, RAM, Disk, and IP | [ ] | Dashboard screenshot |
| **TC-03: Software & Process Ingest** | View Software Inventory tab for 5 random PCs | Complete list of installed apps (64 & 32-bit) matching local registry | [ ] | Exported inventory CSV |
| **TC-04: Session 0 Boot Test** | Reboot all 40 PCs via Windows reboot. Do **NOT** log in as student. | Agents start automatically in Session 0; all 40 PCs report `Online` within 90s | [ ] | Server access logs |
| **TC-05: Power Storm (Simultaneous Startup)** | Shut down all 40 PCs. Power on all 40 simultaneously via smart PDU / master switch. | Server handles simultaneous enrollment/auth spikes without HTTP 500 or SQLite locking | [ ] | Server error logs |
| **TC-06: WebSocket Heartbeat** | Keep dashboard open for 15 minutes | Ping/pong heartbeat active every 30s. No false "Offline" flips | [ ] | ConnectionManager logs |
| **TC-07: Network Disconnect / Outbox Test** | Disconnect Ethernet cable on PC-01 through PC-05 for 5 minutes. | Agent detects drop, queues metrics in SQLite outbox (`slms_outbox.db`). No telemetry lost | [ ] | Client outbox DB query |
| **TC-08: Network Reconnection** | Reconnect Ethernet cables on PC-01 through PC-05. | Outbox worker drains all queued items within 30s. Zero duplicate rows | [ ] | Server timestamped metrics |
| **TC-09: Server Restart Recovery** | Restart backend server service during active lab session. | All 40 clients enter exponential backoff with jitter and reconnect cleanly within 60s | [ ] | Reconnection timeline graph |
| **TC-10: Remote Command Dispatch** | Send "Message" broadcast command to all 40 PCs: "Lab closes in 10 minutes". | Notice appears or logs cleanly on all 40 PCs within 3 seconds | [ ] | Command execution audit |
| **TC-11: Remote Workstation Lock** | Send "Lock" command to PC-20. | PC-20 workstation locks immediately. Status reports `executed` in dashboard | [ ] | Workstation screen lock |
| **TC-12: Privacy & Log Hygiene** | Audit `%PROGRAMDATA%\SLMS\logs\agent.log` across 5 sample PCs. | No passwords, secrets, JWT tokens, student filenames, or PII present | [ ] | Log inspection grep |
| **TC-13: Log Rotation** | Inspect total size of log directory on long-running test PC. | Log files rotate at 10 MB, max 5 backup files (never exceeds 50 MB total) | [ ] | Directory listing size |

---

## 6. Acceptance Criteria

For official Phase 10 lab sign-off, the following criteria must be met:
1. **Enrollment Rate:** 100% (40/40 workstations enrolled and authenticated).
2. **Availability:** >= 99.5% uptime during an 8-hour continuous test window.
3. **Data Loss:** 0 dropped telemetry records during 5-minute simulated network outages (verified by durable outbox drain).
4. **Command Latency:** 95th percentile command delivery and execution latency < 3.0 seconds.
5. **Zero SQLite Lock Contention:** No `database is locked` or unhandled concurrency errors on backend.
6. **Security Compliance:** All client credentials stored exclusively in DPAPI machine vault; no plain secrets on disk or in logs.

---

## 7. Post-Test Teardown & Reset

1. If decommissioning test deployment:
   ```powershell
   python.exe service\service.py stop
   python.exe service\service.py uninstall
   Remove-Item -Recurse -Force "C:\ProgramData\SLMS"
   ```
2. Archive test logs, server performance graphs, and Wireshark captures to `artifacts/phase10_lab_results/`.
3. Sign and date official validation sheet.
