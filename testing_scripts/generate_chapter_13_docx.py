"""
Script to generate the complete, professionally formatted Word Document (.docx)
for CHAPTER 13: REFERENCES for Smart Lab Management System (SLMS).
Strictly covers OS internals, framework RFCs, cryptography, and academic citations.
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

def add_reference_entry(doc, ref_id, authors, year, title, publication, url_or_desc=None):
    p = doc.add_paragraph()
    p.paragraph_format.left_indent = Inches(0.4)
    p.paragraph_format.first_line_indent = Inches(-0.4)
    p.paragraph_format.line_spacing = 1.15
    p.paragraph_format.space_after = Pt(6)
    
    # [Ref ID]
    r_id = p.add_run(f"[{ref_id}] ")
    r_id.font.name = "Calibri"
    r_id.font.size = Pt(10.5)
    r_id.font.bold = True
    r_id.font.color.rgb = RGBColor(0x00, 0x33, 0x66)
    
    # Authors
    r_auth = p.add_run(f"{authors} ({year}). ")
    r_auth.font.name = "Calibri"
    r_auth.font.size = Pt(10.5)
    r_auth.font.color.rgb = RGBColor(0x1F, 0x29, 0x37)
    
    # Title (Italicized)
    r_title = p.add_run(f'"{title}". ')
    r_title.font.name = "Calibri"
    r_title.font.size = Pt(10.5)
    r_title.font.italic = True
    r_title.font.color.rgb = RGBColor(0x11, 0x18, 0x27)
    
    # Publication / Source
    r_pub = p.add_run(f"{publication}. ")
    r_pub.font.name = "Calibri"
    r_pub.font.size = Pt(10.5)
    r_pub.font.color.rgb = RGBColor(0x37, 0x41, 0x51)
    
    if url_or_desc:
        r_url = p.add_run(f"Available: {url_or_desc}")
        r_url.font.name = "Calibri"
        r_url.font.size = Pt(9.5)
        r_url.font.color.rgb = RGBColor(0x4B, 0x55, 0x63)
    return p

def build_chapter_13_docx(output_path: Path):
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
    r_chap_num = p_chap.add_run("CHAPTER 13\n")
    r_chap_num.font.name = "Calibri"
    r_chap_num.font.size = Pt(14)
    r_chap_num.font.bold = True
    r_chap_num.font.color.rgb = RGBColor(0x00, 0x33, 0x66)

    r_chap_title = p_chap.add_run("REFERENCES")
    r_chap_title.font.name = "Calibri"
    r_chap_title.font.size = Pt(20)
    r_chap_title.font.bold = True
    r_chap_title.font.color.rgb = RGBColor(0x00, 0x33, 0x66)

    p_div = doc.add_paragraph()
    p_div.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_div.paragraph_format.space_after = Pt(12)
    r_div = p_div.add_run("―" * 45)
    r_div.font.color.rgb = RGBColor(0x9C, 0xA3, 0xAF)

    # Introduction
    add_body_paragraph(
        doc,
        "This chapter lists the authoritative academic publications, operating system internal technical specifications, "
        "Internet Engineering Task Force (IETF) RFC standards, and official software documentation referenced throughout "
        "the architectural design, implementation, and security hardening of the Smart Lab Management System (SLMS)."
    )

    # =========================================================================
    # 13.1 Operating System Internals & Windows Architecture References
    # =========================================================================
    add_styled_heading(doc, "13.1 Operating System Internals & Windows Architecture", level=2)
    
    add_reference_entry(
        doc,
        ref_id="1",
        authors="Russinovich, M., Solomon, D. A., & Ionescu, A.",
        year="2017",
        title="Windows Internals, Part 1: System architecture, processes, threads, memory management, and more",
        publication="Microsoft Press, 7th Edition",
        url_or_desc="ISBN: 978-0-7356-8418-8"
    )
    add_reference_entry(
        doc,
        ref_id="2",
        authors="Microsoft Corporation",
        year="2023",
        title="Impact of Session 0 Isolation on Services and Drivers in Windows",
        publication="Microsoft Learn Developer Documentation",
        url_or_desc="https://learn.microsoft.com/en-us/windows/win32/services/services-and-redirected-drives-and-other-objects"
    )
    add_reference_entry(
        doc,
        ref_id="3",
        authors="Microsoft Corporation",
        year="2024",
        title="CreateProcessAsUserW function and Token Duplication Mechanics",
        publication="Microsoft Win32 and COM Development Documentation",
        url_or_desc="https://learn.microsoft.com/en-us/windows/win32/api/processthreadsapi/nf-processthreadsapi-createprocessasuserw"
    )
    add_reference_entry(
        doc,
        ref_id="4",
        authors="Microsoft Corporation",
        year="2024",
        title="Windows Data Protection API (DPAPI) and CryptProtectData Function",
        publication="Microsoft Windows Security SDK",
        url_or_desc="https://learn.microsoft.com/en-us/windows/win32/api/dpapi/nf-dpapi-cryptprotectdata"
    )
    add_reference_entry(
        doc,
        ref_id="5",
        authors="Jordan Russell & Martijn Laan",
        year="2024",
        title="Inno Setup 6 Documentation: Windows Installer Creation and Privileged Service Registration",
        publication="JRSoftware Technical Reference",
        url_or_desc="https://jrsoftware.org/ishelp/"
    )

    # =========================================================================
    # 13.2 Network Protocols, Web Standards & Security RFCs
    # =========================================================================
    add_styled_heading(doc, "13.2 Network Protocols, Web Standards & Security RFCs", level=2)

    add_reference_entry(
        doc,
        ref_id="6",
        authors="Fette, I., & Melnikov, A.",
        year="2011",
        title="The WebSocket Protocol",
        publication="Internet Engineering Task Force (IETF) RFC 6455",
        url_or_desc="https://datatracker.ietf.org/doc/html/rfc6455"
    )
    add_reference_entry(
        doc,
        ref_id="7",
        authors="Fielding, R., & Reschke, J.",
        year="2014",
        title="Hypertext Transfer Protocol (HTTP/1.1): Message Syntax and Routing",
        publication="Internet Engineering Task Force (IETF) RFC 7230",
        url_or_desc="https://datatracker.ietf.org/doc/html/rfc7230"
    )
    add_reference_entry(
        doc,
        ref_id="8",
        authors="Rescorla, E.",
        year="2018",
        title="The Transport Layer Security (TLS) Protocol Version 1.3",
        publication="Internet Engineering Task Force (IETF) RFC 8446",
        url_or_desc="https://datatracker.ietf.org/doc/html/rfc8446"
    )
    add_reference_entry(
        doc,
        ref_id="9",
        authors="Hipp, D. R., Kennedy, D., & Mistachkin, J.",
        year="2023",
        title="Write-Ahead Logging (WAL) in SQLite Database Engine",
        publication="SQLite Architecture Specifications",
        url_or_desc="https://www.sqlite.org/wal.html"
    )

    # =========================================================================
    # 13.3 Software Frameworks, Runtimes & Libraries
    # =========================================================================
    add_styled_heading(doc, "13.3 Software Frameworks, Runtimes & Libraries", level=2)

    add_reference_entry(
        doc,
        ref_id="10",
        authors="Ramírez, S. (tiangolo)",
        year="2024",
        title="FastAPI: High performance, easy to learn, fast to code, ready for production",
        publication="FastAPI Technical Documentation",
        url_or_desc="https://fastapi.tiangolo.com/"
    )
    add_reference_entry(
        doc,
        ref_id="11",
        authors="Colvin, S., et al.",
        year="2024",
        title="Pydantic V2: Data validation using Python type hints",
        publication="Pydantic Documentation",
        url_or_desc="https://docs.pydantic.dev/"
    )
    add_reference_entry(
        doc,
        ref_id="12",
        authors="Tauri Programme & Contributors",
        year="2024",
        title="Tauri v2 Documentation: Build smaller, faster, and more secure desktop applications with a web frontend",
        publication="Tauri Foundation",
        url_or_desc="https://v2.tauri.app/"
    )
    add_reference_entry(
        doc,
        ref_id="13",
        authors="Meta Platforms, Inc.",
        year="2024",
        title="React 19: A JavaScript library for building user interfaces",
        publication="React Documentation",
        url_or_desc="https://react.dev/"
    )
    add_reference_entry(
        doc,
        ref_id="14",
        authors="Rodola, G.",
        year="2024",
        title="psutil: Cross-platform process and system monitoring in Python",
        publication="Python Package Index Documentation",
        url_or_desc="https://psutil.readthedocs.io/"
    )
    add_reference_entry(
        doc,
        ref_id="15",
        authors="You, E., & Vite Contributors",
        year="2024",
        title="Vite: Next Generation Frontend Tooling",
        publication="Vite Official Guide",
        url_or_desc="https://vitejs.dev/"
    )

    # Summary Table of Core References
    add_styled_heading(doc, "Summary of Framework & Specification References", level=3)
    table = doc.add_table(rows=1, cols=3)
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = False

    hdr_cells = table.rows[0].cells
    hdr_cells[0].width = Inches(1.8)
    hdr_cells[1].width = Inches(2.3)
    hdr_cells[2].width = Inches(2.4)

    hdr_cells[0].text = "Component / Layer"
    hdr_cells[1].text = "Primary Specification / Standard"
    hdr_cells[2].text = "Implementation Usage in SLMS"

    for cell in hdr_cells:
        set_cell_background(cell, "1F4E79")
        set_cell_margins(cell, top=120, bottom=120, left=140, right=140)
        p = cell.paragraphs[0]
        run = p.runs[0]
        run.font.name = "Calibri"
        run.font.size = Pt(10)
        run.font.bold = True
        run.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)

    summary_data = [
        (
            "Service Isolation",
            "MSDN Session 0 Guidelines & Token Duplication",
            "SLMS_AgentService.exe (Session 0) & SLMS_Notifier.exe (Session 1+)"
        ),
        (
            "Telemetry Transport",
            "IETF RFC 6455 (WebSocket Protocol)",
            "Bidirectional real-time heartbeat and batch command dispatching"
        ),
        (
            "Offline Outbox",
            "SQLite Write-Ahead Logging (WAL) Mode",
            "Zero-loss transactional buffering during network disruptions"
        ),
        (
            "Machine Security",
            "Microsoft DPAPI (CryptProtectData)",
            "Machine-level token cryptography with CRYPTPROTECT_LOCAL_MACHINE"
        ),
        (
            "Host Web Server",
            "FastAPI / Starlette ASGI Framework",
            "Async RESTful routing and WebSocket manager on port 18080"
        ),
        (
            "Client Dashboard",
            "Tauri v2 Native Rust Shell + React 19",
            "Lightweight (<15 MB) desktop shell with system close-to-tray"
        )
    ]

    for item in summary_data:
        row_cells = table.add_row().cells
        row_cells[0].width = Inches(1.8)
        row_cells[1].width = Inches(2.3)
        row_cells[2].width = Inches(2.4)

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
    print(f"[SUCCESS] Complete Chapter 13 Word document saved to: {output_path}")

if __name__ == "__main__":
    base_dir = Path(__file__).parent.parent
    docx_file = base_dir / "SLMS_Chapter_13_References.docx"
    build_chapter_13_docx(docx_file)
