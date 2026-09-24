# ==========================================
# Smart Lab Management System
# Client Agent Configuration
# ==========================================

import os

from paths import LOG_FOLDER, OUTPUT_FOLDER


# ------------------------------------------
# Application
# ------------------------------------------

CLIENT_NAME = "SLMS Client Agent"
VERSION = "1.0.0"


# ------------------------------------------
# Backend Server
# ------------------------------------------

API_BASE_URL = os.getenv(
    "SLMS_API_URL",
    "http://127.0.0.1:8000"
).rstrip("/")


# ------------------------------------------
# Monitoring
# ------------------------------------------

# Normal system metrics collection interval.
MONITOR_INTERVAL = 20


# Installed software scan interval.
SOFTWARE_SCAN_INTERVAL = 10 * 60


ENABLE_SYSTEM_INFO = True
ENABLE_HARDWARE_INFO = True
ENABLE_NETWORK_INFO = True

# Installed software monitoring.
ENABLE_SOFTWARE_INFO = True

# Running process monitoring.
ENABLE_PROCESS_INFO = True

# Application/process usage history.
ENABLE_USAGE_INFO = True


# ------------------------------------------
# Display / Debug
# ------------------------------------------

SHOW_CONSOLE = True

CLEAR_SCREEN = False

SHOW_SOFTWARE_LIST = False

SHOW_PROCESS_LIST = False


# ------------------------------------------
# Local JSON Export
# ------------------------------------------

EXPORT_JSON = True


# ------------------------------------------
# Paths
# ------------------------------------------

LOG_FILE = os.path.join(
    LOG_FOLDER,
    "client.log"
)

OUTPUT_FILE = os.path.join(
    OUTPUT_FOLDER,
    "client_data.json"
)


# ------------------------------------------
# WebSocket
# ------------------------------------------

WS_BASE_URL = os.getenv(
    "SLMS_WS_URL",
    "ws://127.0.0.1:8000/ws/client"
).rstrip("/")


# ------------------------------------------
# Authentication
# ------------------------------------------

SERVER_NAME = "SLMS"


# ------------------------------------------
# Legacy configuration
# ------------------------------------------

REGISTER_ENDPOINT = "/api/agent/register"

DATA_ENDPOINT = "/api/metrics"

AGENT_CREDENTIAL_ENV = "SLMS_AGENT_CREDENTIAL"