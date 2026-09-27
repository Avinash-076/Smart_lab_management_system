"""
DEPRECATED MODULE - DO NOT USE.
This module represents legacy registration code that is superseded by
server/enroll.py and server/auth.py. It is retained temporarily during
the hardening phase to verify that zero external dependencies exist and
will be decommissioned in a subsequent phase.
"""

import os
import json
import socket
import platform
import requests

from paths import CREDENTIAL_FILE
from config import API_BASE_URL, REGISTER_ENDPOINT, AGENT_CREDENTIAL_ENV
from core.logger import logger

from modules.network import get_canonical_network_identity

def get_device_info():
    ident = get_canonical_network_identity()
    return {
        "hostname": socket.gethostname(),
        "ip_address": ident.get("ip_address"),
        "mac_address": ident.get("mac_address"),
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