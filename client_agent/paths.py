import os
import sys


def get_base_path():
    """
    Returns the folder where the program is running.
    Works for both Python and PyInstaller EXE.
    """
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


BASE_PATH = get_base_path()


def get_data_dir() -> str:
    """
    Determine the base data directory for logs, config, and cache.
    - Uses SLMS_DATA_DIR environment variable if specified (ideal for tests).
    - In development mode (SLMS_DEV_MODE=1), defaults to project BASE_PATH.
    - In production, uses standard Windows %PROGRAMDATA%\\SLMS.
    """
    env_dir = os.environ.get("SLMS_DATA_DIR")
    if env_dir:
        return env_dir

    dev_mode = os.environ.get("SLMS_DEV_MODE", "0").lower() in ("1", "true", "yes")
    if dev_mode and not getattr(sys, "frozen", False):
        return BASE_PATH

    program_data = os.environ.get("ProgramData", r"C:\ProgramData")
    return os.path.join(program_data, "SLMS")


DATA_DIR = get_data_dir()

LOG_FOLDER = os.path.join(DATA_DIR, "logs")
OUTPUT_FOLDER = os.path.join(DATA_DIR, "output")
CONFIG_FOLDER = os.path.join(DATA_DIR, "config")
CACHE_FOLDER = os.path.join(DATA_DIR, "cache")
OUTBOX_FOLDER = os.path.join(DATA_DIR, "outbox")
OUTBOX_DB_PATH = os.path.join(OUTBOX_FOLDER, "outbox.db")
SOFTWARE_STATE_FILE = os.path.join(DATA_DIR, "software_state.json")
USAGE_STATE_FILE = os.path.join(DATA_DIR, "usage_state.json")
ISSUE_STATE_FILE = os.path.join(DATA_DIR, "issue_state.json")

# Deprecated legacy path - preserved for backward compatibility
CREDENTIAL_FILE = os.path.join(BASE_PATH, "agent_credential.json")

# Ensure standard directories exist
for folder in (LOG_FOLDER, OUTPUT_FOLDER, CONFIG_FOLDER, CACHE_FOLDER, OUTBOX_FOLDER):
    try:
        os.makedirs(folder, exist_ok=True)
    except Exception:
        pass