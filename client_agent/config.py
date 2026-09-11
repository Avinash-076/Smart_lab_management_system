# ==========================================
# Smart Lab Management System
# Configuration File
# ==========================================

import os

# Client Information
CLIENT_NAME = "SLMS Client"
VERSION = "1.0"

# Monitoring
MONITOR_INTERVAL = 20  # Seconds

from paths import LOG_FOLDER, OUTPUT_FOLDER
import os

LOG_FILE = os.path.join(LOG_FOLDER, "client.log")

# Display Options
SHOW_SOFTWARE_LIST = True
SHOW_PROCESS_LIST = True

# Export Options
EXPORT_JSON = True

# Monitoring Modules
ENABLE_SYSTEM_INFO = True
ENABLE_HARDWARE_INFO = True
ENABLE_SOFTWARE_INFO = True
ENABLE_PROCESS_INFO = False
ENABLE_NETWORK_INFO = True

# Console
CLEAR_SCREEN = False

# Application Mode
SHOW_CONSOLE = True

API_BASE_URL = ""
REGISTER_ENDPOINT = "/api/client/register"
DATA_ENDPOINT = "/api/"

AGENT_CREDENTIAL_ENV = "SLMS_AGENT_CREDENTIAL"
WS_BASE_URL = "ws://127.0.0.1:8000/ws/client"