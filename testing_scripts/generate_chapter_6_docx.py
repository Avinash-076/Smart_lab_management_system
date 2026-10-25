"""
Script to generate the complete, professionally formatted Word Document (.docx)
for CHAPTER 6: SOFTWARE INSTALLATION & PROCEDURE for Smart Lab Management System (SLMS).
"""

import os
from pathlib import Path
import docx
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_ALIGN_VERTICAL
from docx.oxml import OxmlElement, parse_xml
from docx.oxml.ns import nsdecls, qn

def set_cell_background(cell, fill_hex):
    """Set background color of a table cell."""
    tc_pr = cell._tc.get_or_add_tcPr()
    shd = parse_xml(f'<w:shd {nsdecls("w")} w:fill="{fill_hex}"/>')
    tc_pr.append(shd)

def set_cell_margins(cell, top=100, bottom=100, left=150, right=150):
    """Set inner padding for a table cell."""
    tc_pr = cell._tc.get_or_add_tcPr()
    tc_mar = parse_xml(
        f'<w:tcMar {nsdecls("w")}>'
        f'<w:top w:w="{top}" w:type="dxa"/>'
        f'<w:bottom w:w="{bottom}" w:type="dxa"/>'
        f'<w:left w:w="{left}" w:type="dxa"/>'
        f'<w:right w:w="{right}" w:type="dxa"/>'
        f'</w:tcMar>'
    )
    tc_pr.append(tc_mar)

def add_code_block(doc, code_text):
    """Add a shaded box containing monospaced command/code."""
    tbl = doc.add_table(rows=1, cols=1)
    tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
    tbl.autofit = False
    
    cell = tbl.cell(0, 0)
    cell.width = Inches(6.5)
    set_cell_background(cell, "F3F4F6")
    set_cell_margins(cell, top=120, bottom=120, left=180, right=180)
    
    # Border
    tc_pr = cell._tc.get_or_add_tcPr()
    borders = parse_xml(
        f'<w:tcBorders {nsdecls("w")}>'
        f'<w:top w:val="none"/>'
        f'<w:left w:val="single" w:sz="18" w:space="0" w:color="2563EB"/>'
        f'<w:bottom w:val="none"/>'
        f'<w:right w:val="none"/>'
        f'</w:tcBorders>'
    )
    tc_pr.append(borders)
    
    p = cell.paragraphs[0]
    p.paragraph_format.space_before = Pt(2)
    p.paragraph_format.space_after = Pt(2)
    p.paragraph_format.line_spacing = 1.15
    run = p.add_run(code_text.strip())
    run.font.name = "Consolas"
    run.font.size = Pt(9.5)
    run.font.color.rgb = RGBColor(0x1F, 0x29, 0x37)

    # Empty paragraph after table for spacing
    p_after = doc.add_paragraph()
    p_after.paragraph_format.space_before = Pt(0)
    p_after.paragraph_format.space_after = Pt(4)

def add_styled_heading(doc, text, level):
    h = doc.add_heading(text, level=level)
    h.paragraph_format.keep_with_next = True
    run = h.runs[0]
    if level == 1:
        h.paragraph_format.space_before = Pt(18)
        h.paragraph_format.space_after = Pt(8)
        run.font.name = "Calibri"
        run.font.size = Pt(18)
        run.font.bold = True
        run.font.color.rgb = RGBColor(0x00, 0x33, 0x66) # Deep Navy
    elif level == 2:
        h.paragraph_format.space_before = Pt(14)
        h.paragraph_format.space_after = Pt(6)
        run.font.name = "Calibri"
        run.font.size = Pt(14)
        run.font.bold = True
        run.font.color.rgb = RGBColor(0x1F, 0x4E, 0x79) # Slate Blue
    elif level == 3:
        h.paragraph_format.space_before = Pt(10)
        h.paragraph_format.space_after = Pt(4)
        run.font.name = "Calibri"
        run.font.size = Pt(11.5)
        run.font.bold = True
        run.font.color.rgb = RGBColor(0x2E, 0x40, 0x53) # Charcoal
    return h

def add_body_paragraph(doc, text, bold_prefix=None):
    p = doc.add_paragraph()
    p.paragraph_format.line_spacing = 1.15
    p.paragraph_format.space_after = Pt(6)
    if bold_prefix:
        r_pre = p.add_run(bold_prefix)
        r_pre.font.name = "Calibri"
        r_pre.font.size = Pt(11)
        r_pre.font.bold = True
        r_pre.font.color.rgb = RGBColor(0x11, 0x18, 0x27)
    run = p.add_run(text)
    run.font.name = "Calibri"
    run.font.size = Pt(11)
    run.font.color.rgb = RGBColor(0x2B, 0x2B, 0x2B)
    return p

def add_bullet_item(doc, bold_title, text):
    p = doc.add_paragraph(style='List Bullet')
    p.paragraph_format.line_spacing = 1.15
    p.paragraph_format.space_after = Pt(4)
    r_bold = p.add_run(bold_title + ": ")
    r_bold.font.name = "Calibri"
    r_bold.font.size = Pt(11)
    r_bold.font.bold = True
    r_bold.font.color.rgb = RGBColor(0x1F, 0x29, 0x37)
    
    r_text = p.add_run(text)
    r_text.font.name = "Calibri"
    r_text.font.size = Pt(11)
    r_text.font.color.rgb = RGBColor(0x37, 0x41, 0x51)
    return p

def build_chapter_6_docx(output_path: Path):
    doc = docx.Document()

    # Page Margins (Standard Academic 1-inch margins, 1.25-inch left margin for binding)
    for section in doc.sections:
        section.top_margin = Inches(1.0)
        section.bottom_margin = Inches(1.0)
        section.left_margin = Inches(1.25)
        section.right_margin = Inches(1.0)

    # Document Header Title
    p_chap = doc.add_paragraph()
    p_chap.paragraph_format.space_before = Pt(0)
    p_chap.paragraph_format.space_after = Pt(2)
    p_chap.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r_chap_num = p_chap.add_run("CHAPTER 6\n")
    r_chap_num.font.name = "Calibri"
    r_chap_num.font.size = Pt(14)
    r_chap_num.font.bold = True
    r_chap_num.font.color.rgb = RGBColor(0x00, 0x33, 0x66)

    r_chap_title = p_chap.add_run("SOFTWARE INSTALLATION & PROCEDURE")
    r_chap_title.font.name = "Calibri"
    r_chap_title.font.size = Pt(20)
    r_chap_title.font.bold = True
    r_chap_title.font.color.rgb = RGBColor(0x00, 0x33, 0x66)

    # Dividing Rule
    p_div = doc.add_paragraph()
    p_div.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_div.paragraph_format.space_after = Pt(12)
    r_div = p_div.add_run("―" * 45)
    r_div.font.color.rgb = RGBColor(0x9C, 0xA3, 0xAF)

    # Intro Paragraph
    add_body_paragraph(
        doc,
        "This chapter outlines the step-by-step installation, environment setup, and deployment procedure for the Smart Lab "
        "Management System (SLMS). It provides comprehensive guidelines for setting up the development environment, installing core "
        "runtime dependencies, configuring the FastAPI backend on dedicated port 18080, building the Tauri v2 native desktop "
        "dashboard, enrolling client workstations into Windows Service Control Manager (Session 0), and compiling automated "
        "standalone Inno Setup installers for mass deployment."
    )

    # =========================================================================
    # 6.1 Code Editor and Development Environment Setup
    # =========================================================================
    add_styled_heading(doc, "6.1 Code Editor and Development Environment Setup (VS Code)", level=2)
    add_body_paragraph(
        doc,
        "The development and maintenance of SLMS requires an Integrated Development Environment (IDE) capable of managing a "
        "polyglot codebase spanning Python 3.13, Rust, React 19 (TypeScript/JSX), and Inno Setup Pascal Script. Visual Studio Code "
        "(64-bit) serves as the primary IDE."
    )
    add_styled_heading(doc, "Recommended Extensions & Tooling Configuration", level=3)
    add_bullet_item(doc, "Python & Pylance (Microsoft)", "Provides IntelliSense, static type checking, code navigation, and syntax highlighting for FastAPI backend routes and client agent telemetry collectors.")
    add_bullet_item(doc, "rust-analyzer (Rust Community)", "Provides full code analysis, macro expansion, and compile-error reporting for the Tauri v2 Rust native desktop engine (frontend/src-tauri).")
    add_bullet_item(doc, "Tauri Extension (Tauri Apps)", "Facilitates Tauri v2 configuration validation, build script execution, and native window debugging.")
    add_bullet_item(doc, "ESLint & Prettier", "Enforces code quality, ECMAScript standards, and uniform indentation across React 19 frontend components and Vite bundling scripts.")
    add_bullet_item(doc, "Windows PowerShell 7+", "Used as the integrated terminal shell for running non-blocking background workers, service control commands, and build scripts with elevated administrative privileges.")

    # =========================================================================
    # 6.2 Runtime Environments and Development Tools
    # =========================================================================
    add_styled_heading(doc, "6.2 Runtime Environments and Development Tools", level=2)
    add_body_paragraph(
        doc,
        "Before building or launching SLMS, the underlying runtime toolchains must be verified on the host machine. The system "
        "leverages modern package managers to ensure deterministic, reproducible builds."
    )

    add_styled_heading(doc, "1. Python 3.13+ (64-Bit Runtime)", level=3)
    add_body_paragraph(
        doc,
        "Python 3.13 provides native performance enhancements and free-threaded execution optimizations. It must be installed with the "
        "'Add python.exe to PATH' option selected. Verification command:"
    )
    add_code_block(doc, "python --version\n# Expected Output: Python 3.13.x (or higher)")

    add_styled_heading(doc, "2. Astral uv Package Manager (v0.5+)", level=3)
    add_body_paragraph(
        doc,
        "Astral uv is an extremely fast, Rust-based Python package resolver and virtual environment manager. It replaces traditional pip and "
        "virtualenv, synchronizing dependencies in milliseconds. Installed via PowerShell:"
    )
    add_code_block(doc, 'powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"\nuv --version')

    add_styled_heading(doc, "3. Node.js (v18+) and npm", level=3)
    add_body_paragraph(
        doc,
        "Node.js is required for building the React 19 single-page application and compiling assets through Vite. Verification:"
    )
    add_code_block(doc, "node --version\nnpm --version")

    add_styled_heading(doc, "4. Rust Toolchain (rustup)", level=3)
    add_body_paragraph(
        doc,
        "The Tauri v2 desktop shell is built with Rust for native speed, zero-overhead window controls, and native Windows Action Center "
        "toast notifications. Installed with the MSVC toolchain:"
    )
    add_code_block(doc, "rustup default stable-x86_64-pc-windows-msvc\ncargo --version")

    add_styled_heading(doc, "5. Microsoft Edge WebView2 Runtime", level=3)
    add_body_paragraph(
        doc,
        "Tauri uses the OS-native Microsoft Edge WebView2 runtime instead of bundling Chromium. This runtime is pre-installed on modern "
        "Windows 10/11 platforms, reducing application memory consumption from ~300 MB down to ~25 MB."
    )

    # =========================================================================
    # 6.3 Backend Service Setup and Database Configuration
    # =========================================================================
    add_styled_heading(doc, "6.3 Backend Service Setup and Database Configuration (Port 18080)", level=2)
    add_body_paragraph(
        doc,
        "The SLMS Host Backend is built on FastAPI and Uvicorn. To prevent port conflicts with student development environments "
        "(such as Django or FastAPI on port 8000, React on port 3000, or Flask on port 5000), SLMS is hard-coded to bind to dedicated port 18080."
    )

    add_body_paragraph(doc, "Step 1: Clone Repository and Navigate to Backend", bold_prefix=None)
    add_code_block(doc, "git clone https://github.com/Avinash-076/Smart_lab_management_system.git\ncd Smart_lab_management_system\\backend")

    add_body_paragraph(doc, "Step 2: Install Backend Dependencies via uv", bold_prefix=None)
    add_body_paragraph(
        doc,
        "Running 'uv sync' automatically creates a local .venv virtual environment and installs all dependencies specified in pyproject.toml "
        "(FastAPI 0.115+, Uvicorn 0.34+, SQLAlchemy 2.0+, Alembic, Pydantic v2, and PyJWT):"
    )
    add_code_block(doc, "uv sync")

    add_body_paragraph(doc, "Step 3: Initialize Database Schema & Alembic Migrations", bold_prefix=None)
    add_body_paragraph(
        doc,
        "SLMS uses an embedded SQLite database configured with Write-Ahead Logging (WAL mode) and a 30-second busy timeout. This allows "
        "simultaneous high-frequency writes from 100+ workstations while the dashboard reads data without lock contention. Run migrations via:"
    )
    add_code_block(doc, "uv run alembic upgrade head")

    add_body_paragraph(doc, "Step 4: Launch Host Backend Server", bold_prefix=None)
    add_code_block(doc, "uv run uvicorn app.main:app --host 0.0.0.0 --port 18080 --reload")
    add_body_paragraph(
        doc,
        "Once started, the backend exposes interactive Swagger API documentation at http://localhost:18080/docs and OpenAPI specifications "
        "at http://localhost:18080/openapi.json."
    )

    add_body_paragraph(doc, "Step 5: Preconfigure Windows Firewall for Port 18080", bold_prefix=None)
    add_body_paragraph(
        doc,
        "To allow client workstations across the laboratory LAN to communicate with the host server, an inbound firewall rule must be added:"
    )
    add_code_block(doc, 'netsh advfirewall firewall add rule name="SLMS Host Service (18080)" dir=in action=allow protocol=TCP localport=18080 profile=private')

    # =========================================================================
    # 6.4 Frontend Dashboard and Tauri Native Desktop Shell Build
    # =========================================================================
    add_styled_heading(doc, "6.4 Frontend Dashboard & Tauri Native Desktop Shell Build", level=2)
    add_body_paragraph(
        doc,
        "The administration dashboard is constructed using React 19 for declarative UI rendering and Tauri v2 for native desktop shell "
        "capabilities (system tray minimization, close-to-tray handling, and native toast notifications)."
    )

    add_body_paragraph(doc, "Step 1: Install Frontend Dependencies", bold_prefix=None)
    add_code_block(doc, "cd ..\\frontend\nnpm install")

    add_body_paragraph(doc, "Step 2: Run in Development Mode", bold_prefix=None)
    add_body_paragraph(
        doc,
        "Developers can test the UI in a standard web browser preview or launch the complete native desktop shell with system tray integration:"
    )
    add_code_block(doc, "# 1. Run browser dev server (Vite):\nnpm run dev\n\n# 2. Run native desktop application (Tauri + Vite):\nnpx tauri dev")

    add_body_paragraph(doc, "Step 3: Compile Optimized Standalone Executable", bold_prefix=None)
    add_body_paragraph(
        doc,
        "Compiling the production desktop app generates an optimized, standalone binary packaged with Microsoft Edge WebView2 bindings:"
    )
    add_code_block(doc, "npx tauri build --no-bundle")
    add_body_paragraph(
        doc,
        "The compiled native desktop binary is output to: frontend\\src-tauri\\target\\release\\app.exe (~15 MB binary size)."
    )

    # =========================================================================
    # 6.5 Client Agent Enrollment and Windows Service Installation
    # =========================================================================
    add_styled_heading(doc, "6.5 Client Agent Enrollment and Windows Service Installation", level=2)
    add_body_paragraph(
        doc,
        "The client agent runs as a dedicated 64-bit Windows Service (SLMSService) operating under 'NT SERVICE\\SLMSService' in Session 0. "
        "This architecture guarantees that monitoring continues uninterrupted regardless of whether a student logs in or out."
    )

    add_body_paragraph(doc, "Step 1: Navigate to Client Agent and Sync Dependencies", bold_prefix=None)
    add_code_block(doc, "cd ..\\client_agent\nuv sync")

    add_body_paragraph(doc, "Step 2: Enroll Workstation with Host Server", bold_prefix=None)
    add_body_paragraph(
        doc,
        "During enrollment, the client contacts the Host to establish a machine identity. The intelligent URL normalizer automatically "
        "resolves IP inputs to port 18080 (e.g., entering 192.168.1.100 expands to http://192.168.1.100:18080). Stored credentials are "
        "encrypted using the Windows Data Protection API (DPAPI) machine vault (%ProgramData%\\SLMS\\config\\service_credentials.enc):"
    )
    add_code_block(doc, "uv run python main.py enroll --url 192.168.1.100 --key <ENROLLMENT_SECRET_KEY> --force")

    add_body_paragraph(doc, "Step 3: Register and Start Background Windows Service", bold_prefix=None)
    add_body_paragraph(
        doc,
        "Execute the service registration and permission hardening commands from an elevated administrative prompt:"
    )
    add_code_block(doc, "# 1. Register SLMSService in Windows Service Control Manager (SCM)\nuv run python main.py install\n\n# 2. Grant mandatory folder permissions on %ProgramData%\\SLMS\nuv run python main.py configure-acl\n\n# 3. Verify encrypted credentials can be decrypted by service account\nuv run python main.py verify-credentials\n\n# 4. Start the background Windows Service\nuv run python main.py start")

    add_body_paragraph(doc, "Step 4: Verify Service Execution Status", bold_prefix=None)
    add_code_block(doc, "sc query SLMSService\n# Expected Status: STATE: 4 RUNNING")

    # =========================================================================
    # 6.6 Inno Setup Automated Packaging (.exe Installers)
    # =========================================================================
    add_styled_heading(doc, "6.6 Inno Setup Automated Packaging (.exe Installers)", level=2)
    add_body_paragraph(
        doc,
        "For seamless institutional rollout across 50+ laboratory computers, SLMS utilizes Inno Setup 6 (ISCC.exe) to produce turnkey, "
        "single-file graphical and silent installers."
    )

    add_styled_heading(doc, "6.6.1 Host Installer Compilation", level=3)
    add_body_paragraph(
        doc,
        "The Host Installer packages the FastAPI service, Uvicorn server, SQLite WAL engine, Inno Setup wizard, and the Tauri desktop dashboard:"
    )
    add_code_block(doc, '"C:\\Program Files (x86)\\Inno Setup 6\\ISCC.exe" installer\\SLMS_Host_Setup.iss\n# Output Binary: installer\\output\\SLMS_Host_Setup.exe')

    add_styled_heading(doc, "6.6.2 Client Agent Installer Compilation", level=3)
    add_body_paragraph(
        doc,
        "The Client Installer packages the compiled PyInstaller agent binary (SLMS_Client_Agent.exe), the user desktop notification companion "
        "(SLMS_Notifier.exe), DPAPI security routines, and the local SQLite outbox buffer:"
    )
    add_code_block(doc, '"C:\\Program Files (x86)\\Inno Setup 6\\ISCC.exe" installer\\SLMS_Client_Agent_Setup.iss\n# Output Binary: installer\\output\\SLMS_Client_Agent_Setup.exe')

    add_styled_heading(doc, "6.6.3 Unattended Mass Deployment Across Lab Workstations", level=3)
    add_body_paragraph(
        doc,
        "In academic environments containing dozens of computers, manually clicking through installation wizards on every PC is impractical. "
        "SLMS provides two automated unattended deployment methods:"
    )

    add_body_paragraph(doc, "Method 1: Silent Inno Setup Installer (PowerShell Remote / PDQ Deploy)", bold_prefix=None)
    add_body_paragraph(
        doc,
        "Run from an elevated PowerShell prompt or pushed remotely across the subnet via network share:"
    )
    add_code_block(doc, '# Silent installation via network share / administrative script:\n$InstallerPath = "\\\\192.168.1.100\\SharedFolder\\SLMS_Client_Agent_Setup.exe"\nStart-Process -FilePath $InstallerPath -ArgumentList "/VERYSILENT /SUPPRESSMSGBOXES /NORESTART /SERVERURL=http://192.168.1.100:18080 /KEY=<ENROLLMENT_KEY>" -Wait')

    add_body_paragraph(doc, "Method 2: Headless Command-Line Enrollment via Binary (SLMS_Client_Agent.exe)", bold_prefix=None)
    add_body_paragraph(
        doc,
        "If deploying the compiled client executable directly without the Inno Setup wizard:"
    )
    add_code_block(doc, ':: 1. Enroll workstation with the Host server (DPAPI machine encryption)\nSLMS_Client_Agent.exe enroll --url 192.168.1.100 --key "<ENROLLMENT_KEY>" --force\n\n:: 2. Register SLMSService in Windows Service Control Manager\nSLMS_Client_Agent.exe install\n\n:: 3. Configure folder ACL permissions and verify credentials\nSLMS_Client_Agent.exe configure-acl\nSLMS_Client_Agent.exe verify-credentials\n\n:: 4. Start the background Windows Service\nSLMS_Client_Agent.exe start')

    add_body_paragraph(
        doc,
        "Both deployment methods register the background Windows Service, initialize the crash-resilient local SQLite outbox in "
        "%ProgramData%\\SLMS\\data, and register the desktop notification companion (SLMS_Notifier.exe) to start automatically in "
        "Session 1 upon student logon."
    )

    # Save document
    doc.save(str(output_path))
    print(f"[SUCCESS] Complete Chapter 6 Word document saved to: {output_path}")

if __name__ == "__main__":
    base_dir = Path(__file__).parent.parent
    docx_file = base_dir / "SLMS_Chapter_6_Installation_and_Procedure.docx"
    build_chapter_6_docx(docx_file)
