# Smart Lab Management System (SLMS)

[![Python Version](https://img.shields.io/badge/python-3.13+-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688.svg)](https://fastapi.tiangolo.com/)
[![Tauri](https://img.shields.io/badge/Tauri-v2-FFC131.svg)](https://tauri.app/)
[![React](https://img.shields.io/badge/React-19-61DAFB.svg)](https://react.dev/)
[![Platform](https://img.shields.io/badge/platform-Windows%2010%20%7C%2011%20(x64)-blue.svg)](https://www.microsoft.com/windows)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

A robust, enterprise-grade laboratory orchestration, hardware monitoring, and remote workstation administration platform designed specifically for institutional and academic computer labs. 

SLMS combines a high-performance **Python Windows Service** running in Session 0, an ultra-lightweight **Tauri v2 Native Desktop Dashboard** with Windows System Tray integration and Action Center Toast notifications, and an automated **Inno Setup** deployment pipeline.

---

## 📚 Documentation Index
- 🏗️ **[System Architecture Guide](docs/SYSTEM_ARCHITECTURE.md)**: Deep technical dive into Session 0 vs Session 1, SQLite WAL concurrency, DPAPI machine cryptography, and Tauri vs Electron trade-offs.
- 🚀 **[Administrator & Deployment Guide](docs/ADMIN_DEPLOYMENT_GUIDE.md)**: Step-by-step manual for lab technicians: host installation, silent unattended deployment across 50+ PCs, firewall rules, and alert management.

---

## Key Highlights

- **Dedicated Port `18080`**: The host backend binds strictly to port `18080` (with firewall rules preconfigured). It will never conflict with student coding projects (such as FastAPI, Django, or Node.js running on port `8000`, `3000`, or `5000`).
- **Zero-Friction Client Enrollment**: Client installers and CLI automatically default to port `18080` (e.g. typing `192.168.1.100` seamlessly connects to `http://192.168.1.100:18080`).
- **Tauri v2 Desktop Shell (~20–40 MB RAM)**: Unlike Electron apps which consume 200–350 MB of memory, SLMS uses the OS-native Microsoft Edge WebView2 control and native Rust engine.
- **Close-to-Tray & System Tray Controls**: Closing the dashboard window (`X`) minimizes it directly to the Windows System Tray near the clock.
- **Native Windows Toast Notifications**: Real-time alerts (RAM > 90%, CPU spikes, sudden disconnections) trigger standard Windows Action Center toast banners with sound, even when the dashboard is minimized.
- **Durable Offline Telemetry Outbox**: Client workstations buffer telemetry in a local crash-resilient SQLite outbox during network disconnects and auto-flush chronologically upon reconnect.
- **Cryptographic DPAPI Credentials**: Machine-scoped Windows DPAPI (`CRYPTPROTECT_LOCAL_MACHINE`) locks workstation tokens to local hardware security descriptors.

---

## System Overview & Architecture

```
+========================================================================================+
|                        SLMS HOST COMPUTER (Teacher / Admin PC)                         |
+========================================================================================+
|  [Session 1 (Interactive Desktop)]                                                     |
|    SLMS Host Dashboard (Tauri v2 Native Desktop App - ~25 MB RAM)                      |
|    - System Tray Integration (Close-to-Tray)                                           |
|    - Windows Action Center Toast Notification Provider                                 |
|    - Real-time React 19 + Vite Live Laboratory Matrix Grid                             |
|          | Localhost WebSocket (ws://127.0.0.1:18080/ws/dashboard)                     |
|  [Session 0 (Background Service - LocalSystem)]                                        |
|    SLMS Host Service (FastAPI + Uvicorn + SQLite WAL - Dedicated Port 18080)           |
|    - High-Speed Metric Ingestion & Alert Threshold Evaluator                           |
|    - Automatic SCM Recovery (Restarts within 5s on failure)                             |
+===========================================▲============================================+
                                            |
                                            | Local Network (Port 18080 - HTTP / WSS)
                                            |
+===========================================▼============================================+
|                       STUDENT WORKSTATIONS (1 to 100+ Lab PCs)                         |
+========================================================================================+
|  [Session 1+ (Student Desktop)]                                                        |
|    SLMS Notifier (SLMS_Notifier.exe) - Displays announcements & exam timers            |
|  [Session 0 (Windows Service - NT SERVICE\SLMSService)]                                |
|    SLMS Client Agent (SLMS_Client_Agent.exe)                                           |
|    - Non-blocking CPU, RAM, Disk, Process, and Software Inventory Probing              |
|    - Durable SQLite Outbox (Zero data loss during network interruptions)               |
|    - DPAPI Local Machine Encrypted Credential Vault (%ProgramData%\SLMS\config)        |
+========================================================================================+
```

---

## Repository Structure

```
Smart_lab_management_system/
├── backend/                             # FastAPI Backend Service (Port 18080)
│   ├── app/                             # REST routes, SQLAlchemy models, alert engine
│   ├── service_runner.py                # Windows Service Control Manager wrapper
│   └── pyproject.toml                   # Python dependencies managed via uv
│
├── client_agent/                        # Windows Client Agent & Service
│   ├── core/                            # DPAPI credentials, SQLite outbox, security policies
│   ├── modules/                         # Hardware, process, software collectors
│   ├── notifier/                        # Session 1 desktop companion (SLMS_Notifier)
│   ├── SLMS_Client_Agent.spec           # PyInstaller build specification
│   └── pyproject.toml                   # Client Python dependencies
│
├── frontend/                            # Administration Dashboard
│   ├── src/                             # React 19 components, hooks, and pages
│   ├── src-tauri/                       # Tauri v2 native shell, system tray, notifications
│   └── package.json                     # Frontend dependencies
│
├── installer/                           # Windows Inno Setup Deployment Packaging
│   ├── SLMS_Host_Setup.iss              # Host Service + Dashboard Installer Script
│   ├── SLMS_Client_Agent_Setup.iss      # Client Agent + Notifier Installer Script
│   └── output/                          # Compiled setup executables
│
├── docs/                                # Architecture & Technical Documentation
│   ├── SYSTEM_ARCHITECTURE.md           # Deep dive technical architecture
│   └── ADMIN_DEPLOYMENT_GUIDE.md        # Lab technician deployment manual
└── README.md                            # Main project overview
```

---

## Quickstart & Development Setup

### Prerequisites
- **Operating System**: Windows 10 or Windows 11 (64-bit).
- **Python**: Python 3.13+ (64-bit).
- **Package Manager**: [uv](https://github.com/astral-sh/uv) (v0.5+ recommended).
- **Node.js**: Node.js 18+ and npm.
- **Rust**: Rust toolchain (for Tauri desktop app compilation).
- **Inno Setup 6**: For compiling `.exe` installers.

---

### 1. Backend Setup & Local Run
```powershell
cd backend
uv sync

# Run database migrations
uv run alembic upgrade head

# Start FastAPI server on dedicated port 18080
uv run uvicorn app.main:app --host 0.0.0.0 --port 18080 --reload
```
Interactive Swagger API documentation: `http://localhost:18080/docs`

---

### 2. Frontend & Tauri Desktop Setup
```powershell
cd frontend
npm install

# Run web preview in browser (Vite dev server)
npm run dev

# Run native desktop shell with System Tray & Notifications (Tauri)
npx tauri dev
```

---

### 3. Client Agent Setup & CLI Commands
```powershell
cd client_agent
uv sync

# Run interactively in console mode
uv run python main.py

# Headless enrollment (auto-resolves to port 18080)
uv run python main.py enroll --url "192.168.1.100" --key "YOUR_ENROLLMENT_KEY"

# Service installation & management (Elevated Administrator)
uv run python main.py install
uv run python main.py start
uv run python main.py status
uv run python main.py stop
```

---

## Installer Packaging

SLMS produces two standalone, production-ready Windows installers:

### 1. Host Installer (`SLMS_Host_Setup.exe`)
Packages:
- Python Windows Service compiled distribution.
- Tauri native desktop dashboard (`SLMS_Host_Dashboard.exe`).
- Windows Firewall rule (Inbound TCP `18080`).
- Master Administrator account initial configuration.
- SCM Automatic Recovery configuration.

To compile:
```powershell
& "C:\Users\<user>\AppData\Local\Programs\Inno Setup 6\ISCC.exe" installer\SLMS_Host_Setup.iss
```

### 2. Client Agent Installer (`SLMS_Client_Agent_Setup.exe`)
Packages:
- Unified `SLMS_Client_Agent.exe` binary.
- Interactive Session 1 Companion `SLMS_Notifier.exe`.
- Auto-port defaulting to `:18080`.
- Headless DPAPI machine-scoped credential provisioning.

To compile:
```powershell
& "C:\Users\<user>\AppData\Local\Programs\Inno Setup 6\ISCC.exe" installer\SLMS_Client_Agent_Setup.iss
```

---

## Testing Strategy

All subcomponents include comprehensive automated test suites:

```powershell
# 1. Run Client Agent Test Suite (22 security + outbox + service tests)
uv run --directory client_agent pytest

# 2. Run Backend Test Suite
uv run --directory backend pytest

# 3. Run Frontend Vitest Suite (271 tests across 22 test suites)
cd frontend
npm test
```

---

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE) for details.
