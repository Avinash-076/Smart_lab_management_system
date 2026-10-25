"""
Script to generate the complete, professionally formatted Word Document (.docx)
specifically for SECTION 10.9: APPLICATION OUTPUT SCREENS AND OPERATIONAL PROOFS
for the Smart Lab Management System (SLMS).

Includes dedicated placeholder boxes and descriptive writeups for all GUI dashboard screens,
remote control execution, terminal enrollment proofs, and Windows background service verification.
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

def set_cell_margins(cell, top=140, bottom=140, left=180, right=180):
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

def add_image_placeholder(doc, figure_num, figure_title, description, visual_guidance):
    table = doc.add_table(rows=1, cols=1)
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = False
    
    cell = table.rows[0].cells[0]
    cell.width = Inches(6.25)
    set_cell_background(cell, "F3F4F6")
    set_cell_margins(cell, top=260, bottom=260, left=240, right=240)
    
    p = cell.paragraphs[0]
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.line_spacing = 1.25
    p.paragraph_format.space_before = Pt(6)
    p.paragraph_format.space_after = Pt(6)
    
    r1 = p.add_run(f"📷 [ PASTE SCREENSHOT HERE FOR {figure_num} ]\n")
    r1.font.name = "Calibri"
    r1.font.size = Pt(11.5)
    r1.font.bold = True
    r1.font.color.rgb = RGBColor(0x1F, 0x4E, 0x79)
    
    r2 = p.add_run(f"{figure_title}\n")
    r2.font.name = "Calibri"
    r2.font.size = Pt(10)
    r2.font.bold = True
    r2.font.color.rgb = RGBColor(0x37, 0x41, 0x51)
    
    r3 = p.add_run(f"Target View: {description}")
    r3.font.name = "Calibri"
    r3.font.size = Pt(9)
    r3.font.italic = True
    r3.font.color.rgb = RGBColor(0x6B, 0x72, 0x80)

    # Caption paragraph directly beneath image frame
    p_cap = doc.add_paragraph()
    p_cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_cap.paragraph_format.space_before = Pt(4)
    p_cap.paragraph_format.space_after = Pt(4)
    
    r_cap_lbl = p_cap.add_run(f"{figure_num}: ")
    r_cap_lbl.font.name = "Calibri"
    r_cap_lbl.font.size = Pt(10)
    r_cap_lbl.font.bold = True
    r_cap_lbl.font.color.rgb = RGBColor(0x00, 0x33, 0x66)
    
    r_cap_txt = p_cap.add_run(figure_title)
    r_cap_txt.font.name = "Calibri"
    r_cap_txt.font.size = Pt(10)
    r_cap_txt.font.italic = True
    r_cap_txt.font.color.rgb = RGBColor(0x1F, 0x29, 0x37)

    # Contextual note explaining what this screenshot proves
    p_desc = doc.add_paragraph()
    p_desc.paragraph_format.line_spacing = 1.15
    p_desc.paragraph_format.space_before = Pt(2)
    p_desc.paragraph_format.space_after = Pt(12)
    r_guide_lbl = p_desc.add_run("Verification Evidence: ")
    r_guide_lbl.font.name = "Calibri"
    r_guide_lbl.font.size = Pt(9.5)
    r_guide_lbl.font.bold = True
    r_guide_lbl.font.color.rgb = RGBColor(0x37, 0x41, 0x51)
    
    r_guide_txt = p_desc.add_run(visual_guidance)
    r_guide_txt.font.name = "Calibri"
    r_guide_txt.font.size = Pt(9.5)
    r_guide_txt.font.color.rgb = RGBColor(0x4B, 0x55, 0x63)

def build_section_10_9_docx(output_path: Path):
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
    r_chap_num = p_chap.add_run("CHAPTER 10: SOURCE CODE AND IMPLEMENTATION\n")
    r_chap_num.font.name = "Calibri"
    r_chap_num.font.size = Pt(13)
    r_chap_num.font.bold = True
    r_chap_num.font.color.rgb = RGBColor(0x00, 0x33, 0x66)

    r_chap_title = p_chap.add_run("SECTION 10.9: APPLICATION OUTPUT SCREENS & OPERATIONAL PROOFS")
    r_chap_title.font.name = "Calibri"
    r_chap_title.font.size = Pt(17)
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
        "This section documents the visual output screens, graphical user interfaces, runtime terminal executions, "
        "and operational verification evidence of the Smart Lab Management System (SLMS). Each figure demonstrates "
        "a functioning component of the architecture, spanning client workstation background service execution, "
        "real-time fleet telemetry monitoring, software inventory compliance, global remote command dispatch, "
        "and active student session screen locking."
    )

    # =========================================================================
    # Part 1: Deployment & System Internals Proofs
    # =========================================================================
    add_styled_heading(doc, "Part 1: Packaging, Enrollment & System Service Verification", level=2)

    add_image_placeholder(
        doc,
        "Figure 10.9.1",
        "SLMS Host Inno Setup Wizard Installation Screen",
        "SLMS_Host_Setup.exe completing setup on the administrator's PC",
        "Validates the automated, zero-dependency installation package built with Inno Setup 6, verifying proper binary extraction, desktop icon creation, and service prerequisites."
    )

    add_image_placeholder(
        doc,
        "Figure 10.9.2",
        "Workstation Terminal Enrollment with Auto-Port 18080 Normalization",
        "Command prompt showing 'SLMS_Client_Agent.exe enroll' executing successfully",
        "Demonstrates automatic URL normalization (converting raw IP inputs like '192.168.1.100' to 'http://192.168.1.100:18080') and machine-bound credential encryption via Windows DPAPI (CryptProtectData)."
    )

    add_image_placeholder(
        doc,
        "Figure 10.9.3",
        "Windows Service Control Manager (SCM) Status Verification",
        "PowerShell terminal displaying 'sc.exe query SLMSService' with STATE: 4 RUNNING",
        "Provides architectural proof that the client agent operates continuously in Windows Session 0 as an un-elevated system service, independent of whether a student is logged into the workstation."
    )

    # =========================================================================
    # Part 2: Working Graphical User Interface (GUI) Screens
    # =========================================================================
    add_styled_heading(doc, "Part 2: Working Graphical User Interface (GUI) Outputs", level=2)

    add_image_placeholder(
        doc,
        "Figure 10.9.4",
        "SLMS Central Laboratory Overview Dashboard and Telemetry Gauges",
        "Main dashboard page (/dashboard) showing summary metric cards and CPU/RAM gauges",
        "Shows the real-time aggregated metrics across all active lab computers, including online/offline workstation counters, average fleet CPU load, and RAM saturation meters."
    )

    add_image_placeholder(
        doc,
        "Figure 10.9.5",
        "Live Workstation Matrix Grid displaying Real-Time Machine Status",
        "Computers view (/computers) rendering responsive workstation cards with color badges",
        "Demonstrates real-time visual status classification where workstations display emerald green (healthy), amber (warning: RAM > 80%), or crimson red (critical: RAM > 90% or offline)."
    )

    add_image_placeholder(
        doc,
        "Figure 10.9.6",
        "Global Remote Control Command Center with Multi-Action Cards",
        "Remote Control hub (/remote-control) showing the 4 action cards and workstation selector",
        "Illustrates the administrative command center supporting batch operations: 'Send Announcement Message', 'Lock Workstations', 'Restart Computers', and 'Shutdown Computers' with safety confirmation."
    )

    add_image_placeholder(
        doc,
        "Figure 10.9.7",
        "Workstation Inspection Drawer with Live Process Table and Hardware Specs",
        "Computer Details side-drawer (/computers/:id) showing active process list",
        "Confirms read-only process auditing where faculty can inspect running student tasks (PIDs, CPU %, resident memory) and hardware configuration without disrupting the student session."
    )

    add_image_placeholder(
        doc,
        "Figure 10.9.8",
        "Centralized Software Inventory and Installed Application Audit View",
        "Software Inventory page (/software) listing application catalog and installation counts",
        "Shows automated software compliance auditing, listing installed software harvested from 32-bit and 64-bit Windows Registry keys across all enrolled lab PCs."
    )

    add_image_placeholder(
        doc,
        "Figure 10.9.9",
        "Laboratory Issue Ticketing and Problem Report Triage Interface",
        "Issue Management page (/issues) showing ticket status, workstation IDs, and severity",
        "Validates the digital helpdesk system replacing paper logbooks, tracking reported hardware defects (mouse, display, network) across 'Open', 'In Progress', and 'Resolved' statuses."
    )

    add_image_placeholder(
        doc,
        "Figure 10.9.10",
        "Student Workstation Full-Screen Lock Overlay Screen",
        "Student monitor showing full-screen lock overlay rendered by SLMS_Notifier.exe",
        "Visual proof of the cross-session bridge where the Session 0 background service launches the Session 1 notifier using CreateProcessAsUserW to freeze student screens during lectures or exams."
    )

    add_image_placeholder(
        doc,
        "Figure 10.9.11",
        "Windows System Tray Integration and Native Desktop Notification Alert",
        "Taskbar tray icon with context menu and native Windows Action Center toast alert",
        "Validates Tauri v2 native desktop shell integration, showing close-to-tray lifecycle maintenance and native Windows Action Center toast alerts for memory saturation breaches."
    )

    doc.save(str(output_path))
    print(f"[SUCCESS] Complete Section 10.9 Word document saved to: {output_path}")

if __name__ == "__main__":
    base_dir = Path(__file__).parent.parent
    docx_file = base_dir / "SLMS_Section_10_9_Application_Output_Screens.docx"
    build_section_10_9_docx(docx_file)
