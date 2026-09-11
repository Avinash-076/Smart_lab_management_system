import os
import sys


def get_base_path():
    """
    Returns the folder where the program is running.
    Works for both Python and PyInstaller EXE.
    """

    if getattr(sys, "frozen", False):
        # Running as EXE
        return os.path.dirname(sys.executable)

    # Running as Python
    return os.path.dirname(os.path.abspath(__file__))


BASE_PATH = get_base_path()

LOG_FOLDER = os.path.join(BASE_PATH, "logs")
OUTPUT_FOLDER = os.path.join(BASE_PATH, "output")
CREDENTIAL_FILE = os.path.join(BASE_PATH, "agent_credential.json")