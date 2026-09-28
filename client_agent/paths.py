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

# Target Phase 9 Directory Structure:
# %ProgramData%\SLMS\
#     logs\
#     data\
#         outbox\
#         software_state.json
#         usage_state.json
#         issue_state.json
#         diagnostic\
#             client_data.json
#     cache\
#     config\
LOG_FOLDER = os.path.join(DATA_DIR, "logs")
DATA_FOLDER = os.path.join(DATA_DIR, "data")
CACHE_FOLDER = os.path.join(DATA_DIR, "cache")
CONFIG_FOLDER = os.path.join(DATA_DIR, "config")

OUTBOX_FOLDER = os.path.join(DATA_FOLDER, "outbox")
OUTBOX_DB_PATH = os.path.join(OUTBOX_FOLDER, "outbox.db")
SOFTWARE_STATE_FILE = os.path.join(DATA_FOLDER, "software_state.json")
USAGE_STATE_FILE = os.path.join(DATA_FOLDER, "usage_state.json")
ISSUE_STATE_FILE = os.path.join(DATA_FOLDER, "issue_state.json")
DIAGNOSTIC_FOLDER = os.path.join(DATA_FOLDER, "diagnostic")
DIAGNOSTIC_FILE = os.path.join(DIAGNOSTIC_FOLDER, "client_data.json")

# Backward compatibility aliases
OUTPUT_FOLDER = DIAGNOSTIC_FOLDER
OUTPUT_FILE = DIAGNOSTIC_FILE

# Deprecated legacy path - preserved for backward compatibility
CREDENTIAL_FILE = os.path.join(BASE_PATH, "agent_credential.json")


def get_path_layout(data_dir: str | None = None) -> dict[str, str]:
    """Return dictionary of path mappings for a given base data directory."""
    base = data_dir or get_data_dir()
    data = os.path.join(base, "data")
    logs = os.path.join(base, "logs")
    cache = os.path.join(base, "cache")
    config = os.path.join(base, "config")
    outbox = os.path.join(data, "outbox")
    diagnostic = os.path.join(data, "diagnostic")
    return {
        "data_dir": base,
        "logs": logs,
        "data": data,
        "cache": cache,
        "config": config,
        "outbox": outbox,
        "outbox_db": os.path.join(outbox, "outbox.db"),
        "diagnostic": diagnostic,
        "diagnostic_file": os.path.join(diagnostic, "client_data.json"),
        "software_state": os.path.join(data, "software_state.json"),
        "usage_state": os.path.join(data, "usage_state.json"),
        "issue_state": os.path.join(data, "issue_state.json"),
    }


def ensure_directories_exist(data_dir: str | None = None) -> None:
    """
    Explicitly ensure standard application directories exist before runtime use.
    Avoids unintended import-time side-effects.
    """
    layout = get_path_layout(data_dir)
    for key in ("logs", "data", "cache", "config", "outbox", "diagnostic"):
        try:
            os.makedirs(layout[key], exist_ok=True)
        except OSError:
            pass