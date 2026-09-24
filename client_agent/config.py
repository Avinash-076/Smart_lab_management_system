# ==========================================
# Smart Lab Management System
# Client Agent Configuration
# ==========================================

import os

from paths import (
    LOG_FOLDER,
    OUTPUT_FOLDER,
)


# ==========================================
# Application
# ==========================================

CLIENT_NAME = "SLMS Client Agent"

VERSION = "1.0.0"


# ==========================================
# Backend Server
# ==========================================

API_BASE_URL = os.getenv(
    "SLMS_API_URL",
    "http://127.0.0.1:8000",
).rstrip("/")


# ==========================================
# Monitoring
# ==========================================

# Normal system metrics collection interval.
MONITOR_INTERVAL = 20


# Installed software scan interval.
SOFTWARE_SCAN_INTERVAL = 10 * 60


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
# Issue Detection Thresholds
# ==========================================
#
# These values are currently used by
# modules/issues.py.
#
# They are kept here so they can later be
# changed without modifying the detection logic.
#

RAM_HIGH_THRESHOLD = 85

DISK_CRITICAL_THRESHOLD = 90


# ==========================================
# Display / Debug
# ==========================================

SHOW_CONSOLE = True

CLEAR_SCREEN = False

SHOW_SOFTWARE_LIST = False

SHOW_PROCESS_LIST = False


# ==========================================
# Local JSON Export
# ==========================================

EXPORT_JSON = True


# ==========================================
# Paths
# ==========================================

LOG_FILE = os.path.join(
    LOG_FOLDER,
    "client.log",
)

OUTPUT_FILE = os.path.join(
    OUTPUT_FOLDER,
    "client_data.json",
)


# ==========================================
# WebSocket
# ==========================================

WS_BASE_URL = os.getenv(
    "SLMS_WS_URL",
    "ws://127.0.0.1:8000/ws/client",
).rstrip("/")


# ==========================================
# Authentication
# ==========================================

SERVER_NAME = "SLMS"


# ==========================================
# Legacy Configuration
# ==========================================

REGISTER_ENDPOINT = "/api/agent/register"

DATA_ENDPOINT = "/api/metrics"

AGENT_CREDENTIAL_ENV = "SLMS_AGENT_CREDENTIAL"