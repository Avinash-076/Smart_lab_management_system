# ==========================================
# Smart Lab Management System
# Client Agent Configuration
# ==========================================

from __future__ import annotations

import os

from paths import (
    CONFIG_FOLDER,
    LOG_FOLDER,
    OUTPUT_FOLDER,
)
from core.security import (
    derive_ws_url,
    is_insecure_http_allowed,
    validate_and_normalize_server_url,
)
from core.credentials import (
    DEFAULT_SERVICE_NAME,
    get_credential_store,
)


# ==========================================
# Application
# ==========================================

CLIENT_NAME = "SLMS Client Agent"

try:
    from importlib.metadata import version as _get_version
    __version__ = _get_version("client-agent")
except Exception:
    __version__ = "1.0.0"

VERSION = __version__


# ==========================================
# Backend Server
# ==========================================

DEFAULT_DEV_API_URL = "http://127.0.0.1:8000"
DEFAULT_PROD_API_URL = "https://127.0.0.1:8000"


def get_api_base_url() -> str:
    """
    Resolve the active API base URL.

    Resolution rules:
    1. If the agent is enrolled (has a persisted server URL in the credential store):
       - In production (allow_insecure is False):
         The persisted enrolled server URL is strictly authoritative.
         If SLMS_API_URL is set and conflicts with the persisted URL, a RuntimeError
         is raised to prevent silent redirection or hijacking.
       - In development/insecure mode (SLMS_ALLOW_INSECURE_HTTP=1 or SLMS_DEV_MODE=1):
         An explicit SLMS_API_URL override is permitted for local debugging.
       - Returns the normalized persisted server URL.
    2. If the agent is NOT enrolled:
       - SLMS_API_URL is used as the initial target for enrollment.
       - Defaults to DEFAULT_DEV_API_URL if allow_insecure else DEFAULT_PROD_API_URL.
    """
    allow_insecure = is_insecure_http_allowed()
    env_url = os.getenv("SLMS_API_URL", "").strip()

    persisted_url = ""
    try:
        persisted = get_credential_store().get_server_url()
        if persisted:
            persisted_url = persisted.strip()
    except Exception:
        persisted_url = ""

    if persisted_url:
        normalized_persisted = validate_and_normalize_server_url(
            persisted_url,
            allow_insecure=allow_insecure,
        )
        if env_url:
            normalized_env = validate_and_normalize_server_url(
                env_url,
                allow_insecure=allow_insecure,
            )
            if normalized_env != normalized_persisted:
                if not allow_insecure:
                    raise RuntimeError(
                        f"Cannot override enrolled server URL '{normalized_persisted}' "
                        f"with environment variable SLMS_API_URL='{normalized_env}' in production. "
                        f"Enrolled server URL is authoritative."
                    )
                return normalized_env
        return normalized_persisted

    configured_url = env_url or (DEFAULT_DEV_API_URL if allow_insecure else DEFAULT_PROD_API_URL)
    return validate_and_normalize_server_url(configured_url, allow_insecure=allow_insecure)


def get_ws_base_url() -> str:
    """
    Resolve the active WebSocket base URL.
    - If SLMS_WS_URL is explicitly set:
      * In production mode, rejects conflicting override if agent is enrolled.
      * In development mode, allows explicit override.
    - Otherwise derives wss:// or ws:// endpoint from the authoritative get_api_base_url().
    """
    allow_insecure = is_insecure_http_allowed()
    api_url = get_api_base_url()
    derived_ws = derive_ws_url(api_url, allow_insecure=allow_insecure)

    custom_ws = os.getenv("SLMS_WS_URL", "").strip()
    if custom_ws:
        normalized_custom = custom_ws.rstrip("/")
        if not allow_insecure:
            try:
                enrolled = get_credential_store().get_server_url()
            except Exception:
                enrolled = None
            if enrolled and normalized_custom != derived_ws:
                raise RuntimeError(
                    f"WebSocket endpoint '{derived_ws}' derived from authoritative server URL "
                    f"cannot be overridden by SLMS_WS_URL='{normalized_custom}' in production mode."
                )
        return normalized_custom

    return derived_ws


# For backward-compatible module access
try:
    API_BASE_URL = get_api_base_url()
except Exception:
    API_BASE_URL = DEFAULT_DEV_API_URL if is_insecure_http_allowed() else DEFAULT_PROD_API_URL

try:
    WS_BASE_URL = get_ws_base_url()
except Exception:
    WS_BASE_URL = "ws://127.0.0.1:8000/ws/client" if is_insecure_http_allowed() else "wss://127.0.0.1:8000/ws/client"


# ==========================================
# WebSocket Communication (Phase 7 G-03 / G-06)
# ==========================================

WS_PING_INTERVAL_SECONDS: float = float(os.getenv("SLMS_WS_PING_INTERVAL", "20.0"))
WS_RECONNECT_BASE_DELAY: float = float(os.getenv("SLMS_WS_RECONNECT_BASE_DELAY", "5.0"))
WS_RECONNECT_MAX_DELAY: float = float(os.getenv("SLMS_WS_RECONNECT_MAX_DELAY", "60.0"))
WS_RECONNECT_JITTER_RATIO: float = float(os.getenv("SLMS_WS_RECONNECT_JITTER", "0.15"))


# ==========================================
# Monitoring
# ==========================================

# Normal system metrics collection interval (seconds).
MONITOR_INTERVAL = 20

# Running processes inventory collection interval (seconds) - E-01 (target 1-5 minutes).
PROCESS_COLLECTION_INTERVAL: int = int(os.getenv("SLMS_PROCESS_INTERVAL", "120"))

# Installed software scan interval (seconds) - E-05 (target 10-30 minutes).
SOFTWARE_SCAN_INTERVAL: int = int(os.getenv("SLMS_SOFTWARE_INTERVAL", str(15 * 60)))

# Maximum processes retained in inventory payload - E-04 (bounded payload).
MAX_PROCESSES_INVENTORY: int = int(os.getenv("SLMS_MAX_PROCESSES", "500"))

# Maximum process name character length (matches backend schema).
MAX_PROCESS_NAME_LENGTH: int = 255


# ==========================================
# Feature Flags
# ==========================================

ENABLE_SYSTEM_INFO = True
ENABLE_HARDWARE_INFO = True
ENABLE_NETWORK_INFO = True
ENABLE_SOFTWARE_INFO = True
ENABLE_PROCESS_INFO = True
ENABLE_USAGE_INFO = True
ENABLE_ISSUE_REPORTING = True


# ==========================================
# Issue Detection & Debounce/Hysteresis (Phase 6 F-03 / F-04)
# ==========================================

# RAM thresholds (trigger > threshold, recovery <= threshold)
RAM_HIGH_THRESHOLD: float = float(os.getenv("SLMS_RAM_HIGH_THRESHOLD", "85.0"))
RAM_RECOVERY_THRESHOLD: float = float(os.getenv("SLMS_RAM_RECOVERY_THRESHOLD", "80.0"))

# Disk thresholds (trigger > threshold, recovery <= threshold)
DISK_CRITICAL_THRESHOLD: float = float(os.getenv("SLMS_DISK_CRITICAL_THRESHOLD", "90.0"))
DISK_RECOVERY_THRESHOLD: float = float(os.getenv("SLMS_DISK_RECOVERY_THRESHOLD", "85.0"))

# Debounce & Cooldown
ISSUE_DEBOUNCE_CYCLES: int = int(os.getenv("SLMS_ISSUE_DEBOUNCE_CYCLES", "2"))
ISSUE_COOLDOWN_SECONDS: int = int(os.getenv("SLMS_ISSUE_COOLDOWN_SECONDS", "0"))


# ==========================================
# Display / Debug
# ==========================================

SHOW_CONSOLE = True
CLEAR_SCREEN = False
SHOW_SOFTWARE_LIST = False
SHOW_PROCESS_LIST = False


# ==========================================
# Logging Configuration (Phase 9 I-01 / I-02)
# ==========================================

# Maximum active log size before rotation (default: 5 MB)
LOG_MAX_BYTES: int = int(os.getenv("SLMS_LOG_MAX_BYTES", str(5 * 1024 * 1024)))

# Retained rotated backup logs (default: 5 files)
LOG_BACKUP_COUNT: int = int(os.getenv("SLMS_LOG_BACKUP_COUNT", "5"))


# ==========================================
# Local JSON Export (Phase 9 I-04 / I-06)
# ==========================================

# Diagnostic export disabled by default in production; opt-in via SLMS_EXPORT_JSON=1
EXPORT_JSON: bool = os.getenv("SLMS_EXPORT_JSON", "0").lower() in ("1", "true", "yes")

# Diagnostic retention policy: 1 current snapshot only (Correction 1)
DIAGNOSTIC_MAX_FILES: int = int(os.getenv("SLMS_DIAGNOSTIC_MAX_FILES", "1"))


# ==========================================
# Paths
# ==========================================

LOG_FILE = os.path.join(LOG_FOLDER, "client.log")
OUTPUT_FILE = os.path.join(OUTPUT_FOLDER, "client_data.json")
DIAGNOSTIC_FILE = OUTPUT_FILE


# ==========================================
# Authentication & Security
# ==========================================

SERVER_NAME = DEFAULT_SERVICE_NAME
CA_BUNDLE_PATH = os.getenv("SLMS_CA_BUNDLE")


# ==========================================
# Legacy Configuration (DEPRECATED)
# ==========================================

REGISTER_ENDPOINT = "/api/agent/register"
DATA_ENDPOINT = "/api/metrics"
AGENT_CREDENTIAL_ENV = "SLMS_AGENT_CREDENTIAL"