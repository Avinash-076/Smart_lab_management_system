import os
import shutil
from pathlib import Path


def add_to_startup(exe_path=None):
    """
    Copies the executable to the user's Startup folder.
    Returns True if successful, otherwise False.
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