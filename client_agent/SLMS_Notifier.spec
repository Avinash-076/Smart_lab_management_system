# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller Build Specification for SLMS Interactive User Notification Companion (SLMS_Notifier.exe).

Builds a lightweight, windowed (console=False) Windows executable that runs in
logged-in interactive user desktop sessions (Session 1..N).
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

block_cipher = None

base_dir = Path(__file__).parent.resolve() if "__file__" in globals() else Path(SPECPATH).resolve()
venv_site = base_dir / ".venv" / "Lib" / "site-packages"

pathex_paths = [str(base_dir)]
if venv_site.exists():
    for p in [venv_site, venv_site / "win32", venv_site / "win32" / "lib", venv_site / "pythonwin"]:
        if p.exists():
            pathex_paths.append(str(p))
            if str(p) not in sys.path:
                sys.path.insert(0, str(p))

hidden_imports = [
    "core.logger",
    "core.single_instance",
    "core.ipc",
    "notifier",
    "notifier.companion",
    "paths",
]

a = Analysis(
    ["notifier_main.py"],
    pathex=pathex_paths,
    binaries=[],
    datas=[],
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
        "servicemanager",
        "win32service",
        "win32serviceutil",
        "sqlite3",
        "psutil",
        "keyring",
        "requests",
        "websocket",
    ],
    noarchive=False,
    optimize=0,
)

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
    name="SLMS_Notifier",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
