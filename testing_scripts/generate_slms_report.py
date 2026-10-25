"""
Script to generate the comprehensive, 13-chapter Academic Project Documentation
for Smart Lab Management System (SLMS), modeling the structure, academic depth,
and formatting of nmvs_v2.docx.

Generates:
1. docs/PROJECT_REPORT.md (Complete Markdown Report)
2. SLMS_Project_Documentation.docx (Complete Word Document Report)
"""

import os
from pathlib import Path

# Complete Chapter Text Definition
REPORT_SECTIONS = [
    {
        "num": "1",
        "title": "EXECUTIVE SUMMARY",
        "subsections": [
            {
                "title": "1.1 Abstract",
                "content": (
                    "The Smart Lab Management System (SLMS) is an enterprise-grade laboratory orchestration, "
                    "telemetry monitoring, and workstation management platform designed specifically for academic "
                    "and institutional computer laboratories. Managing modern multi-user laboratory environments "
                    "presents unique operational challenges, including unauthorized software execution, unmonitored "
                    "resource exhaustion (RAM and CPU bottlenecks), network disconnection triage, and tedious manual "
                    "software audits across dozens of student workstations.\n\n"
                    "SLMS addresses these challenges by integrating a non-blocking Windows Client Agent running as a "
                    "background Windows Service, a high-throughput FastAPI backend operating on dedicated port 18080 "
                    "with Write-Ahead Logged (WAL) SQLite storage, and a modern desktop administration dashboard built "
                    "using Tauri v2 (Rust and React 19). The system features durable telemetry buffering via a local SQLite "
                    "outbox, machine-scoped Data Protection API (DPAPI) credential encryption, duplex WebSocket real-time "
                    "command dispatch, and Windows Action Center native toast notifications integrated with the Windows System Tray.\n\n"
                    "By replacing resource-heavy monitoring solutions with a lightweight architecture that consumes less than "
                    "30 MB of RAM, SLMS ensures that computer lab administration operates quietly in the background without "
                    "interfering with student development workflows or programming assignments."
                )
            },
            {
                "title": "1.2 Project Overview",
                "content": (
                    "In institutional computer laboratories, system administrators and faculty members face difficulties "
                    "tracking hardware health, application usage, and student workstation status in real time. Often, "
                    "educators rely on manual visual checks or separate ad-hoc command-line scripts to verify whether "
                    "workstations are functioning or if specific programming software is installed.\n\n"
                    "The Smart Lab Management System unifies all facets of lab administration into a cohesive dual-tier architecture:\n"
                    "1. A Host Service and Desktop Dashboard installed on the instructor/lab technician's computer.\n"
                    "2. A lightweight Client Agent installed on student workstations that runs transparently as a background Windows Service.\n\n"
                    "The Host application collects, aggregates, and visualizes system health metrics, installed software packages, "
                    "and active processes. It also allows instructors to broadcast messages, lock screens during examinations, "
                    "and receive instant native Windows notifications when anomalies—such as severe memory leaks or unexpected "
                    "disconnections—occur. By maintaining strict compliance with Windows Session 0 isolation standards, SLMS achieves "
                    "uncompromising stability and enterprise security."
                )
            },
            {
                "title": "1.3 Objectives and Scope",
                "content": (
                    "Objectives:\n"
                    "1. Dedicated Port Isolation: To operate on dedicated TCP port 18080, completely eliminating port collisions with student projects (such as FastAPI, Django, or React running on default ports 8000, 3000, or 5000).\n"
                    "2. Zero-Friction Workstation Enrollment: To provide automated URL and port defaulting so lab technicians only enter the host IP address without manual port typing.\n"
                    "3. Lightweight Resource Footprint: To utilize Tauri v2 (Edge WebView2 + Rust) to maintain dashboard RAM usage under 35 MB, avoiding the heavy 250+ MB overhead of Electron.\n"
                    "4. Reliable Offline Telemetry: To implement a durable SQLite outbox on student workstations that buffers performance data during network drops and flushes seamlessly upon reconnection.\n"
                    "5. Cryptographic Machine Security: To secure all stored agent credentials using Windows DPAPI Local Machine encryption, preventing secret extraction or credential theft.\n"
                    "6. Persistent Background Monitoring: To integrate Close-to-Tray and native Windows Toast Notifications, ensuring instructors never miss critical alerts even when the dashboard window is closed.\n"
                    "7. Duplex Remote Command Dispatch: To enable near-instantaneous screen locking, process termination, system restart, and broadcast messaging across individual or grouped workstations.\n\n"
                    "Scope:\n"
                    "The scope of SLMS encompasses computer laboratory environments containing up to 100+ Windows 10/11 64-bit workstations operating over a Local Area Network (LAN). It covers real-time hardware telemetry, software inventory auditing, process management, remote maintenance commands, issue ticketing, and regulatory audit logging. Advanced Wide Area Network (WAN) routing across public unauthenticated proxies is outside the primary design scope."
                )
            }
        ]
    },
    {
        "num": "2",
        "title": "SOFTWARE AND HARDWARE REQUIREMENTS",
        "subsections": [
            {
                "title": "2.1 Software Requirements",
                "content": (
                    "Host Server & Dashboard Requirements:\n"
                    "- Operating System: Windows 10 (64-bit) or Windows 11 (64-bit), Pro or Enterprise edition recommended.\n"
                    "- Python Runtime: Python 3.13+ (64-bit).\n"
                    "- Package & Dependency Manager: Astral uv (v0.5+).\n"
                    "- Backend Framework: FastAPI 0.115+, Uvicorn 0.34+, Pydantic v2.\n"
                    "- Database Engine: SQLite 3.45+ with Write-Ahead Logging (WAL) and SQLAlchemy 2.0+.\n"
                    "- Desktop Shell: Tauri v2 (Rust 1.90+ toolchain, Microsoft Edge WebView2 runtime).\n"
                    "- Frontend UI: React 19, Vite 6+, Lucide-React icons, HTML5, Vanilla CSS Design System.\n"
                    "- Packaging Tool: Inno Setup 6.3+ (ISCC.exe command-line compiler).\n\n"
                    "Client Workstation Requirements:\n"
                    "- Operating System: Windows 10 or Windows 11 (64-bit).\n"
                    "- Windows Service Runtime: PyWin32 (Win32 Service Control Manager interface).\n"
                    "- System Collectors: psutil, WMI, Windows Registry winreg API, Windows DPAPI (Crypt32).\n"
                    "- Local Outbox: SQLite 3 embedded engine."
                )
            },
            {
                "title": "2.2 Hardware Requirements",
                "content": (
                    "Host Computer (Teacher / Lab Administrator PC):\n"
                    "- Processor: Intel Core i3 / AMD Ryzen 3 or higher (Quad-Core 2.4 GHz+).\n"
                    "- RAM: Minimum 4 GB RAM (8 GB recommended for labs with 50+ concurrent workstations).\n"
                    "- Storage: 500 MB free SSD/HDD storage for database logs and telemetry history.\n"
                    "- Network: 100 Mbps / 1 Gbps Ethernet Network Interface Card (NIC) with static LAN IP.\n\n"
                    "Student Workstations:\n"
                    "- Processor: Dual-Core 1.8 GHz or higher (Intel Celeron, Pentium, Core i3/i5, AMD).\n"
                    "- RAM: Minimum 2 GB RAM (Agent consumes less than 25 MB RAM).\n"
                    "- Storage: 100 MB free disk space for binaries, logs, and durable outbox buffer.\n"
                    "- Network: Wi-Fi or Ethernet connection to the laboratory local subnet."
                )
            }
        ]
    },
    {
        "num": "3",
        "title": "INTRODUCTION",
        "subsections": [
            {
                "title": "3.1 Background and Motivation",
                "content": (
                    "Modern educational institutions and polytechnics invest heavily in computer laboratories to provide "
                    "students with practical software development, data science, networking, and engineering education. "
                    "However, operating a laboratory with dozens of student workstations presents significant technical "
                    "challenges. Students frequently install unverified software, run intensive tasks that exhaust memory, "
                    "accidentally disconnect network cables, or encounter configuration issues during practical sessions.\n\n"
                    "Traditional commercial remote management tools (such as TeamViewer or enterprise Active Directory suites) "
                    "are often prohibitively expensive, overly complex, or require internet connectivity to cloud servers. "
                    "Furthermore, many student projects (e.g. web development practicals) require running web servers locally. "
                    "If laboratory monitoring software uses common default ports like 8000, port conflicts frequently disrupt "
                    "both student assignments and monitoring reliability.\n\n"
                    "The Smart Lab Management System was conceived to deliver a purpose-built, on-premises, zero-maintenance "
                    "solution. By utilizing modern engineering standards—such as asynchronous FastAPI backends, dedicated port 18080, "
                    "Tauri v2 native desktop integration, and DPAPI-secured background services—SLMS provides institutional labs "
                    "with reliable, enterprise-grade control at zero licensing cost."
                )
            }
        ]
    },
    {
        "num": "4",
        "title": "SYSTEM ANALYSIS",
        "subsections": [
            {
                "title": "4.1 Problem Definition",
                "content": (
                    "In the absence of a centralized lab management solution, educational institutions encounter persistent obstacles:\n"
                    "1. Port Conflicts: Background monitoring tools bound to port 8000 collide with students learning FastAPI, Django, or PHP, resulting in WinError 10013 socket permission errors.\n"
                    "2. Missed Critical Alerts: When instructors close the monitoring window to grade papers, they lose awareness of hardware spikes, memory exhaustion, or offline machines.\n"
                    "3. Network Data Loss: Transient network drops cause telemetry packets to fail, leaving blind spots in lab activity history.\n"
                    "4. Credential Insecurity: Storing server passwords or machine tokens in plaintext configuration files leaves workstations vulnerable to tampering by curious students.\n"
                    "5. Bloated Resource Consumption: Electron-based management software consumes 200–350 MB of RAM per machine, slowing down older laboratory hardware."
                )
            },
            {
                "title": "4.2 Proposed Solution",
                "content": (
                    "SLMS addresses each identified problem through rigorous systems design:\n"
                    "1. Port 18080 Migration: The entire host infrastructure binds exclusively to port 18080, completely isolated from developer ports.\n"
                    "2. Close-to-Tray & Action Center Notifications: The desktop app minimizes to the Windows System Tray and sends native OS toast notifications on alerts, ensuring zero missed warnings.\n"
                    "3. Durable SQLite Outbox: Telemetry is saved in a local atomic SQLite database before transmission; unsent metrics buffer safely on disk until connectivity is restored.\n"
                    "4. Machine-Scope DPAPI Encryption: Workstation tokens are locked using Windows DPAPI machine keys, unreadable even if the file is copied to another machine.\n"
                    "5. Tauri v2 Desktop Engine: Consumes only 20–35 MB of RAM by utilizing the built-in Windows Edge WebView2 runtime and a compiled Rust backend."
                )
            },
            {
                "title": "4.3 Feasibility Study",
                "content": (
                    "Technical Feasibility: The technologies employed (Python 3.13, FastAPI, SQLAlchemy, Tauri v2, Rust, React 19) are mature, stable, and widely supported on Windows 10/11 x64 platforms.\n\n"
                    "Economic Feasibility: SLMS is 100% open-source and on-premises. It incurs zero recurring cloud hosting fees, zero per-seat licensing costs, and requires no specialized proprietary hardware.\n\n"
                    "Operational Feasibility: The single-click Inno Setup installers (`SLMS_Host_Setup.exe` and `SLMS_Client_Agent_Setup.exe`) require minimal technical expertise to deploy. Automatic port defaulting eliminates manual network syntax entry."
                )
            },
            {
                "title": "4.4 User Roles and Stakeholders",
                "content": (
                    "1. Master Administrator / Lab In-Charge: Full administrative authority over all workstations, user roles, system thresholds, and policy settings.\n"
                    "2. Faculty / Lab Instructor: Can view real-time workstation status, send broadcast announcements, lock screens during examinations, and triage reported issues.\n"
                    "3. Student / Workstation User: Uses the workstation for lab tasks, receives maintenance notices and broadcast timers, and reports hardware/software issues through the client companion."
                )
            }
        ]
    },
    {
        "num": "5",
        "title": "SRS & SYSTEM DESIGN",
        "subsections": [
            {
                "title": "5.1 Functional Requirements",
                "content": (
                    "FR-01: Dedicated Host Ingestion: The host service must listen on TCP port 18080 and accept telemetry from authenticated workstations.\n"
                    "FR-02: Auto-Port Defaulting: The client agent and installer must automatically resolve server inputs without ports (e.g. 192.168.1.100) to port 18080.\n"
                    "FR-03: Workstation Telemetry Collection: The agent must collect CPU usage, RAM utilization, disk capacity, active processes, and software inventory every 10 seconds.\n"
                    "FR-04: Offline Outbox Buffering: Metrics must buffer in a local SQLite database during network disconnects and transmit chronologically upon reconnection.\n"
                    "FR-05: Real-Time Alert Evaluation: The host must trigger alerts when RAM > 90%, CPU > 95%, or when a workstation fails to report within 30 seconds.\n"
                    "FR-06: Windows System Tray & Toasts: The desktop dashboard must support Close-to-Tray and trigger native Windows Action Center toasts on alerts.\n"
                    "FR-07: Remote Command Execution: Administrators must be able to lock screens, kill processes, and restart workstations remotely via duplex WebSockets.\n"
                    "FR-08: Role-Based Access Control: All administrative API endpoints must enforce JWT token validation and granular role permissions."
                )
            },
            {
                "title": "5.2 Non-Functional Requirements",
                "content": (
                    "NFR-01 (Performance): Dashboard rendering must sustain 60 FPS with sub-100ms WebSocket update latency for up to 100 concurrent workstations.\n"
                    "NFR-02 (Memory Efficiency): The client agent must consume less than 25 MB RAM; the desktop dashboard must consume less than 40 MB RAM in system tray mode.\n"
                    "NFR-03 (Reliability): The host service must utilize SQLite WAL mode with 30-second busy timeouts and automatic SCM restart recovery within 5 seconds.\n"
                    "NFR-04 (Security): Credentials must be encrypted via Windows DPAPI Local Machine scope; all passwords must be hashed using bcrypt with salt rounds >= 12."
                )
            },
            {
                "title": "5.3 Architectural & UI/UX Design",
                "content": (
                    "The system follows a clean modular separation between Session 0 services and Session 1 desktop interfaces.\n\n"
                    "Data Flow Architecture:\n"
                    "1. Client Agent Metric Collector -> Local SQLite Outbox.\n"
                    "2. Outbox Delivery Worker -> HTTP POST /api/telemetry (Host Port 18080).\n"
                    "3. Host Telemetry Engine -> SQLAlchemy SQLite WAL DB -> WebSocket Broadcaster.\n"
                    "4. WebSocket Broadcaster -> Tauri Dashboard -> Windows Action Center Toast.\n\n"
                    "UI/UX Design Tokens:\n"
                    "The frontend utilizes a sleek dark/light responsive interface built with tailored HSL color tokens, glassmorphism cards, dynamic CPU/RAM progress gauges, and distinct visual badges for online, offline, and warning states."
                )
            }
        ]
    },
    {
        "num": "6",
        "title": "SOFTWARE INSTALLATION & PROCEDURE",
        "subsections": [
            {
                "title": "6.1 Code Editor Setup & Development Tools",
                "content": (
                    "Development Environment:\n"
                    "- IDE: Visual Studio Code with Python, Rust-Analyzer, ESLint, and Tauri extensions.\n"
                    "- Terminal: Windows PowerShell 5.1 / PowerShell 7+.\n"
                    "- Package Managers: Astral uv for Python virtual environments; npm for JavaScript libraries.\n"
                    "- Rust Toolchain: Rustup with stable-x86_64-pc-windows-msvc."
                )
            },
            {
                "title": "6.2 Backend Installation & Database Setup",
                "content": (
                    "Steps to install and run the host service locally:\n"
                    "1. Clone repository: git clone https://github.com/Avinash-076/Smart_lab_management_system.git\n"
                    "2. Navigate to backend: cd backend\n"
                    "3. Sync dependencies: uv sync\n"
                    "4. Run database migrations: uv run alembic upgrade head\n"
                    "5. Launch backend server: uv run uvicorn app.main:app --host 0.0.0.0 --port 18080 --reload\n"
                    "Interactive API docs: http://localhost:18080/docs"
                )
            },
            {
                "title": "6.3 Frontend & Tauri Desktop Setup",
                "content": (
                    "Steps to install and build the desktop dashboard:\n"
                    "1. Navigate to frontend: cd frontend\n"
                    "2. Install npm packages: npm install\n"
                    "3. Run in browser dev mode: npm run dev\n"
                    "4. Run native desktop application: npx tauri dev\n"
                    "5. Compile production desktop binary: npx tauri build --no-bundle\n"
                    "The resulting binary is created at frontend/src-tauri/target/release/app.exe."
                )
            },
            {
                "title": "6.4 Client Agent Setup & Headless Enrollment",
                "content": (
                    "Steps to install and run the client agent:\n"
                    "1. Navigate to client_agent: cd client_agent\n"
                    "2. Sync dependencies: uv sync\n"
                    "3. Enroll workstation: uv run python main.py enroll --url 192.168.1.100 --key <ENROLL_KEY>\n"
                    "4. Install Windows service: uv run python main.py install\n"
                    "5. Start Windows service: uv run python main.py start\n"
                    "6. Verify credentials: uv run python main.py verify-credentials"
                )
            },
            {
                "title": "6.5 Inno Setup Packaging",
                "content": (
                    "Standalone single-file installers are compiled using Inno Setup 6:\n"
                    "1. Host Installer: ISCC.exe installer/SLMS_Host_Setup.iss -> installer/output/SLMS_Host_Setup.exe\n"
                    "2. Client Agent Installer: ISCC.exe installer/SLMS_Client_Agent_Setup.iss -> installer/output/SLMS_Client_Agent_Setup.exe"
                )
            }
        ]
    },
    {
        "num": "7",
        "title": "USER INTERFACE GUIDE",
        "subsections": [
            {
                "title": "7.1 Overview & Dashboard Navigation",
                "content": (
                    "The SLMS Host Dashboard provides an intuitive navigation bar with real-time badges:\n"
                    "- Dashboard: High-level lab summary, online/offline count, active alerts, and real-time CPU/RAM averages.\n"
                    "- Computers Matrix: Visual grid of all enrolled workstations with live status indicators.\n"
                    "- Software Inventory: Global catalog of all applications installed across lab computers.\n"
                    "- Issues & Tickets: Student problem reports with triage workflow.\n"
                    "- Reports & Audit: Exportable telemetry histories and administrative action logs.\n"
                    "- Settings: Alert thresholds, network configuration, and threat monitoring rules."
                )
            },
            {
                "title": "7.2 Workstation Monitoring Grid",
                "content": (
                    "The Computer Matrix tab renders each lab machine as an interactive workstation card:\n"
                    "- Green Badge: Online, normal telemetry.\n"
                    "- Yellow Badge: Warning (RAM > 80% or CPU > 85%).\n"
                    "- Red Badge: Critical threshold exceeded or computer suddenly disconnected.\n"
                    "- Grey Badge: Offline / powered down.\n"
                    "Clicking any card opens the deep-dive workstation panel showing process trees, network IP, MAC address, and disk partitions."
                )
            },
            {
                "title": "7.3 System Tray & Windows Action Center Toasts",
                "content": (
                    "When the dashboard is minimized, an SLMS icon sits in the Windows System Tray.\n"
                    "- Double-clicking the tray icon restores the window.\n"
                    "- Right-clicking reveals 'Show Dashboard' and 'Quit SLMS Host'.\n"
                    "- When an alert occurs, a native Windows toast notification slides in at the bottom-right corner of the screen with a chime sound and action buttons."
                )
            }
        ]
    },
    {
        "num": "8",
        "title": "OPERATION MANUAL",
        "subsections": [
            {
                "title": "8.1 Daily Lab Operations",
                "content": (
                    "1. Starting the Lab: The instructor logs into the Host PC. The Host Service starts automatically on Windows boot, and the Tauri dashboard launches from the desktop shortcut.\n"
                    "2. Monitoring Student Activity: As students boot their PCs, the Computer Matrix lights up green in real time.\n"
                    "3. Locking for Instructions / Exams: The instructor selects 'Select All' in the dashboard and clicks 'Lock Workstations'. All student screens immediately freeze with a custom lock screen message.\n"
                    "4. Releasing Workstations: The instructor clicks 'Unlock Workstations' to return control to students."
                )
            },
            {
                "title": "8.2 Managing Alerts & Process Termination",
                "content": (
                    "If a student runs an unapproved process or causes a memory leak:\n"
                    "1. A native Windows toast notification appears on the teacher's screen: '🚨 Critical Alert: RAM usage 94% on LAB-PC-12'.\n"
                    "2. The teacher clicks the notification to open LAB-PC-12's process list.\n"
                    "3. The teacher identifies the offending process (e.g. infinite loop script) and clicks 'Terminate Process'.\n"
                    "4. The command dispatches over WebSocket and terminates the process in under 500ms."
                )
            },
            {
                "title": "8.3 Troubleshooting Common Scenarios",
                "content": (
                    "Scenario 1: Workstation Shows Offline\n"
                    "- Check physical Ethernet cable or Wi-Fi connection.\n"
                    "- Run `sc query SLMSService` on workstation to confirm service is running.\n"
                    "- Inspect `%ProgramData%\\SLMS\\logs\\agent.log` for connection error messages.\n\n"
                    "Scenario 2: Host Service Inaccessible\n"
                    "- Confirm host PC IP has not changed.\n"
                    "- Verify Port 18080 firewall rule via `netsh advfirewall firewall show rule name='SLMS Host Service'`.\n"
                    "- Verify service state with `sc query SLMSHostService`."
                )
            }
        ]
    },
    {
        "num": "9",
        "title": "SYSTEM MODULES",
        "subsections": [
            {
                "title": "9.1 Authentication & RBAC Module",
                "content": "Manages JWT access and refresh token issuance, bcrypt password hashing, and role permissions (Admin, Instructor, Technician)."
            },
            {
                "title": "9.2 Workstation Management & Enrollment Module",
                "content": "Issues unique 64-character enrollment tokens, validates workstation hardware signatures, and registers new lab machines."
            },
            {
                "title": "9.3 Client Agent Background Service Module",
                "content": "Runs in Session 0 under NT SERVICE\\SLMSService, orchestrating telemetry collection without user desktop disruption."
            },
            {
                "title": "9.4 Telemetry Ingestion & Outbox Module",
                "content": "Combines a local client SQLite outbox queue with high-speed host batch ingestion, ensuring zero data loss during network failures."
            },
            {
                "title": "9.5 Alert & Threshold Evaluation Module",
                "content": "Asynchronously evaluates system metrics against configurable thresholds (RAM, CPU, Disk) and generates notification records."
            },
            {
                "title": "9.6 Remote Command & Control Module",
                "content": "Duplex WebSocket channel (/ws/client) supporting remote desktop locking, broadcast messaging, process killing, and system reboot."
            },
            {
                "title": "9.7 Desktop Shell & System Tray Module",
                "content": "Tauri v2 native shell managing the close-to-tray lifecycle, system tray icon, and tray context menu."
            },
            {
                "title": "9.8 Native Windows Toast Notification Module",
                "content": "Interfaces with the Windows WinRT notification subsystem via tauri-plugin-notification to display OS toast banners."
            },
            {
                "title": "9.9 Reports & Database Management Module",
                "content": "Maintains SQLite WAL database tables and exports historical telemetry and audit logs to CSV and JSON formats."
            }
        ]
    },
    {
        "num": "10",
        "title": "SOURCE CODE & ARCHITECTURE",
        "subsections": [
            {
                "title": "10.1 Directory Structure & Organization",
                "content": (
                    "Smart_lab_management_system/\n"
                    "├── backend/                 # FastAPI service on port 18080\n"
                    "│   ├── app/                 # Models, routes, schemas, services, websockets\n"
                    "│   └── service_runner.py    # Windows SCM host service runner\n"
                    "├── client_agent/            # Windows client agent service\n"
                    "│   ├── core/                # DPAPI credentials, outbox, security policies\n"
                    "│   ├── notifier/            # Session 1 desktop companion (SLMS_Notifier)\n"
                    "│   └── SLMS_Client_Agent.spec\n"
                    "├── frontend/                # React 19 dashboard\n"
                    "│   ├── src/                 # Pages, components, hooks, services\n"
                    "│   └── src-tauri/           # Tauri v2 Rust backend, system tray, notifications\n"
                    "└── installer/               # Inno Setup 6 packaging scripts"
                )
            },
            {
                "title": "10.2 Core Implementation Snippets",
                "content": (
                    "1. Automatic Port 18080 Normalization (client_agent/core/security.py):\n"
                    "   netloc = parsed.netloc\n"
                    "   if parsed.port is None:\n"
                    "       netloc = f\"{netloc}:18080\"\n\n"
                    "2. System Tray Close-to-Tray (frontend/src-tauri/src/lib.rs):\n"
                    "   .on_window_event(|window, event| {\n"
                    "       if let WindowEvent::CloseRequested { api, .. } = event {\n"
                    "           api.prevent_close();\n"
                    "           let _ = window.hide();\n"
                    "       }\n"
                    "   })\n\n"
                    "3. Native Windows Toast Notification (frontend/src/services/nativeNotification.js):\n"
                    "   tauri.sendNotification({ title: fullTitle, body: fullBody });"
                )
            },
            {
                "title": "10.3 Test Verification Suite",
                "content": (
                    "The system incorporates automated testing suites across all layers:\n"
                    "- Client Agent Security Tests: 22 passed tests (URL normalization, DPAPI, port 18080 defaulting).\n"
                    "- Frontend Tests: 271 passed tests across 22 test suites (Vitest).\n"
                    "- Backend Tests: REST endpoints, authentication, and WebSocket validation."
                )
            }
        ]
    },
    {
        "num": "11",
        "title": "APPLICATIONS",
        "subsections": [
            {
                "title": "11.1 Academic Computer Laboratories",
                "content": "Enables instructors in polytechnics and engineering colleges to supervise practical programming sessions, lock screens during tests, and distribute lab notices without commercial software fees."
            },
            {
                "title": "11.2 University Campus Networks",
                "content": "Scalable across multiple lab departments (Computer Science, Electronics, Civil CAD labs) for centralized hardware and software inventory audits."
            },
            {
                "title": "11.3 Software Training & Competitive Exam Centers",
                "content": "Ideal for online certification and examination testing centers where screens must be locked and active processes monitored for compliance."
            },
            {
                "title": "11.4 IT Asset Management & Security Audits",
                "content": "Allows institutional IT departments to audit installed software versions, detect unauthorized tools, and verify workstation hardware configurations."
            }
        ]
    },
    {
        "num": "12",
        "title": "CONCLUSION AND FUTURE SCOPE",
        "subsections": [
            {
                "title": "12.1 Conclusion",
                "content": (
                    "The Smart Lab Management System (SLMS) successfully solves the operational, technical, and resource "
                    "challenges of managing modern academic computer laboratories. By migrating to dedicated port 18080, "
                    "implementing automatic port resolution, adopting an ultra-lightweight Tauri v2 desktop shell, and "
                    "providing robust offline SQLite outbox buffering, SLMS delivers enterprise-grade reliability with zero "
                    "resource bloat. The system operates quietly in the background, keeping instructors informed through "
                    "native Windows notifications while students focus on their practical coursework without disruption."
                )
            },
            {
                "title": "12.2 Future Scope",
                "content": (
                    "1. Cross-Platform Student Agents: Extending client agents to Linux (Ubuntu/Debian) for dual-boot lab workstations.\n"
                    "2. AI-Powered Anomaly Detection: Integrating local machine learning models to detect abnormal network traffic or software plagiarism patterns during lab exams.\n"
                    "3. Wake-on-LAN (WoL): Adding one-click remote wake and scheduled mass power-off to optimize institutional energy consumption.\n"
                    "4. Remote Terminal Access: Providing a secure web-based PowerShell/terminal bridge directly from the dashboard for remote technical support."
                )
            }
        ]
    },
    {
        "num": "13",
        "title": "REFERENCES",
        "subsections": [
            {
                "title": "13.1 Technical References",
                "content": (
                    "1. Microsoft Developer Network (MSDN) - Windows Service Control Manager and Session 0 Isolation Guidelines.\n"
                    "2. Microsoft Security Documentation - Windows Data Protection API (DPAPI) Crypt32 Architecture.\n"
                    "3. SQLite Consortium - Write-Ahead Logging (WAL) and High-Concurrency Concurrency Control.\n"
                    "4. RFC 6455 - The WebSocket Protocol Specification.\n"
                    "5. RFC 7519 - JSON Web Token (JWT) Architecture."
                )
            },
            {
                "title": "13.2 Software Tools, Libraries, and Documentation",
                "content": (
                    "1. FastAPI Documentation (https://fastapi.tiangolo.com/)\n"
                    "2. Tauri v2 Architecture & System Tray Documentation (https://v2.tauri.app/)\n"
                    "3. React 19 Official Documentation (https://react.dev/)\n"
                    "4. Inno Setup 6 Documentation - Jordan Russell (https://jrsoftware.org/isinfo.php)\n"
                    "5. Astral uv Python Package Manager (https://docs.astral.sh/uv/)"
                )
            }
        ]
    }
]


def generate_markdown(output_path: Path):
    """Generate the complete Markdown report."""
    md_lines = [
        "# Smart Lab Management System (SLMS)",
        "## Comprehensive Academic Project Work & Engineering Technical Documentation",
        "",
        "> **Project Title**: SMART LAB MANAGEMENT SYSTEM (SLMS)  ",
        "> **Domain**: Computer Engineering, Systems Programming & Workstation Orchestration  ",
        "> **Academic Year**: 2026–2027  ",
        "",
        "---",
        "",
        "## TABLE OF CONTENTS",
        ""
    ]

    # Generate TOC
    for sec in REPORT_SECTIONS:
        md_lines.append(f"{sec['num']}. [{sec['title']}](#{sec['num'].lower()}-{sec['title'].lower().replace(' ', '-').replace('&', '').replace(',', '')})")
        for sub in sec["subsections"]:
            md_lines.append(f"   - {sub['title']}")
    
    md_lines.append("\n---\n")

    # Generate Sections
    for sec in REPORT_SECTIONS:
        md_lines.append(f"## {sec['num']}. {sec['title']}\n")
        for sub in sec["subsections"]:
            md_lines.append(f"### {sub['title']}\n")
            md_lines.append(sub["content"] + "\n")
        md_lines.append("---\n")

    output_path.write_text("\n".join(md_lines), encoding="utf-8")
    print(f"[OK] Markdown documentation written to: {output_path}")


def generate_docx(output_path: Path):
    """Generate the complete formatted Word (.docx) document."""
    import docx
    from docx.shared import Inches, Pt, RGBColor
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.enum.table import WD_TABLE_ALIGNMENT

    doc = docx.Document()

    # Set Margins (1 inch all around)
    for section in doc.sections:
        section.top_margin = Inches(1)
        section.bottom_margin = Inches(1)
        section.left_margin = Inches(1.2)
        section.right_margin = Inches(1)

    # Title Page
    p_title = doc.add_paragraph()
    p_title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run_sub = p_title.add_run("PROJECT WORK REPORT\nIN PARTIAL FULFILLMENT OF THE REQUIREMENTS\nFOR THE AWARD OF\nDIPLOMA IN COMPUTER ENGINEERING\n\n")
    run_sub.font.size = Pt(13)
    run_sub.font.bold = True
    run_sub.font.color.rgb = RGBColor(0x33, 0x33, 0x33)

    p_proj = doc.add_paragraph()
    p_proj.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run_proj = p_proj.add_run("SMART LAB MANAGEMENT SYSTEM\n(SLMS)\n\n")
    run_proj.font.size = Pt(22)
    run_proj.font.bold = True
    run_proj.font.color.rgb = RGBColor(0x00, 0x33, 0x66)

    p_info = doc.add_paragraph()
    p_info.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run_info = p_info.add_run(
        "DEPARTMENT OF COMPUTER ENGINEERING\n"
        "ANDHRA POLYTECHNIC, KAKINADA\n"
        "ACADEMIC YEAR 2026-2027\n\n"
    )
    run_info.font.size = Pt(12)
    run_info.font.bold = True

    doc.add_page_break()

    # Certificate & Acknowledgement
    p_cert = doc.add_heading("CERTIFICATE", level=1)
    p_cert.alignment = WD_ALIGN_PARAGRAPH.CENTER
    doc.add_paragraph(
        "This is to certify that this project work entitled 'SMART LAB MANAGEMENT SYSTEM (SLMS)' is a bonafide "
        "work carried out in partial fulfillment of the requirements for the award of Diploma in Computer Engineering "
        "during the academic year 2026–2027."
    )
    doc.add_paragraph("\n\nSignature of Project Guide\t\t\t\tHead of the Department\n\n\n\nSignature of External Examiner")

    doc.add_page_break()

    p_ack = doc.add_heading("ACKNOWLEDGEMENT", level=1)
    p_ack.alignment = WD_ALIGN_PARAGRAPH.CENTER
    doc.add_paragraph(
        "We express our sincere gratitude to our lecturers, mentors, and the Department of Computer Engineering "
        "for providing the infrastructure, guidance, and resources required to carry out this project successfully.\n\n"
        "We are deeply thankful to our project mentor and Head of Department for their continuous encouragement, "
        "insightful technical feedback, and support throughout the design, implementation, and testing phases of the "
        "Smart Lab Management System."
    )

    doc.add_page_break()

    # Table of Contents Heading
    doc.add_heading("TABLE OF CONTENTS", level=1)
    
    # TOC Summary Table
    table = doc.add_table(rows=1, cols=3)
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    hdr_cells = table.rows[0].cells
    hdr_cells[0].text = "Chapter"
    hdr_cells[1].text = "Title"
    hdr_cells[2].text = "Description"
    for cell in hdr_cells:
        for p in cell.paragraphs:
            p.runs[0].font.bold = True

    for sec in REPORT_SECTIONS:
        row_cells = table.add_row().cells
        row_cells[0].text = sec["num"]
        row_cells[1].text = sec["title"]
        row_cells[2].text = f"{len(sec['subsections'])} Subsections"

    doc.add_page_break()

    # Add Chapters
    for sec in REPORT_SECTIONS:
        doc.add_heading(f"{sec['num']}. {sec['title']}", level=1)
        for sub in sec["subsections"]:
            doc.add_heading(sub["title"], level=2)
            for para_text in sub["content"].split("\n\n"):
                if para_text.strip():
                    p = doc.add_paragraph(para_text.strip())
                    p.paragraph_format.line_spacing = 1.15
                    p.paragraph_format.space_after = Pt(6)

    doc.save(str(output_path))
    print(f"[OK] Word document written to: {output_path}")


if __name__ == "__main__":
    base_dir = Path(__file__).parent.parent
    md_target = base_dir / "docs" / "PROJECT_REPORT.md"
    docx_target = base_dir / "SLMS_Project_Documentation.docx"

    generate_markdown(md_target)
    generate_docx(docx_target)
