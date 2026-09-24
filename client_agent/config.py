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
#
# Development:
#   http://127.0.0.1:8000
#
# LAN:
#   http://HOST-PC-IP:8000
#
# Example:
#   http://192.168.1.100:8000
#

API_BASE_URL = os.getenv(
    "SLMS_API_URL",
    "http://127.0.0.1:8000"
).rstrip("/")


# ------------------------------------------
# Monitoring
# ------------------------------------------

# Normal system metrics collection interval
MONITOR_INTERVAL = 20

# How often installed software should be
# collected and uploaded.
#
# Software inventory is heavier than normal
# CPU/RAM/disk monitoring, so we do not run
# it every 20 seconds.
SOFTWARE_SCAN_INTERVAL = 10 * 60


ENABLE_SYSTEM_INFO = True
ENABLE_HARDWARE_INFO = True
ENABLE_NETWORK_INFO = True

# Software inventory is now enabled.
ENABLE_SOFTWARE_INFO = True

# Process monitoring will be implemented next.
ENABLE_PROCESS_INFO = True


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