# Smart Lab Management System (SLMS)
## Comprehensive Academic Project Work & Engineering Technical Documentation

> **Project Title**: SMART LAB MANAGEMENT SYSTEM (SLMS)  
> **Domain**: Computer Engineering, Systems Programming & Workstation Orchestration  
> **Academic Year**: 2026–2027  

---

## TABLE OF CONTENTS

1. [EXECUTIVE SUMMARY](#1-executive-summary)
   - 1.1 Abstract
   - 1.2 Project Overview
   - 1.3 Objectives and Scope
2. [SOFTWARE AND HARDWARE REQUIREMENTS](#2-software-and-hardware-requirements)
   - 2.1 Software Requirements
   - 2.2 Hardware Requirements
3. [INTRODUCTION](#3-introduction)
   - 3.1 Background and Motivation
4. [SYSTEM ANALYSIS](#4-system-analysis)
   - 4.1 Problem Definition
   - 4.2 Proposed Solution
   - 4.3 Feasibility Study
   - 4.4 User Roles and Stakeholders
5. [SRS & SYSTEM DESIGN](#5-srs--system-design)
   - 5.1 Functional Requirements
   - 5.2 Non-Functional Requirements
   - 5.3 Architectural & UI/UX Design
6. [SOFTWARE INSTALLATION & PROCEDURE](#6-software-installation--procedure)
   - 6.1 Code Editor Setup & Development Tools
   - 6.2 Backend Installation & Database Setup
   - 6.3 Frontend & Tauri Desktop Setup
   - 6.4 Client Agent Setup & Headless Enrollment
   - 6.5 Inno Setup Packaging
7. [USER INTERFACE GUIDE](#7-user-interface-guide)
   - 7.1 Overview & Dashboard Navigation
   - 7.2 Workstation Monitoring Grid
   - 7.3 System Tray & Windows Action Center Toasts
8. [OPERATION MANUAL](#8-operation-manual)
   - 8.1 Daily Lab Operations
   - 8.2 Managing Alerts & Process Termination
   - 8.3 Troubleshooting Common Scenarios
9. [SYSTEM MODULES](#9-system-modules)
   - 9.1 Authentication & RBAC Module
   - 9.2 Workstation Management & Enrollment Module
   - 9.3 Client Agent Background Service Module
   - 9.4 Telemetry Ingestion & Outbox Module
   - 9.5 Alert & Threshold Evaluation Module
   - 9.6 Remote Command & Control Module
   - 9.7 Desktop Shell & System Tray Module
   - 9.8 Native Windows Toast Notification Module
   - 9.9 Reports & Database Management Module
10. [SOURCE CODE & ARCHITECTURE](#10-source-code--architecture)
   - 10.1 Directory Structure & Organization
   - 10.2 Core Implementation Snippets
   - 10.3 Test Verification Suite
11. [APPLICATIONS](#11-applications)
   - 11.1 Academic Computer Laboratories
   - 11.2 University Campus Networks
   - 11.3 Software Training & Competitive Exam Centers
   - 11.4 IT Asset Management & Security Audits
12. [CONCLUSION AND FUTURE SCOPE](#12-conclusion-and-future-scope)
   - 12.1 Conclusion
   - 12.2 Future Scope
13. [REFERENCES](#13-references)
   - 13.1 Technical References
   - 13.2 Software Tools, Libraries, and Documentation

---

## 1. EXECUTIVE SUMMARY

### 1.1 Abstract

The Smart Lab Management System (SLMS) is an enterprise-grade laboratory orchestration, telemetry monitoring, and workstation management platform designed specifically for academic and institutional computer laboratories. Managing modern multi-user laboratory environments presents unique operational challenges, including unauthorized software execution, unmonitored resource exhaustion (RAM and CPU bottlenecks), network disconnection triage, and tedious manual software audits across dozens of student workstations.

SLMS addresses these challenges by integrating a non-blocking Windows Client Agent running as a background Windows Service, a high-throughput FastAPI backend operating on dedicated port 18080 with Write-Ahead Logged (WAL) SQLite storage, and a modern desktop administration dashboard built using Tauri v2 (Rust and React 19). The system features durable telemetry buffering via a local SQLite outbox, machine-scoped Data Protection API (DPAPI) credential encryption, duplex WebSocket real-time command dispatch, and Windows Action Center native toast notifications integrated with the Windows System Tray.

By replacing resource-heavy monitoring solutions with a lightweight architecture that consumes less than 30 MB of RAM, SLMS ensures that computer lab administration operates quietly in the background without interfering with student development workflows or programming assignments.

### 1.2 Project Overview

In institutional computer laboratories, system administrators and faculty members face difficulties tracking hardware health, application usage, and student workstation status in real time. Often, educators rely on manual visual checks or separate ad-hoc command-line scripts to verify whether workstations are functioning or if specific programming software is installed.

The Smart Lab Management System unifies all facets of lab administration into a cohesive dual-tier architecture:
1. A Host Service and Desktop Dashboard installed on the instructor/lab technician's computer.
2. A lightweight Client Agent installed on student workstations that runs transparently as a background Windows Service.

The Host application collects, aggregates, and visualizes system health metrics, installed software packages, and active processes. It also allows instructors to broadcast messages, lock screens during examinations, and receive instant native Windows notifications when anomalies—such as severe memory leaks or unexpected disconnections—occur. By maintaining strict compliance with Windows Session 0 isolation standards, SLMS achieves uncompromising stability and enterprise security.

### 1.3 Objectives and Scope

Objectives:
1. Dedicated Port Isolation: To operate on dedicated TCP port 18080, completely eliminating port collisions with student projects (such as FastAPI, Django, or React running on default ports 8000, 3000, or 5000).
2. Zero-Friction Workstation Enrollment: To provide automated URL and port defaulting so lab technicians only enter the host IP address without manual port typing.
3. Lightweight Resource Footprint: To utilize Tauri v2 (Edge WebView2 + Rust) to maintain dashboard RAM usage under 35 MB, avoiding the heavy 250+ MB overhead of Electron.
4. Reliable Offline Telemetry: To implement a durable SQLite outbox on student workstations that buffers performance data during network drops and flushes seamlessly upon reconnection.
5. Cryptographic Machine Security: To secure all stored agent credentials using Windows DPAPI Local Machine encryption, preventing secret extraction or credential theft.
6. Persistent Background Monitoring: To integrate Close-to-Tray and native Windows Toast Notifications, ensuring instructors never miss critical alerts even when the dashboard window is closed.
7. Duplex Remote Command Dispatch: To enable near-instantaneous screen locking, process termination, system restart, and broadcast messaging across individual or grouped workstations.

Scope:
The scope of SLMS encompasses computer laboratory environments containing up to 100+ Windows 10/11 64-bit workstations operating over a Local Area Network (LAN). It covers real-time hardware telemetry, software inventory auditing, process management, remote maintenance commands, issue ticketing, and regulatory audit logging. Advanced Wide Area Network (WAN) routing across public unauthenticated proxies is outside the primary design scope.

---

## 2. SOFTWARE AND HARDWARE REQUIREMENTS

### 2.1 Software Requirements

Host Server & Dashboard Requirements:
- Operating System: Windows 10 (64-bit) or Windows 11 (64-bit), Pro or Enterprise edition recommended.
- Python Runtime: Python 3.13+ (64-bit).
- Package & Dependency Manager: Astral uv (v0.5+).
- Backend Framework: FastAPI 0.115+, Uvicorn 0.34+, Pydantic v2.
- Database Engine: SQLite 3.45+ with Write-Ahead Logging (WAL) and SQLAlchemy 2.0+.
- Desktop Shell: Tauri v2 (Rust 1.90+ toolchain, Microsoft Edge WebView2 runtime).
- Frontend UI: React 19, Vite 6+, Lucide-React icons, HTML5, Vanilla CSS Design System.
- Packaging Tool: Inno Setup 6.3+ (ISCC.exe command-line compiler).

Client Workstation Requirements:
- Operating System: Windows 10 or Windows 11 (64-bit).
- Windows Service Runtime: PyWin32 (Win32 Service Control Manager interface).
- System Collectors: psutil, WMI, Windows Registry winreg API, Windows DPAPI (Crypt32).
- Local Outbox: SQLite 3 embedded engine.

### 2.2 Hardware Requirements

Host Computer (Teacher / Lab Administrator PC):
- Processor: Intel Core i3 / AMD Ryzen 3 or higher (Quad-Core 2.4 GHz+).
- RAM: Minimum 4 GB RAM (8 GB recommended for labs with 50+ concurrent workstations).
- Storage: 500 MB free SSD/HDD storage for database logs and telemetry history.
- Network: 100 Mbps / 1 Gbps Ethernet Network Interface Card (NIC) with static LAN IP.

Student Workstations:
- Processor: Dual-Core 1.8 GHz or higher (Intel Celeron, Pentium, Core i3/i5, AMD).
- RAM: Minimum 2 GB RAM (Agent consumes less than 25 MB RAM).
- Storage: 100 MB free disk space for binaries, logs, and durable outbox buffer.
- Network: Wi-Fi or Ethernet connection to the laboratory local subnet.

---

## 3. INTRODUCTION

### 3.1 Background and Motivation

Modern educational institutions and polytechnics invest heavily in computer laboratories to provide students with practical software development, data science, networking, and engineering education. However, operating a laboratory with dozens of student workstations presents significant technical challenges. Students frequently install unverified software, run intensive tasks that exhaust memory, accidentally disconnect network cables, or encounter configuration issues during practical sessions.

Traditional commercial remote management tools (such as TeamViewer or enterprise Active Directory suites) are often prohibitively expensive, overly complex, or require internet connectivity to cloud servers. Furthermore, many student projects (e.g. web development practicals) require running web servers locally. If laboratory monitoring software uses common default ports like 8000, port conflicts frequently disrupt both student assignments and monitoring reliability.

The Smart Lab Management System was conceived to deliver a purpose-built, on-premises, zero-maintenance solution. By utilizing modern engineering standards—such as asynchronous FastAPI backends, dedicated port 18080, Tauri v2 native desktop integration, and DPAPI-secured background services—SLMS provides institutional labs with reliable, enterprise-grade control at zero licensing cost.

---

## 4. SYSTEM ANALYSIS

### 4.1 Problem Definition

In the absence of a centralized lab management solution, educational institutions encounter persistent obstacles:
1. Port Conflicts: Background monitoring tools bound to port 8000 collide with students learning FastAPI, Django, or PHP, resulting in WinError 10013 socket permission errors.
2. Missed Critical Alerts: When instructors close the monitoring window to grade papers, they lose awareness of hardware spikes, memory exhaustion, or offline machines.
3. Network Data Loss: Transient network drops cause telemetry packets to fail, leaving blind spots in lab activity history.
4. Credential Insecurity: Storing server passwords or machine tokens in plaintext configuration files leaves workstations vulnerable to tampering by curious students.
5. Bloated Resource Consumption: Electron-based management software consumes 200–350 MB of RAM per machine, slowing down older laboratory hardware.

### 4.2 Proposed Solution

SLMS addresses each identified problem through rigorous systems design:
1. Port 18080 Migration: The entire host infrastructure binds exclusively to port 18080, completely isolated from developer ports.
2. Close-to-Tray & Action Center Notifications: The desktop app minimizes to the Windows System Tray and sends native OS toast notifications on alerts, ensuring zero missed warnings.
3. Durable SQLite Outbox: Telemetry is saved in a local atomic SQLite database before transmission; unsent metrics buffer safely on disk until connectivity is restored.
4. Machine-Scope DPAPI Encryption: Workstation tokens are locked using Windows DPAPI machine keys, unreadable even if the file is copied to another machine.
5. Tauri v2 Desktop Engine: Consumes only 20–35 MB of RAM by utilizing the built-in Windows Edge WebView2 runtime and a compiled Rust backend.

### 4.3 Feasibility Study

Technical Feasibility: The technologies employed (Python 3.13, FastAPI, SQLAlchemy, Tauri v2, Rust, React 19) are mature, stable, and widely supported on Windows 10/11 x64 platforms.

Economic Feasibility: SLMS is 100% open-source and on-premises. It incurs zero recurring cloud hosting fees, zero per-seat licensing costs, and requires no specialized proprietary hardware.

Operational Feasibility: The single-click Inno Setup installers (`SLMS_Host_Setup.exe` and `SLMS_Client_Agent_Setup.exe`) require minimal technical expertise to deploy. Automatic port defaulting eliminates manual network syntax entry.

### 4.4 User Roles and Stakeholders

1. Master Administrator / Lab In-Charge: Full administrative authority over all workstations, user roles, system thresholds, and policy settings.
2. Faculty / Lab Instructor: Can view real-time workstation status, send broadcast announcements, lock screens during examinations, and triage reported issues.
3. Student / Workstation User: Uses the workstation for lab tasks, receives maintenance notices and broadcast timers, and reports hardware/software issues through the client companion.

---

## 5. SRS & SYSTEM DESIGN

### 5.1 Functional Requirements

FR-01: Dedicated Host Ingestion: The host service must listen on TCP port 18080 and accept telemetry from authenticated workstations.
FR-02: Auto-Port Defaulting: The client agent and installer must automatically resolve server inputs without ports (e.g. 192.168.1.100) to port 18080.
FR-03: Workstation Telemetry Collection: The agent must collect CPU usage, RAM utilization, disk capacity, active processes, and software inventory every 10 seconds.
FR-04: Offline Outbox Buffering: Metrics must buffer in a local SQLite database during network disconnects and transmit chronologically upon reconnection.
FR-05: Real-Time Alert Evaluation: The host must trigger alerts when RAM > 90%, CPU > 95%, or when a workstation fails to report within 30 seconds.
FR-06: Windows System Tray & Toasts: The desktop dashboard must support Close-to-Tray and trigger native Windows Action Center toasts on alerts.
FR-07: Remote Command Execution: Administrators must be able to lock screens, kill processes, and restart workstations remotely via duplex WebSockets.
FR-08: Role-Based Access Control: All administrative API endpoints must enforce JWT token validation and granular role permissions.

### 5.2 Non-Functional Requirements

NFR-01 (Performance): Dashboard rendering must sustain 60 FPS with sub-100ms WebSocket update latency for up to 100 concurrent workstations.
NFR-02 (Memory Efficiency): The client agent must consume less than 25 MB RAM; the desktop dashboard must consume less than 40 MB RAM in system tray mode.
NFR-03 (Reliability): The host service must utilize SQLite WAL mode with 30-second busy timeouts and automatic SCM restart recovery within 5 seconds.
NFR-04 (Security): Credentials must be encrypted via Windows DPAPI Local Machine scope; all passwords must be hashed using bcrypt with salt rounds >= 12.

### 5.3 Architectural & UI/UX Design

The system follows a clean modular separation between Session 0 services and Session 1 desktop interfaces.

Data Flow Architecture:
1. Client Agent Metric Collector -> Local SQLite Outbox.
2. Outbox Delivery Worker -> HTTP POST /api/telemetry (Host Port 18080).
3. Host Telemetry Engine -> SQLAlchemy SQLite WAL DB -> WebSocket Broadcaster.
4. WebSocket Broadcaster -> Tauri Dashboard -> Windows Action Center Toast.

UI/UX Design Tokens:
The frontend utilizes a sleek dark/light responsive interface built with tailored HSL color tokens, glassmorphism cards, dynamic CPU/RAM progress gauges, and distinct visual badges for online, offline, and warning states.

---

## 6. SOFTWARE INSTALLATION & PROCEDURE

### 6.1 Code Editor Setup & Development Tools

Development Environment:
- IDE: Visual Studio Code with Python, Rust-Analyzer, ESLint, and Tauri extensions.
- Terminal: Windows PowerShell 5.1 / PowerShell 7+.
- Package Managers: Astral uv for Python virtual environments; npm for JavaScript libraries.
- Rust Toolchain: Rustup with stable-x86_64-pc-windows-msvc.

### 6.2 Backend Installation & Database Setup

Steps to install and run the host service locally:
1. Clone repository: git clone https://github.com/Avinash-076/Smart_lab_management_system.git
2. Navigate to backend: cd backend
3. Sync dependencies: uv sync
4. Run database migrations: uv run alembic upgrade head
5. Launch backend server: uv run uvicorn app.main:app --host 0.0.0.0 --port 18080 --reload
Interactive API docs: http://localhost:18080/docs

### 6.3 Frontend & Tauri Desktop Setup

Steps to install and build the desktop dashboard:
1. Navigate to frontend: cd frontend
2. Install npm packages: npm install
3. Run in browser dev mode: npm run dev
4. Run native desktop application: npx tauri dev
5. Compile production desktop binary: npx tauri build --no-bundle
The resulting binary is created at frontend/src-tauri/target/release/app.exe.

### 6.4 Client Agent Setup & Headless Enrollment

Steps to install and run the client agent:
1. Navigate to client_agent: cd client_agent
2. Sync dependencies: uv sync
3. Enroll workstation: uv run python main.py enroll --url 192.168.1.100 --key <ENROLL_KEY>
4. Install Windows service: uv run python main.py install
5. Start Windows service: uv run python main.py start
6. Verify credentials: uv run python main.py verify-credentials

### 6.5 Inno Setup Packaging

Standalone single-file installers are compiled using Inno Setup 6:
1. Host Installer: ISCC.exe installer/SLMS_Host_Setup.iss -> installer/output/SLMS_Host_Setup.exe
2. Client Agent Installer: ISCC.exe installer/SLMS_Client_Agent_Setup.iss -> installer/output/SLMS_Client_Agent_Setup.exe

---

## 7. USER INTERFACE GUIDE

### 7.1 Overview & Dashboard Navigation

The SLMS Host Dashboard provides an intuitive navigation bar with real-time badges:
- Dashboard: High-level lab summary, online/offline count, active alerts, and real-time CPU/RAM averages.
- Computers Matrix: Visual grid of all enrolled workstations with live status indicators.
- Software Inventory: Global catalog of all applications installed across lab computers.
- Issues & Tickets: Student problem reports with triage workflow.
- Reports & Audit: Exportable telemetry histories and administrative action logs.
- Settings: Alert thresholds, network configuration, and threat monitoring rules.

### 7.2 Workstation Monitoring Grid

The Computer Matrix tab renders each lab machine as an interactive workstation card:
- Green Badge: Online, normal telemetry.
- Yellow Badge: Warning (RAM > 80% or CPU > 85%).
- Red Badge: Critical threshold exceeded or computer suddenly disconnected.
- Grey Badge: Offline / powered down.
Clicking any card opens the deep-dive workstation panel showing process trees, network IP, MAC address, and disk partitions.

### 7.3 System Tray & Windows Action Center Toasts

When the dashboard is minimized, an SLMS icon sits in the Windows System Tray.
- Double-clicking the tray icon restores the window.
- Right-clicking reveals 'Show Dashboard' and 'Quit SLMS Host'.
- When an alert occurs, a native Windows toast notification slides in at the bottom-right corner of the screen with a chime sound and action buttons.

---

## 8. OPERATION MANUAL

### 8.1 Daily Lab Operations

1. Starting the Lab: The instructor logs into the Host PC. The Host Service starts automatically on Windows boot, and the Tauri dashboard launches from the desktop shortcut.
2. Monitoring Student Activity: As students boot their PCs, the Computer Matrix lights up green in real time.
3. Locking for Instructions / Exams: The instructor selects 'Select All' in the dashboard and clicks 'Lock Workstations'. All student screens immediately freeze with a custom lock screen message.
4. Releasing Workstations: The instructor clicks 'Unlock Workstations' to return control to students.

### 8.2 Managing Alerts & Process Termination

If a student runs an unapproved process or causes a memory leak:
1. A native Windows toast notification appears on the teacher's screen: '🚨 Critical Alert: RAM usage 94% on LAB-PC-12'.
2. The teacher clicks the notification to open LAB-PC-12's process list.
3. The teacher identifies the offending process (e.g. infinite loop script) and clicks 'Terminate Process'.
4. The command dispatches over WebSocket and terminates the process in under 500ms.

### 8.3 Troubleshooting Common Scenarios

Scenario 1: Workstation Shows Offline
- Check physical Ethernet cable or Wi-Fi connection.
- Run `sc query SLMSService` on workstation to confirm service is running.
- Inspect `%ProgramData%\SLMS\logs\agent.log` for connection error messages.

Scenario 2: Host Service Inaccessible
- Confirm host PC IP has not changed.
- Verify Port 18080 firewall rule via `netsh advfirewall firewall show rule name='SLMS Host Service'`.
- Verify service state with `sc query SLMSHostService`.

---

## 9. SYSTEM MODULES

### 9.1 Authentication & RBAC Module

Manages JWT access and refresh token issuance, bcrypt password hashing, and role permissions (Admin, Instructor, Technician).

### 9.2 Workstation Management & Enrollment Module

Issues unique 64-character enrollment tokens, validates workstation hardware signatures, and registers new lab machines.

### 9.3 Client Agent Background Service Module

Runs in Session 0 under NT SERVICE\SLMSService, orchestrating telemetry collection without user desktop disruption.

### 9.4 Telemetry Ingestion & Outbox Module

Combines a local client SQLite outbox queue with high-speed host batch ingestion, ensuring zero data loss during network failures.

### 9.5 Alert & Threshold Evaluation Module

Asynchronously evaluates system metrics against configurable thresholds (RAM, CPU, Disk) and generates notification records.

### 9.6 Remote Command & Control Module

Duplex WebSocket channel (/ws/client) supporting remote desktop locking, broadcast messaging, process killing, and system reboot.

### 9.7 Desktop Shell & System Tray Module

Tauri v2 native shell managing the close-to-tray lifecycle, system tray icon, and tray context menu.

### 9.8 Native Windows Toast Notification Module

Interfaces with the Windows WinRT notification subsystem via tauri-plugin-notification to display OS toast banners.

### 9.9 Reports & Database Management Module

Maintains SQLite WAL database tables and exports historical telemetry and audit logs to CSV and JSON formats.

---

## 10. SOURCE CODE & ARCHITECTURE

### 10.1 Directory Structure & Organization

Smart_lab_management_system/
├── backend/                 # FastAPI service on port 18080
│   ├── app/                 # Models, routes, schemas, services, websockets
│   └── service_runner.py    # Windows SCM host service runner
├── client_agent/            # Windows client agent service
│   ├── core/                # DPAPI credentials, outbox, security policies
│   ├── notifier/            # Session 1 desktop companion (SLMS_Notifier)
│   └── SLMS_Client_Agent.spec
├── frontend/                # React 19 dashboard
│   ├── src/                 # Pages, components, hooks, services
│   └── src-tauri/           # Tauri v2 Rust backend, system tray, notifications
└── installer/               # Inno Setup 6 packaging scripts

### 10.2 Core Implementation Snippets

1. Automatic Port 18080 Normalization (client_agent/core/security.py):
   netloc = parsed.netloc
   if parsed.port is None:
       netloc = f"{netloc}:18080"

2. System Tray Close-to-Tray (frontend/src-tauri/src/lib.rs):
   .on_window_event(|window, event| {
       if let WindowEvent::CloseRequested { api, .. } = event {
           api.prevent_close();
           let _ = window.hide();
       }
   })

3. Native Windows Toast Notification (frontend/src/services/nativeNotification.js):
   tauri.sendNotification({ title: fullTitle, body: fullBody });

### 10.3 Test Verification Suite

The system incorporates automated testing suites across all layers:
- Client Agent Security Tests: 22 passed tests (URL normalization, DPAPI, port 18080 defaulting).
- Frontend Tests: 271 passed tests across 22 test suites (Vitest).
- Backend Tests: REST endpoints, authentication, and WebSocket validation.

---

## 11. APPLICATIONS

### 11.1 Academic Computer Laboratories

Enables instructors in polytechnics and engineering colleges to supervise practical programming sessions, lock screens during tests, and distribute lab notices without commercial software fees.

### 11.2 University Campus Networks

Scalable across multiple lab departments (Computer Science, Electronics, Civil CAD labs) for centralized hardware and software inventory audits.

### 11.3 Software Training & Competitive Exam Centers

Ideal for online certification and examination testing centers where screens must be locked and active processes monitored for compliance.

### 11.4 IT Asset Management & Security Audits

Allows institutional IT departments to audit installed software versions, detect unauthorized tools, and verify workstation hardware configurations.

---

## 12. CONCLUSION AND FUTURE SCOPE

### 12.1 Conclusion

The Smart Lab Management System (SLMS) successfully solves the operational, technical, and resource challenges of managing modern academic computer laboratories. By migrating to dedicated port 18080, implementing automatic port resolution, adopting an ultra-lightweight Tauri v2 desktop shell, and providing robust offline SQLite outbox buffering, SLMS delivers enterprise-grade reliability with zero resource bloat. The system operates quietly in the background, keeping instructors informed through native Windows notifications while students focus on their practical coursework without disruption.

### 12.2 Future Scope

1. Cross-Platform Student Agents: Extending client agents to Linux (Ubuntu/Debian) for dual-boot lab workstations.
2. AI-Powered Anomaly Detection: Integrating local machine learning models to detect abnormal network traffic or software plagiarism patterns during lab exams.
3. Wake-on-LAN (WoL): Adding one-click remote wake and scheduled mass power-off to optimize institutional energy consumption.
4. Remote Terminal Access: Providing a secure web-based PowerShell/terminal bridge directly from the dashboard for remote technical support.

---

## 13. REFERENCES

### 13.1 Technical References

1. Microsoft Developer Network (MSDN) - Windows Service Control Manager and Session 0 Isolation Guidelines.
2. Microsoft Security Documentation - Windows Data Protection API (DPAPI) Crypt32 Architecture.
3. SQLite Consortium - Write-Ahead Logging (WAL) and High-Concurrency Concurrency Control.
4. RFC 6455 - The WebSocket Protocol Specification.
5. RFC 7519 - JSON Web Token (JWT) Architecture.

### 13.2 Software Tools, Libraries, and Documentation

1. FastAPI Documentation (https://fastapi.tiangolo.com/)
2. Tauri v2 Architecture & System Tray Documentation (https://v2.tauri.app/)
3. React 19 Official Documentation (https://react.dev/)
4. Inno Setup 6 Documentation - Jordan Russell (https://jrsoftware.org/isinfo.php)
5. Astral uv Python Package Manager (https://docs.astral.sh/uv/)

---
