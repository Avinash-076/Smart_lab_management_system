"""
Script to generate the complete, professionally formatted Word Document (.docx)
for CHAPTER 7: USER INTERFACE GUIDE for Smart Lab Management System (SLMS).
Includes dedicated screenshot placement frames and academic captions.
"""

import os
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

def add_image_placeholder(doc, figure_num, figure_title, description):
    """Add a framed placeholder box where the user can paste their screenshot."""
    tbl = doc.add_table(rows=1, cols=1)
    tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
    tbl.autofit = False
    
    cell = tbl.cell(0, 0)
    cell.width = Inches(6.5)
    set_cell_background(cell, "F9FAFB")
    set_cell_margins(cell, top=200, bottom=200, left=200, right=200)
    
    # Dashed/Single Border
    tc_pr = cell._tc.get_or_add_tcPr()
    borders = parse_xml(
        f'<w:tcBorders {nsdecls("w")}>'
        f'<w:top w:val="single" w:sz="6" w:space="0" w:color="9CA3AF"/>'
        f'<w:left w:val="single" w:sz="6" w:space="0" w:color="9CA3AF"/>'
        f'<w:bottom w:val="single" w:sz="6" w:space="0" w:color="9CA3AF"/>'
        f'<w:right w:val="single" w:sz="6" w:space="0" w:color="9CA3AF"/>'
        f'</w:tcBorders>'
    )
    tc_pr.append(borders)
    
    p = cell.paragraphs[0]
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(12)
    p.paragraph_format.space_after = Pt(12)
    
    r1 = p.add_run(f"📷 [ PASTE SCREENSHOT HERE FOR {figure_num} ]\n")
    r1.font.name = "Calibri"
    r1.font.size = Pt(10)
    r1.font.bold = True
    r1.font.color.rgb = RGBColor(0x4B, 0x55, 0x63)
    
    r2 = p.add_run(f"({description})")
    r2.font.name = "Calibri"
    r2.font.size = Pt(9.5)
    r2.font.italic = True
    r2.font.color.rgb = RGBColor(0x6B, 0x72, 0x80)

    # Caption paragraph directly below table
    p_cap = doc.add_paragraph()
    p_cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_cap.paragraph_format.space_before = Pt(4)
    p_cap.paragraph_format.space_after = Pt(12)
    
    r_cap_lbl = p_cap.add_run(f"{figure_num}: ")
    r_cap_lbl.font.name = "Calibri"
    r_cap_lbl.font.size = Pt(10)
    r_cap_lbl.font.bold = True
    r_cap_lbl.font.color.rgb = RGBColor(0x11, 0x18, 0x27)
    
    r_cap_txt = p_cap.add_run(figure_title)
    r_cap_txt.font.name = "Calibri"
    r_cap_txt.font.size = Pt(10)
    r_cap_txt.font.italic = True
    r_cap_txt.font.color.rgb = RGBColor(0x37, 0x41, 0x51)

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

def build_chapter_7_docx(output_path: Path):
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
    r_chap_num = p_chap.add_run("CHAPTER 7\n")
    r_chap_num.font.name = "Calibri"
    r_chap_num.font.size = Pt(14)
    r_chap_num.font.bold = True
    r_chap_num.font.color.rgb = RGBColor(0x00, 0x33, 0x66)

    r_chap_title = p_chap.add_run("USER INTERFACE GUIDE")
    r_chap_title.font.name = "Calibri"
    r_chap_title.font.size = Pt(20)
    r_chap_title.font.bold = True
    r_chap_title.font.color.rgb = RGBColor(0x00, 0x33, 0x66)

    p_div = doc.add_paragraph()
    p_div.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_div.paragraph_format.space_after = Pt(12)
    r_div = p_div.add_run("―" * 45)
    r_div.font.color.rgb = RGBColor(0x9C, 0xA3, 0xAF)

    # Intro Paragraph
    add_body_paragraph(
        doc,
        "This chapter provides a comprehensive guide to the graphical user interface (GUI) of the Smart Lab Management System (SLMS). "
        "The application is engineered using React 19 and packaged within the Tauri v2 desktop framework. It features an ergonomic, "
        "high-scannability interface tailored specifically for lab administrators and faculty instructors. Each section explains the functional "
        "layout, interactive controls, and visual indicators of a specific module, accompanied by corresponding screen illustrations."
    )

    # =========================================================================
    # 7.1 Lab Overview Dashboard & Telemetry Metrics
    # =========================================================================
    add_styled_heading(doc, "7.1 Lab Overview Dashboard & Telemetry Metrics", level=2)
    add_body_paragraph(
        doc,
        "The Lab Overview Dashboard serves as the primary landing page upon application startup. It aggregates high-level lab telemetry "
        "into real-time summary statistics cards, resource gauges, and an activity event feed, providing instantaneous situational awareness "
        "of the entire computer laboratory."
    )
    add_styled_heading(doc, "Key Dashboard Elements", level=3)
    add_bullet_item(doc, "Workstation Summary Cards", "Four prominent status counters displaying Total Enrolled Computers, Active Online Workstations, Offline Workstations, and Active Alert Count.")
    add_bullet_item(doc, "Lab-Wide Resource Utilization Gauges", "Dynamic radial and linear progress meters reflecting the real-time average CPU load percentage and average physical RAM utilization across all active laboratory machines.")
    add_bullet_item(doc, "Live Activity Feed", "A chronological log stream detailing recent network events, client enrollments, disconnections, and administrative command acknowledgments.")

    add_image_placeholder(
        doc,
        "Figure 7.1",
        "SLMS Central Laboratory Overview Dashboard and Telemetry Gauges",
        "Screenshot showing the main dashboard page with summary statistics cards, average CPU/RAM gauges, and recent activity log"
    )

    # =========================================================================
    # 7.2 Live Computer Matrix Grid & Workstation Status Cards
    # =========================================================================
    add_styled_heading(doc, "7.2 Live Computer Matrix Grid & Workstation Status Cards", level=2)
    add_body_paragraph(
        doc,
        "The Computer Matrix Grid renders all enrolled laboratory computers in a visual, responsive tile layout. Each workstation is "
        "represented by an individual card displaying real-time health metrics, network IP, and distinct color-coded status badges, as "
        "illustrated in Figure 7.2."
    )
    add_styled_heading(doc, "Workstation Status Indicators", level=3)
    add_bullet_item(doc, "Emerald Green (Online / Healthy)", "Indicates that the workstation is connected, streaming telemetry, and running within nominal CPU/RAM limits.")
    add_bullet_item(doc, "Amber Yellow (Warning)", "Indicates that the machine is experiencing resource strain (RAM utilization > 80% or CPU usage > 85%).")
    add_bullet_item(doc, "Crimson Red (Critical Alert)", "Indicates an urgent condition requiring immediate attention, such as memory exhaustion (RAM > 90%), severe CPU spiking, or sudden network disconnection.")
    add_bullet_item(doc, "Slate Grey (Offline)", "Indicates that the workstation is powered down or has gracefully shut down.")

    add_image_placeholder(
        doc,
        "Figure 7.2",
        "Live Workstation Matrix Grid displaying Real-Time Machine Status",
        "Screenshot showing the interactive grid of computer cards with green, yellow, and red status badges"
    )

    # =========================================================================
    # 7.3 Workstation Deep-Dive, Process Inspection & Remote Commands
    # =========================================================================
    add_styled_heading(doc, "7.3 Workstation Deep-Dive, Process Inspection & Remote Commands", level=2)
    add_body_paragraph(
        doc,
        "Selecting any computer card within the Matrix Grid opens the Workstation Inspection Drawer. This side-over panel provides a deep-dive "
        "view into the target workstation's internal state without disrupting the student's interactive session."
    )
    add_styled_heading(doc, "Interactive Drawer Capabilities", level=3)
    add_bullet_item(doc, "Detailed Hardware Specifications", "Displays host name, logged-in user, OS version, processor architecture, physical memory capacity, disk drive partitions (C: / D:), and network MAC address.")
    add_bullet_item(doc, "Live Process Inspector", "A searchable, real-time table enumerating all running tasks, including Process ID (PID), executable name, CPU share, and resident memory usage.")
    add_bullet_item(doc, "Terminate Process Action", "Allows instructors to select any unauthorized process (e.g., games, infinite loops) and terminate it instantly over WebSocket.")
    add_bullet_item(doc, "Remote Workstation Controls", "One-click action buttons enabling screen lock, screen unlock, remote system restart, and power-off.")

    add_image_placeholder(
        doc,
        "Figure 7.3",
        "Workstation Inspection Drawer with Live Process Table and Remote Actions",
        "Screenshot showing the side drawer with hardware specs, active process list, and 'Lock Workstation' / 'Terminate Process' buttons"
    )

    # =========================================================================
    # 7.4 Software Inventory & Installed Application Auditing
    # =========================================================================
    add_styled_heading(doc, "7.4 Software Inventory & Installed Application Auditing", level=2)
    add_body_paragraph(
        doc,
        "The Software Inventory interface provides centralized asset auditing across all laboratory machines. Client agents automatically "
        "extract installed applications from the 32-bit and 64-bit Windows Registry uninstall keys and sync them with the Host database."
    )
    add_styled_heading(doc, "Auditing & Compliance Features", level=3)
    add_bullet_item(doc, "Global Application Catalog", "A centralized table listing all installed software packages, publisher details, version numbers, and install dates.")
    add_bullet_item(doc, "Workstation Installation Counter", "Displays the exact count of computers containing each software title, allowing faculty to confirm prerequisite software availability ahead of examinations.")
    add_bullet_item(doc, "Quick Filter & Search", "Facilitates instant searching for development environments (e.g., Python, VS Code, Node.js, JDK, MySQL).")

    add_image_placeholder(
        doc,
        "Figure 7.4",
        "Centralized Software Inventory and Installed Application Audit View",
        "Screenshot showing the software inventory table with application names, versions, and workstation installation counts"
    )

    # =========================================================================
    # 7.5 Student Issue Reporting & Ticketing Interface
    # =========================================================================
    add_styled_heading(doc, "7.5 Student Issue Reporting & Ticketing Interface", level=2)
    add_body_paragraph(
        doc,
        "To streamline hardware and software support, SLMS integrates an institutional ticketing helpdesk. Students can submit problem "
        "reports directly from the desktop companion (SLMS_Notifier.exe), which immediately appear in the instructor's Issues interface."
    )
    add_styled_heading(doc, "Helpdesk & Triage Workflow", level=3)
    add_bullet_item(doc, "Structured Ticket Submission", "Captures workstation identifier, category (Hardware, Software, Network), severity, student remarks, and timestamp.")
    add_bullet_item(doc, "Status Management", "Enables technicians to update ticket progression across 'Open', 'In Progress', and 'Resolved' states.")
    add_bullet_item(doc, "Resolution Audit History", "Maintains an institutional record of recurring hardware malfunctions for departmental replacement planning.")

    add_image_placeholder(
        doc,
        "Figure 7.5",
        "Laboratory Issue Ticketing and Problem Report Triage Interface",
        "Screenshot showing the issues table with open/resolved tickets, machine IDs, and severity tags"
    )

    # =========================================================================
    # 7.6 Windows System Tray Integration & Action Center Toast Alerts
    # =========================================================================
    add_styled_heading(doc, "7.6 Windows System Tray Integration & Action Center Toast Alerts", level=2)
    add_body_paragraph(
        doc,
        "Unlike standard browser-based or Electron applications, SLMS integrates natively with the Windows desktop through Tauri v2, "
        "ensuring that lab instructors remain aware of system anomalies even while grading papers or running lectures."
    )
    add_styled_heading(doc, "Native Desktop Capabilities", level=3)
    add_bullet_item(doc, "Close-to-Tray Window Lifecycle", "Closing the dashboard window hides the application into the Windows System Tray near the taskbar clock, keeping background WebSocket telemetry listeners active with an ultra-low memory footprint (~25 MB RAM).")
    add_bullet_item(doc, "System Tray Context Menu", "Right-clicking the tray icon reveals 'Open Dashboard' and 'Quit SLMS Host' options; left-clicking restores and focuses the window.")
    add_bullet_item(doc, "Native Windows Action Center Toasts", "When a critical threshold is breached (e.g., LAB-PC-08 RAM > 90%), a native Windows toast notification slides in at the bottom-right corner of the desktop accompanied by an audio alert. Clicking the toast restores the app directly to the target machine.")

    add_image_placeholder(
        doc,
        "Figure 7.6",
        "Windows System Tray Close-to-Tray Integration and Action Center Toast Alert",
        "Screenshot showing the taskbar system tray with the SLMS icon and a native Windows Action Center toast alert banner"
    )

    # =========================================================================
    # 7.7 Reports, Historical Telemetry Logs & Accessibility
    # =========================================================================
    add_styled_heading(doc, "7.7 Reports, Historical Telemetry Logs & Accessibility", level=2)
    add_body_paragraph(
        doc,
        "The Reports and Historical Logs module allows administrators to analyze long-term laboratory performance, export compliance "
        "documentation, and review operator audit trails."
    )
    add_styled_heading(doc, "Reporting Capabilities", level=3)
    add_bullet_item(doc, "Time-Series Telemetry Charts", "Interactive graphs rendering CPU load, RAM utilization, and network traffic over customizable 1-hour, 6-hour, and 24-hour windows.")
    add_bullet_item(doc, "Data Export in CSV / JSON", "Single-click data export generating standardized CSV and JSON reports for institutional auditing.")
    add_bullet_item(doc, "Administrative Audit Trail", "Maintains an immutable chronological record of every remote command dispatched (screen lock, reboot, process termination) with operator timestamp.")
    add_bullet_item(doc, "Visual Accessibility & Contrast", "Built with high-contrast color tokens and clean typographic hierarchy, ensuring effortless readability across diverse lighting and projector environments.")

    add_image_placeholder(
        doc,
        "Figure 7.7",
        "Historical Workstation Telemetry Logs and Data Export Interface",
        "Screenshot showing historical metric charts and data export buttons"
    )

    doc.save(str(output_path))
    print(f"[SUCCESS] Complete Chapter 7 Word document saved to: {output_path}")

if __name__ == "__main__":
    base_dir = Path(__file__).parent.parent
    docx_file = base_dir / "SLMS_Chapter_7_User_Interface_Guide.docx"
    build_chapter_7_docx(docx_file)
