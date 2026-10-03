# Smart Lab Management System (SLMS)

A robust, enterprise-grade laboratory workstation management and monitoring system. SLMS combines a high-performance Python Windows Client Agent running as a background Windows Service, a FastAPI backend with real-time WebSocket telemetry and command orchestration, a React administration dashboard, and an Inno Setup automated installer.

---

## Table of Contents
1. [Project Overview](#project-overview)
2. [Repository Structure](#repository-structure)
3. [Prerequisites](#prerequisites)
4. [Backend Setup & Execution](#backend-setup--execution)
5. [Frontend Setup & Execution](#frontend-setup--execution)
6. [Client Agent Setup & CLI Reference](#client-agent-setup--cli-reference)
7. [Workstation Enrollment](#workstation-enrollment)
8. [Transport Security & Development Modes](#transport-security--development-modes)
9. [Windows Service Architecture](#windows-service-architecture)
10. [Installer Build & Packaging](#installer-build--packaging)
11. [Installation & Lifecycle Flow](#installation--lifecycle-flow)
12. [Telemetry & Outbox Architecture](#telemetry--outbox-architecture)
13. [Testing Strategy](#testing-strategy)
14. [Troubleshooting & Diagnostics](#troubleshooting--diagnostics)
15. [Security Invariants](#security-invariants)

---

## 1. Project Overview

SLMS provides centralized oversight, real-time telemetry, and remote management for computer lab environments:

- **Client Agent (`client_agent/`)**: A native Windows service running in Session 0 (`NT SERVICE\SLMSService`). Non-blockingly gathers CPU, RAM, disk, network, process lists, installed software inventories, and application usage sessions. Features a crash-resilient local SQLite outbox for offline buffering, automatic token renewal, and duplex WebSocket command dispatch.
- **Backend API (`backend/`)**: FastAPI application powered by SQLAlchemy and Alembic. Manages computer registration, enrollment token issuance, historical telemetry persistence, real-time WebSocket connections, and remote command queuing.
- **Frontend Dashboard (`frontend/`)**: Modern React + Vite application providing live computer monitoring, dynamic charts, software inventories, issue triage, and administrative command controls.
- **Windows Installer (`installer/`)**: Standalone Inno Setup 6 x64 installer that compiles a unified PyInstaller executable, executes headless enrollment, establishes DPAPI machine-scope credentials, registers the Windows Service, and configures secure NTFS ACLs.

---

## 2. Repository Structure

```
Smart_lab_management_system/
├── backend/                             # FastAPI Backend Service
│   ├── alembic/                         # Database migrations
│   ├── app/
│   │   ├── auth/                        # JWT authentication & password hashing
│   │   ├── models/                      # SQLAlchemy database models
│   │   ├── routes/                      # REST & WebSocket API endpoints
│   │   ├── schemas/                     # Pydantic request/response schemas
│   │   ├── services/                    # Business logic & database operations
│   │   ├── websocket/                   # WebSocket connection & timeout managers
│   │   └── main.py                      # FastAPI application entry point
│   ├── tests/                           # Backend pytest test suite
│   └── pyproject.toml                   # Backend Python dependencies
│
├── client_agent/                        # Windows Client Agent & Service
│   ├── core/
│   │   ├── credentials.py               # DPAPI machine-scope & Keyring credential stores
│   │   ├── collector.py                 # Telemetry collection coordinator & caches
│   │   ├── logger.py                    # Structured logging with secret masking
│   │   ├── managers.py                  # Runtime managers (Token, Outbox, WS, Collector)
│   │   ├── outbox/                      # Durable SQLite outbox & delivery worker
│   │   ├── runtime.py                   # Modular AgentRuntime lifecycle coordinator
│   │   ├── scheduler.py                 # Drift-free recurring task scheduler
│   │   ├── security.py                  # TLS verification, URL validation & security policies
│   │   └── single_instance.py           # Global mutex preventing duplicate instances
│   ├── modules/                         # System collectors (hardware, software, processes, usage)
│   ├── server/                          # REST sender, auth, enrollment & WebSocket client
│   ├── service/
│   │   ├── lifecycle.py                 # Windows Service state machine
│   │   └── service.py                   # Win32 ServiceControlManager implementation & CLI
│   ├── tests/                           # Client Agent pytest test suite
│   ├── main.py                          # Client Agent CLI entry point
│   ├── config.py                        # Agent configuration & polling intervals
│   ├── paths.py                         # System path resolution (%PROGRAMDATA%\SLMS)
│   ├── SLMS_Client_Agent.spec           # Canonical PyInstaller build specification
│   └── pyproject.toml                   # Client Agent Python dependencies
│
├── frontend/                            # React + Vite Dashboard
│   ├── src/                             # React components, pages, hooks, and services
│   └── package.json                     # Frontend dependencies
│
├── installer/                           # Windows Installer Packaging
│   ├── SLMS_Client_Agent_Setup.iss      # Inno Setup 6 compiler script
│   └── output/                          # Output directory for compiled Setup.exe
│
├── docs/                                # Architecture & Phase Documentation
│   └── phases/                          # Implementation specifications and validation reports
├── testing_scripts/                     # Load testing and client simulation scripts
├── pytest.ini                           # Root pytest configuration
└── README.md                            # Comprehensive system documentation
```

---

## 3. Prerequisites

### Windows Development Machine
- **Operating System**: Windows 10 or Windows 11 (64-bit).
- **Python**: Python 3.13+ (64-bit).
- **Package Manager**: [uv](https://github.com/astral-sh/uv) (v0.5+ recommended).
- **Node.js**: Node.js 18+ and npm (for frontend development).
- **Build Tools**:
  - [Inno Setup 6](https://jrsoftware.org/isdl.php) (ISCC.exe) for compiling the installer.
  - Windows SDK / Visual C++ runtime (standard for pywin32).

---

## 4. Backend Setup & Execution

### 1. Synchronize Dependencies
```powershell
cd backend
uv sync
```

### 2. Configure Database & Migrations
The backend defaults to SQLite (`sqlite:///./slms.db`) for local development or PostgreSQL when configured via environment variables.

Run database migrations to prepare all tables and constraints:
```powershell
uv run alembic upgrade head
```

### 3. Start Backend API Server
Launch FastAPI via Uvicorn:
```powershell
uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```
The interactive Swagger API documentation will be available at `http://localhost:8000/docs`.

---

## 5. Frontend Setup & Execution

```powershell
cd frontend
npm install
npm run dev
```
The administration dashboard will launch at `http://localhost:5173`.

---

## 6. Client Agent Setup & CLI Reference

### 1. Synchronize Dependencies
```powershell
cd client_agent
uv sync
```

### 2. CLI Command Reference
The client agent entry point (`main.py` or compiled `SLMS_Client_Agent.exe`) supports administrative commands:

```powershell
# Display help and available commands
uv run python main.py --help

# Run interactively in console mode (foreground)
uv run python main.py

# Headless / Automated Workstation Enrollment
uv run python main.py enroll --url "https://slms.lab.edu:8000" --key "ENROLL_KEY_HERE"

# Install Windows Service under NT SERVICE\SLMSService (Administrator required)
uv run python main.py install

# Configure mandatory NTFS permissions for service account
uv run python main.py configure-acl

# Verify credential decryption and service account access
uv run python main.py verify-credentials

# Start, query, and stop Windows Service
uv run python main.py start
uv run python main.py status
uv run python main.py stop

# Interactive Service Debugger (simulates Session 0 in console)
uv run python main.py debug

# Uninstall Windows Service
uv run python main.py uninstall
```

---

## 7. Workstation Enrollment

Workstation enrollment binds a computer to the SLMS backend and establishes cryptographic identity.

### Headless Enrollment Methods
The `enroll` command securely accepts enrollment keys without command-line parameter leakage:

1. **Direct Parameter**:
   ```powershell
   SLMS_Client_Agent.exe enroll --url "https://slms.lab.edu:8000" --key "KEY"
   ```
2. **Standard Input (Masked / Pipe-safe)**:
   ```powershell
   "KEY" | SLMS_Client_Agent.exe enroll --url "https://slms.lab.edu:8000" --stdin-key
   ```
3. **Protected Key File**:
   ```powershell
   SLMS_Client_Agent.exe enroll --url "https://slms.lab.edu:8000" --key-file "C:\Temp\enroll.key"
   ```
4. **Force Re-enrollment**:
   Add `--force` to overwrite existing enrolled credentials.

### Credential Persistence
Credentials (`agent_id`, `client_secret`, `computer_id`) and `server_url` are encrypted via Windows DPAPI Machine Scope (`CRYPTPROTECT_LOCAL_MACHINE`) with custom entropy and saved to:
- `C:\ProgramData\SLMS\config\service_credentials.enc`
- `C:\ProgramData\SLMS\config\server_config.json`

---

## 8. Transport Security & Development Modes

### Production Mode (Default)
- **Strict HTTPS/WSS**: Plaintext HTTP and WS URLs are rejected with `InsecureHttpProhibitedError`.
- **Strict TLS Verification**: All HTTP requests and WebSocket connections verify certificates against the Windows System Trust Store or enterprise CA bundle (`SLMS_CA_BUNDLE`). `verify=False` is prohibited.
- **Enrolled URL Authority**: The enrolled server URL stored in credentials cannot be overridden by ambient environment variables.

### Local Development & Lab Testing
To permit plaintext HTTP communication for local development:
```powershell
# Set environment variables for interactive testing
$env:SLMS_DEV_MODE="1"
$env:SLMS_ALLOW_INSECURE_HTTP="1"
```
*Note: For the Windows Service running in Session 0, the installer automatically configures machine-level environment variables when an HTTP URL is supplied during setup.*

---

## 9. Windows Service Architecture

The SLMS Client Agent runs as a native Windows service named **`SLMSService`** under the dedicated virtual service account **`NT SERVICE\SLMSService`**.

### Service Management Commands
```powershell
# Check Service State
sc.exe query SLMSService
Get-Service SLMSService

# Start / Stop / Restart Service
sc.exe start SLMSService
sc.exe stop SLMSService
Restart-Service SLMSService
```

### Crash Recovery Policy
Configured automatically via `sc.exe failure`:
- **Reset Period**: 86400 seconds (24 hours).
- **1st Failure**: Restart after 5,000 ms (5s).
- **2nd Failure**: Restart after 10,000 ms (10s).
- **Subsequent Failures**: Restart after 60,000 ms (60s).

---

## 10. Installer Build & Packaging

### 1. Build PyInstaller Executable
```powershell
cd client_agent
uv run pyinstaller --clean --noconfirm SLMS_Client_Agent.spec
```
Artifact generated: `client_agent/dist/SLMS_Client_Agent.exe`.

### 2. Compile Inno Setup Installer
Compile using the Inno Setup 6 compiler (`ISCC.exe`):
```powershell
& "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" installer\SLMS_Client_Agent_Setup.iss
```
Artifact generated: `installer/output/SLMS_Client_Agent_Setup.exe`.

---

## 11. Installation & Lifecycle Flow

```
User specifies Server URL & Key
               │
               ▼
   Validate Server URL (HTTPS/HTTP)
               │
               ▼
   Configure Environment Variables
               │
               ▼
   Copy Executable to Program Files
               │
               ▼
   Execute Headless Enrollment (--key-file)
               │
               ▼
   Persist DPAPI Encrypted Credentials
               │
               ▼
   Create Windows Service (SLMSService)
               │
               ▼
   Apply Mandatory NTFS ACLs to ProgramData
               │
               ▼
   Pre-Flight Verify Credential Decryption
               │
               ▼
   Start Service & Poll RUNNING State
```

### Supported Lifecycle Modes
- **Fresh Installation**: Prompts for Server URL and Enrollment Key, completes registration, configures ACLs, and starts `SLMSService`.
- **Upgrade**: Preserves `service_credentials.enc`, outbox records, and configuration in `%PROGRAMDATA%\SLMS`. Updates binary and restarts service.
- **Repair**: Re-registers service with SCM, verifies credential readability, reapplies ACLs, and restarts service.
- **Rollback**: On any setup failure, stops service, restores backup executable or cleans up partial state, and displays failure diagnosis.
- **Uninstall**: Stops and removes `SLMSService`, cleans binary directory, and removes installer-owned configuration.

---

## 12. Telemetry & Outbox Architecture

```
┌────────────────────────────────────────────────────────────┐
│                    SLMSService (Session 0)                 │
│                                                            │
│  ┌──────────────────────────────────────────────────────┐  │
│  │                    AgentRuntime                      │  │
│  │                                                      │  │
│  │  ┌───────────────┐        ┌───────────────────────┐  │  │
│  │  │   Scheduler   │───────▶│   CollectorManager    │  │  │
│  │  │ (20s/120s/15m)│        │(Hardware/Process/SW)  │  │  │
│  │  └───────────────┘        └───────────┬───────────┘  │  │
│  │                                       │              │  │
│  │                                       ▼              │  │
│  │                           ┌───────────────────────┐  │  │
│  │                           │     UploadManager     │  │  │
│  │                           │   (Payload & Keys)    │  │  │
│  │                           └───────────┬───────────┘  │  │
│  │                                       │              │  │
│  │                                       ▼              │  │
│  │                           ┌───────────────────────┐  │  │
│  │                           │     DurableOutbox     │  │  │
│  │                           │  (SQLite: outbox.db)  │  │  │
│  │                           └───────────┬───────────┘  │  │
│  │                                       │              │  │
│  │                                       ▼              │  │
│  │                           ┌───────────────────────┐  │  │
│  │                           │ OutboxDeliveryWorker  │  │  │
│  │                           └───────────┬───────────┘  │  │
│  │                                       │ (Bearer JWT) │  │
│  └───────────────────────────────────────┼──────────────┘  │
└──────────────────────────────────────────┼─────────────────┘
                                           │
                        HTTPS POST / WSS   ▼
               ┌───────────────────────────────────────┐
               │             SLMS Backend              │
               │  - /api/metrics                       │
               │  - /api/processes                     │
               │  - /api/software                      │
               │  - /api/usage                         │
               │  - /api/issues/agent                  │
               │  - /ws/client/{computer_id}           │
               └───────────────────────────────────────┘
```

### Telemetry Cadence
- **System Metrics (Fast Telemetry)**: Every 20 seconds (`cpu_usage`, `ram_usage`, `disk_usage`, network byte counters).
- **Process Inventory**: Every 120 seconds (bounded list of active processes).
- **Software Inventory**: Every 15 minutes (differential fingerprint scan).
- **JWT Token Refresh**: Every 12 minutes (preemptive renewal before 15-minute expiration).

---

## 13. Testing Strategy

The repository includes a comprehensive test suite across unit, integration, platform, and load dimensions.

### Run All Tests
```powershell
# Client Agent Test Suite (400+ tests)
cd client_agent
uv run pytest -q

# Backend Test Suite (135+ tests)
cd ../backend
uv run pytest -q
```

### Git Diff & Integrity Check
```powershell
git diff --check
```

---

## 14. Troubleshooting & Diagnostics

### 1. Service Fails to Reach `RUNNING`
Check Windows Service Control Manager status:
```powershell
sc.exe query SLMSService
```
Inspect service agent logs:
```powershell
Get-Content C:\ProgramData\SLMS\logs\agent.log -Tail 50
```

### 2. Verify Credential File Accessibility
Run the diagnostic credential verifier:
```powershell
cd "C:\Program Files\SLMS"
.\SLMS_Client_Agent.exe verify-credentials
```

### 3. Repair Data Folder ACLs
If permissions are corrupted, reapply the mandatory security ACLs:
```powershell
.\SLMS_Client_Agent.exe configure-acl
```

### 4. Inspect SQLite Outbox Status
Examine pending or dead-letter outbox records:
```powershell
sqlite3 C:\ProgramData\SLMS\cache\outbox.db "SELECT id, event_type, status, attempt_count FROM outbox_records;"
```

---

## 15. Security Invariants

1. **No Plaintext Secrets**: Enrollment keys and client secrets are never logged or stored unencrypted.
2. **Machine-Scope DPAPI**: All service credentials use `CRYPTPROTECT_LOCAL_MACHINE` with dedicated application entropy.
3. **Restricted NTFS ACLs**: `C:\ProgramData\SLMS\config` is restricted exclusively to `Builtin\Administrators`, `NT AUTHORITY\SYSTEM`, and `NT SERVICE\SLMSService`.
4. **Strict Transport Security**: Production traffic enforces HTTPS/WSS with strict TLS validation and prohibits token parameters in WebSocket query strings.
5. **Single Instance Guarantee**: Windows named mutex prevents concurrent agent execution on the same workstation.
