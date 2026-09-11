import os
import json
import socket
import platform
import uuid
import requests

from paths import CREDENTIAL_FILE
from config import API_BASE_URL, REGISTER_ENDPOINT, AGENT_CREDENTIAL_ENV
from core.logger import logger

def get_device_info():
    return {
        "hostname": socket.gethostname(),
        "ip_address": socket.gethostbyname(socket.gethostname()),
        "mac_address": ":".join(
            f"{(uuid.getnode() >> ele) & 0xff:02x}"
            for ele in range(40, -8, -8)
        ),
        "os_name": platform.system(),
        "os_version": platform.version()
    }

def get_credential():

    if os.path.exists(CREDENTIAL_FILE):
        try:
            with open(CREDENTIAL_FILE, "r", encoding="utf-8") as f:
                return json.load(f).get("credential")

        except Exception as e:
            logger.error(f"Failed to read credentials file: {e}")

    env_val = os.environ.get(AGENT_CREDENTIAL_ENV)