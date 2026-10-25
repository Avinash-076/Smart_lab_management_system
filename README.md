# Smart Lab Management System (SLMS)

[![Python Version](https://img.shields.io/badge/python-3.13+-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688.svg)](https://fastapi.tiangolo.com/)
[![Tauri](https://img.shields.io/badge/Tauri-v2-FFC131.svg)](https://tauri.app/)
[![React](https://img.shields.io/badge/React-19-61DAFB.svg)](https://react.dev/)
[![Platform](https://img.shields.io/badge/platform-Windows%2010%20%7C%2011%20(x64)-blue.svg)](https://www.microsoft.com/windows)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

An enterprise-grade laboratory orchestration, real-time hardware telemetry monitoring, remote administration, and notification platform engineered for academic and institutional computer labs.

SLMS combines a high-speed **FastAPI Windows Service** running on dedicated port `18080`, an ultra-lightweight **Tauri v2 Native Desktop Dashboard** (~25–40 MB RAM) with System Tray minimization and Windows Action Center toast notifications, and a low-overhead **Python Client Agent** with DPAPI machine cryptography and crash-resilient SQLite telemetry buffering.

---

## 📚 Documentation Index
- 🏗️ **[System Architecture Guide](docs/SYSTEM_ARCHITECTURE.md)**: Deep technical dive into Session 0 vs Session 1, SQLite WAL concurrency, DPAPI machine cryptography, and Tauri vs Electron trade-offs.
- 🚀 **[Administrator & Deployment Guide](docs/ADMIN_DEPLOYMENT_GUIDE.md)**: Manual for lab technicians: host installation, unattended deployment across 50+ PCs, firewall rules, and alert management.

---

## ⚙️ System Architecture

```
+========================================================================================+
|                        SLMS HOST COMPUTER (Teacher / Admin PC)                         |
+========================================================================================+
|  [Session 1 (Interactive Desktop)]                                                     |
|    SLMS Host Dashboard (Tauri v2 Native Desktop App - ~25 MB RAM)                      |
|    - System Tray Integration (Close-to-Tray near clock)                                |
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

## 📋 Prerequisites

Before running the project, ensure you have the following installed on your system:

| Tool | Version | Purpose | Installation / Link |
| :--- | :--- | :--- | :--- |
| **Python** | 3.13+ (64-bit) | Host backend service & client agent | [python.org](https://www.python.org/downloads/) |
| **uv** *(Recommended)* | Latest | Fast Python package manager | Run `powershell -c "irm https://astral.sh/uv/install.ps1 \| iex"` |
| **Node.js** | 18+ LTS | Frontend React development | [nodejs.org](https://nodejs.org/) |
| **Rust Toolchain** *(Optional)* | 1.77+ | For running the Tauri desktop app | [rustup.rs](https://rustup.rs/) |
| **C++ Build Tools** | VS 2022 Build Tools | For native C extensions & Rust compilation | [visualstudio.microsoft.com](https://visualstudio.microsoft.com/visual-cpp-build-tools/) |

> **Note**: While the client agent service and Tauri toast integrations are designed for Windows 10/11 (x64), the **backend** and **frontend (web mode)** can be run on macOS or Linux for development and testing.

---

## 🚀 Quickstart: Running the Project Locally

Follow these steps to run the complete system locally for development or demonstration:

### Step 1: Start the Backend Service

1. **Open a terminal** and navigate to the backend directory:
   ```powershell
   cd backend
   ```

2. **Install dependencies**:
   ```powershell
   uv sync
   ```
   *(Or using standard pip: `python -m venv .venv; .venv\Scripts\activate; pip install -e .`)*

3. **Run database migrations**:
   ```powershell
   uv run alembic upgrade head
   ```

4. **Initialize the Master Administrator account**:
   ```powershell
   uv run python service_runner.py init-admin admin Admin@123
   ```
   *Creates the primary administrator account (`username: admin`, `password: Admin@123`) and seeds default system roles and settings.*

5. **Start the FastAPI backend server**:
   ```powershell
   uv run uvicorn app.main:app --host 0.0.0.0 --port 18080 --reload
   ```

6. **Verify Backend Status**:
   - Backend API: `http://localhost:18080/api`
   - Interactive Swagger API Docs: `http://localhost:18080/docs`

---

### Step 2: Start the Frontend Dashboard

Open a **second terminal** and navigate to the frontend directory:

```powershell
cd frontend
npm install
```

You can run the dashboard in **either of two modes**:

#### Mode A: Web Browser Mode (Fast UI Development)
Runs the React 19 app inside your web browser via Vite:
```powershell
npm run dev
```
- Open `http://localhost:5173` in your browser.
- Log in with the administrator credentials:
  - **Username**: `admin`
  - **Password**: `Admin@123`

#### Mode B: Tauri v2 Native Desktop Shell (Production Experience)
Runs the native Windows desktop app with close-to-tray system tray controls and Windows Action Center native toast notifications:
```powershell
npx tauri dev
```
*(Requires the Rust toolchain installed).*

---

### Step 3: Run the Client Agent (Workstation Telemetry)

To simulate or connect a student workstation to the dashboard:

1. **Open a third terminal** and navigate to the `client_agent` directory:
   ```powershell
   cd client_agent
   uv sync
   ```

2. **Generate an Enrollment Key**:
   - In your browser/Tauri dashboard, go to **Settings** → **Enrollment Keys**.
   - Click **Generate Key** and copy the generated token (e.g. `ENROLL-XXXXXX`).

3. **Enroll the Agent**:
   ```powershell
   uv run python main.py enroll --url "127.0.0.1" --key "YOUR_ENROLLMENT_KEY"
   ```
   *Note: Port `18080` is automatically appended by default, so providing `127.0.0.1` or LAN IP `192.168.1.X` connects directly.*

4. **Run the Client Agent in Console Mode**:
   ```powershell
   uv run python main.py
   ```
   The client agent will immediately register hardware specifications (CPU, RAM, Disks, GPU, Active Processes) and begin streaming real-time telemetry every 5 seconds to the Host Dashboard.

5. **(Optional) Run the Student Desktop Notifier**:
   In another window, start the companion GUI that displays administrative broadcasts and exam timers on the desktop:
   ```powershell
   uv run python notifier_main.py
   ```

---

## 🛠️ Windows Service Deployment (Production)

In institutional computer laboratories, the backend and client agent are deployed as unattended Windows Services running under `LocalSystem` / `Session 0`:

### Host Windows Service
Run from an elevated (Administrator) command prompt:
```powershell
cd backend

# Install the Windows Service
uv run python service_runner.py install

# Start the Windows Service
uv run python service_runner.py start

# Stop or remove service
uv run python service_runner.py stop
uv run python service_runner.py remove
```

### Client Agent Windows Service
Run from an elevated (Administrator) command prompt on student machines:
```powershell
cd client_agent

# Install and start background monitoring service
uv run python main.py install
uv run python main.py start

# Check service status
uv run python main.py status

# Stop and uninstall service
uv run python main.py stop
uv run python main.py uninstall
```

---

## 🧪 Running Automated Tests

All system modules include unit and integration test suites:

```powershell
# 1. Run Backend API & Database Tests (FastAPI + SQLAlchemy)
uv run --directory backend pytest

# 2. Run Client Agent Tests (DPAPI, Outbox buffer, Collectors)
uv run --directory client_agent pytest

# 3. Run Frontend Vitest Suite (React 19 Components & Services)
cd frontend
npm test
```

---

## 📦 Building Standalone Installers

SLMS compiles into two production Inno Setup Windows installers located in `installer/`:

### 1. Host Installer (`SLMS_Host_Setup.exe`)
Builds the complete host package:
- Compiles `service_runner.py` into a standalone service binary via PyInstaller.
- Compiles the Tauri v2 desktop application (`SLMS_Host_Dashboard.exe`).
- Automatically configures Windows Firewall rule for inbound TCP `18080`.
- Sets up SCM automatic restart failure recovery.

Compile using Inno Setup 6:
```powershell
& "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" installer\SLMS_Host_Setup.iss
```

### 2. Client Agent Installer (`SLMS_Client_Agent_Setup.exe`)
Builds the silent/GUI student workstation installer:
- Packages `SLMS_Client_Agent.exe` and `SLMS_Notifier.exe`.
- Supports silent command-line deployment across 50+ PCs:
  ```powershell
  SLMS_Client_Agent_Setup.exe /VERYSILENT /SUPPRESSMSGBOXES /NORESTART /HOST_IP="192.168.1.100" /ENROLL_KEY="YOUR_KEY"
  ```

Compile using Inno Setup 6:
```powershell
& "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" installer\SLMS_Client_Agent_Setup.iss
```

---

## 🔧 Environment Configuration Reference

### Backend (`backend/.env`)
| Variable | Default | Description |
| :--- | :--- | :--- |
| `DATABASE_URL` | `sqlite:///slms.db` | SQLite database connection string with WAL mode |
| `JWT_SECRET_KEY` | `slms-secure-lab-secret-key-2026` | Cryptographic secret for signing tokens |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `15` | Admin session access token expiration |
| `REFRESH_TOKEN_EXPIRE_HOURS` | `8` | Refresh token lifetime |
| `AGENT_TOKEN_EXPIRE_MINUTES` | `15` | Client agent authentication token lifetime |

### Frontend (`frontend/.env`)
| Variable | Default | Description |
| :--- | :--- | :--- |
| `VITE_API_BASE_URL` | `http://127.0.0.1:18080/api` | Host REST API base endpoint |
| `VITE_WS_BASE_URL` | `ws://127.0.0.1:18080/ws/dashboard` | Real-time WebSocket event connection |

---

## ❓ Troubleshooting

- **Port 18080 is already in use**:
  Ensure no previous uvicorn or SLMS service is running:
  ```powershell
  netstat -ano | findstr :18080
  Stop-Process -Id <PID> -Force
  ```
- **Login fails with 401 Unauthorized**:
  Ensure you initialized the admin account using:
  ```powershell
  cd backend
  uv run python service_runner.py init-admin admin Admin@123
  ```
- **Tauri build errors regarding WebView2 or Rust**:
  Verify Rust is installed with `rustc --version` and `cargo --version`. Ensure the "Desktop development with C++" workload is installed in Visual Studio Build Tools.
- **Client Agent fails to enroll**:
  Verify the Host Backend is running and reachable on port `18080`:
  ```powershell
  Test-NetConnection -ComputerName 127.0.0.1 -Port 18080
  ```

---

## 📄 License

This project is licensed under the MIT License. See [LICENSE](LICENSE) for details.
