"""
DEPRECATED MODULE - DO NOT USE IN PRODUCTION.
This module copied the agent executable into the per-user Windows Startup folder.
In Phase 2, this mechanism is superseded by the Windows Service architecture
(`service/service.py`) which runs automatically on system boot in Session 0
without requiring user login.
Retained temporarily for backward compatibility with legacy scripts.
"""

import os
import shutil
from pathlib import Path


def add_to_startup(exe_path=None):
    """
    DEPRECATED: Copies the executable to the user's Startup folder.
    Use Windows Service (`python -m service install`) for production deployments.
    """

    try:
        startup_folder = (
            Path(os.getenv("APPDATA"))
            / "Microsoft"
            / "Windows"
            / "Start Menu"
            / "Programs"
            / "Startup"
        )

        if exe_path is None:
            exe_path = os.path.abspath(__file__)

        destination = startup_folder / os.path.basename(exe_path)

        # Don't copy again if it already exists
        if not destination.exists():
            shutil.copy2(exe_path, destination)

        return True

    except Exception as e:
        print(f"Startup Error: {e}")
        return False