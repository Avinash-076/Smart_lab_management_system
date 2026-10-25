"""
Script to generate the complete, professionally formatted Word Document (.docx)
for CHAPTER 12: CONCLUSION AND FUTURE SCOPE for Smart Lab Management System (SLMS).
Strictly reflects the verified features, architectural achievements, and technical roadmap.
"""

from pathlib import Path
import docx
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml import parse_xml
from docx.oxml.ns import nsdecls

def set_cell_background(cell, fill_hex):
    tc_pr = cell._tc.get_or_add_tcPr()
    shd = parse_xml(f'<w:shd {nsdecls("w")} w:fill="{fill_hex}"/>')
    tc_pr.append(shd)

def set_cell_margins(cell, top=100, bottom=100, left=150, right=150):
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
        run.font.color.rgb = RGBColor(0x00, 0x33, 0x66)
    elif level == 2:
        h.paragraph_format.space_before = Pt(14)
        h.paragraph_format.space_after = Pt(6)
        run.font.name = "Calibri"
        run.font.size = Pt(14)
        run.font.bold = True
        run.font.color.rgb = RGBColor(0x1F, 0x4E, 0x79)
    elif level == 3:
        h.paragraph_format.space_before = Pt(10)
        h.paragraph_format.space_after = Pt(4)
        run.font.name = "Calibri"
        run.font.size = Pt(11.5)
        run.font.bold = True
        run.font.color.rgb = RGBColor(0x2E, 0x40, 0x53)
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

def build_chapter_12_docx(output_path: Path):
    doc = docx.Document()

    # Standard Academic Margins (1.25-inch left margin for binding, 1-inch top/bottom/right)
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
    r_chap_num = p_chap.add_run("CHAPTER 12\n")
    r_chap_num.font.name = "Calibri"
    r_chap_num.font.size = Pt(14)
    r_chap_num.font.bold = True
    r_chap_num.font.color.rgb = RGBColor(0x00, 0x33, 0x66)

    r_chap_title = p_chap.add_run("CONCLUSION AND FUTURE SCOPE")
    r_chap_title.font.name = "Calibri"
    r_chap_title.font.size = Pt(20)
    r_chap_title.font.bold = True
    r_chap_title.font.color.rgb = RGBColor(0x00, 0x33, 0x66)

    p_div = doc.add_paragraph()
    p_div.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_div.paragraph_format.space_after = Pt(12)
    r_div = p_div.add_run("―" * 45)
    r_div.font.color.rgb = RGBColor(0x9C, 0xA3, 0xAF)

    # =========================================================================
    # 12.1 Conclusion
    # =========================================================================
    add_styled_heading(doc, "12.1 Conclusion", level=2)
    add_body_paragraph(
        doc,
        "The Smart Lab Management System (SLMS) has been successfully designed, engineered, and validated as an enterprise-grade, "
        "lightweight laboratory management and remote administration platform. Specifically tailored to overcome the operational and "
        "pedagogical bottlenecks of academic computer laboratories, the platform replaces manual hardware supervision, paper-based maintenance "
        "logbooks, and noisy classroom instructions with an automated, synchronized, and centralized control architecture."
    )
    add_body_paragraph(
        doc,
        "The project has realized several critical technical and operational milestones that directly address the constraints of real-world "
        "institutional computing environments:"
    )

    add_bullet_item(
        doc,
        "Session 0 vs Session 1 Architectural Resolution",
        "By implementing a dual-process architecture comprising an un-elevated Windows background service (SLMS_AgentService.exe) in Session 0 "
        "and an interactive user notification agent (SLMS_Notifier.exe) in Session 1+, the system circumvents modern Windows Session 0 Isolation. "
        "This design enables non-intrusive system-level telemetry and power state control while ensuring that broadcast notifications and screen locking "
        "are rendered reliably directly within the active student desktop context."
    )
    add_bullet_item(
        doc,
        "Zero Socket Conflict Guarantee on Port 18080",
        "By anchoring all host communication and WebSocket telemetry to dedicated TCP port 18080, the system prevents socket collision errors "
        "(WinError 10013) that routinely disrupt educational institutions when student programming coursework utilizes standard development "
        "ports (such as 3000, 5000, or 8000)."
    )
    add_bullet_item(
        doc,
        "Lossless Offline Telemetry Buffering",
        "The implementation of an embedded SQLite outbox queue utilizing Write-Ahead Logging (WAL) and exponential backoff retry workers "
        "guarantees that intermittent local area network disruptions, switch reboots, or temporary server restarts do not cause loss of hardware "
        "or software metrics."
    )
    add_bullet_item(
        doc,
        "High Performance & Minimal Footprint",
        "Leveraging Tauri v2 with a native Rust system wrapper alongside an asynchronous FastAPI backend and React 19 frontend delivers sub-second "
        "command dispatch and real-time dashboard updates while maintaining an exceptionally modest client memory footprint (<15 MB RAM), "
        "ensuring zero degradation of workstation responsiveness during intense student computing tasks."
    )
    add_bullet_item(
        doc,
        "Cryptographic Rigor & Administrative Accountability",
        "The integration of Windows Data Protection API (DPAPI) with machine-level encryption (CRYPTPROTECT_LOCAL_MACHINE) protects machine-agent "
        "secrets against extraction, while comprehensive audit logging preserves an immutable historical trail of all administrative remote actions "
        "for institutional accreditation and governance."
    )

    # =========================================================================
    # 12.2 Future Scope
    # =========================================================================
    add_styled_heading(doc, "12.2 Future Scope", level=2)
    add_body_paragraph(
        doc,
        "While the current release of SLMS provides a complete, robust, and deployable solution for Windows-based institutional laboratories, "
        "the architecture has been intentionally designed to serve as a modular foundation for progressive future enhancements:"
    )

    add_bullet_item(
        doc,
        "Cross-Platform Client Agent for Linux Labs",
        "Educational institutions frequently maintain dual-boot or Linux-only laboratories for operating systems, cybersecurity, and cloud computing courses. "
        "Future development will extend the Python client agent into a native Linux systemd daemon, interacting with systemd-logind and DBus to provide "
        "identical telemetry probing, remote power controls, and broadcast notifications under popular academic distributions such as Ubuntu and Debian."
    )
    add_bullet_item(
        doc,
        "Wake-on-LAN (WoL) Remote Hardware Awakening",
        "Incorporating Wake-on-LAN magic packet broadcasting across local subnets will permit administrators to power on cold (powered-off) laboratory "
        "workstations remotely prior to morning laboratory sessions, eliminating manual boot sequences and streamlining automated overnight maintenance."
    )
    add_bullet_item(
        doc,
        "AI-Driven Predictive Maintenance & Anomaly Detection",
        "Integrating lightweight machine learning models into the telemetry ingestion pipeline will enable the platform to perform predictive failure "
        "analysis. By evaluating historical trends in CPU temperature, fan speeds, RAM saturation spikes, and storage degradation patterns, the system will "
        "automatically alert technicians to impending hardware component failures before physical breakdown occurs."
    )
    add_bullet_item(
        doc,
        "Dynamic Server Auto-Discovery via mDNS/ZeroConf",
        "To streamline deployment across very large university campuses with dynamic IP configurations, future releases will incorporate multicast DNS (mDNS) "
        "or UDP beacon discovery. This will allow newly installed client agents to automatically detect active SLMS backend instances without requiring "
        "manual entry of server IP addresses during initial enrollment."
    )
    add_bullet_item(
        doc,
        "Exam Kiosk Mode & Secure Assessment Lockdown",
        "Expanding the screen locking mechanism into a full examination kiosk environment will allow faculty to temporarily disable task switching "
        "(Alt+Tab, Windows Key shortcuts), restrict browser navigation to authorized assessment portals, and enforce a tamper-resistant environment "
        "for university practical and competitive programming examinations."
    )

    # Technical Milestones and Roadmap Comparison Table
    add_styled_heading(doc, "Summary of Achievements and Future Roadmap", level=3)
    table = doc.add_table(rows=1, cols=3)
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = False

    hdr_cells = table.rows[0].cells
    hdr_cells[0].width = Inches(1.8)
    hdr_cells[1].width = Inches(2.4)
    hdr_cells[2].width = Inches(2.3)

    hdr_cells[0].text = "Dimension"
    hdr_cells[1].text = "Current SLMS Achievement (v1.0)"
    hdr_cells[2].text = "Targeted Future Scope Enhancement"

    for cell in hdr_cells:
        set_cell_background(cell, "1F4E79")
        set_cell_margins(cell, top=120, bottom=120, left=140, right=140)
        p = cell.paragraphs[0]
        run = p.runs[0]
        run.font.name = "Calibri"
        run.font.size = Pt(10)
        run.font.bold = True
        run.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)

    roadmap_data = [
        (
            "Operating System",
            "Windows 10/11 Service (Session 0 + 1 Split)",
            "Cross-platform Linux daemon (Ubuntu/Debian via systemd & DBus)"
        ),
        (
            "Power Orchestration",
            "Synchronized Remote Shutdown & Restart via Win32",
            "Subnet Wake-on-LAN (WoL) magic packet remote cold boot"
        ),
        (
            "Telemetry & Health",
            "Real-time CPU/RAM/Disk metrics & process list inspection",
            "Predictive AI anomaly detection for impending hardware breakdown"
        ),
        (
            "Agent Enrollment",
            "Manual IP entry with automatic Port 18080 normalization",
            "Dynamic ZeroConf/mDNS automated local server discovery"
        ),
        (
            "Classroom Control",
            "Fullscreen screen locking & broadcast notifications",
            "Secure examination kiosk lockdown mode (disabling Alt+Tab/WinKey)"
        )
    ]

    for item in roadmap_data:
        row_cells = table.add_row().cells
        row_cells[0].width = Inches(1.8)
        row_cells[1].width = Inches(2.4)
        row_cells[2].width = Inches(2.3)

        for idx, text in enumerate(item):
            cell = row_cells[idx]
            set_cell_background(cell, "F9FAFB" if len(table.rows) % 2 == 0 else "FFFFFF")
            set_cell_margins(cell, top=100, bottom=100, left=120, right=120)
            p = cell.paragraphs[0]
            p.paragraph_format.line_spacing = 1.15
            p.paragraph_format.space_after = Pt(2)
            run = p.add_run(text)
            run.font.name = "Calibri"
            run.font.size = Pt(9.5)
            run.font.color.rgb = RGBColor(0x2B, 0x2B, 0x2B)
            if idx == 0:
                run.font.bold = True

    doc.save(str(output_path))
    print(f"[SUCCESS] Complete Chapter 12 Word document saved to: {output_path}")

if __name__ == "__main__":
    base_dir = Path(__file__).parent.parent
    docx_file = base_dir / "SLMS_Chapter_12_Conclusion_and_Future_Scope.docx"
    build_chapter_12_docx(docx_file)
