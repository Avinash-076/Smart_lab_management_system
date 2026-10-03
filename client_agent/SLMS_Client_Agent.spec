# -*- mode: python ; coding: utf-8 -*-
"""
Canonical PyInstaller Build Specification for SLMS Windows Client Agent.

Builds a self-contained, unified Windows executable capable of running in:
1. Interactive CLI mode (default execution)
2. Windows Service Control Manager (SCM) mode (Session 0 execution via 'run' or '--service')
3. Service Management CLI mode ('install', 'uninstall', 'start', 'stop', 'status', 'debug')
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

block_cipher = None

# Dynamically resolve client_agent base path and virtual environment site-packages
base_dir = Path(__file__).parent.resolve() if "__file__" in globals() else Path(SPECPATH).resolve()
venv_site = base_dir / ".venv" / "Lib" / "site-packages"

pathex_paths = [str(base_dir)]
if venv_site.exists():
    for p in [venv_site, venv_site / "win32", venv_site / "win32" / "lib", venv_site / "pythonwin"]:
        if p.exists():
            pathex_paths.append(str(p))
            if str(p) not in sys.path:
                sys.path.insert(0, str(p))

from PyInstaller.utils.hooks import collect_all, copy_metadata

cn_datas, cn_binaries, cn_hiddenimports = collect_all("charset_normalizer")

# Hidden imports required for Windows SCM, crypto, SQLite, and dynamically loaded modules
hidden_imports = list(set([
    # Core third-party runtime libraries
    "keyring",
    "keyring.backends",
    "keyring.backends.Windows",
    "psutil",
    "requests",
    "charset_normalizer",
    "charset_normalizer.api",
    "charset_normalizer.cd",
    "charset_normalizer.constant",
    "charset_normalizer.legacy",
    "charset_normalizer.md",
    "charset_normalizer.models",
    "charset_normalizer.utils",
    "charset_normalizer.version",
    "urllib3",
    "idna",
    "websocket",
    "certifi",
    "sqlite3",
    # Windows API and Service Framework (pywin32)
    "servicemanager",
    "win32service",
    "win32serviceutil",
    "win32event",
    "win32security",
    "win32timezone",
    "win32process",
    "win32api",
    "win32con",
    # SLMS Core subsystems
    "core.logger",
    "core.runtime",
    "core.security",
    "core.credentials",
    "core.single_instance",
    "core.outbox",
    "core.outbox.migration",
    "core.outbox.models",
    "core.outbox.policy",
    "core.outbox.storage",
    "core.outbox.worker",
    # SLMS Telemetry and collector modules
    "modules.hardware",
    "modules.issues",
    "modules.network",
    "modules.processes",
    "modules.software",
    "modules.system_info",
    "modules.usage",
    # SLMS Server communication
    "server.auth",
    "server.command_handler",
    "server.communication",
    "server.enroll",
    "server.sender",
    # SLMS Service integration
    "service.lifecycle",
    "service.service",
    # Interactive GUI enrollment
    "gui.enrollment_window",
] + cn_hiddenimports))

a = Analysis(
    ["main.py"],
    pathex=pathex_paths,
    binaries=cn_binaries,
    datas=cn_datas,
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "tests",
        "pytest",
        "_pytest",
        "coverage",
        "pytest_cov",
        "ruff",
    ],
    noarchive=False,
    optimize=0,
)

# Filter out mypyc compiled C-extensions for charset_normalizer that require missing internal hash modules on Python 3.13
a.binaries = [b for b in a.binaries if not ("charset_normalizer" in b[0].lower() and b[0].lower().endswith(".pyd"))]

pyz = PYZ(
    a.pure,
    a.zipped_data,
    cipher=block_cipher,
)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="SLMS_Client_Agent",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
