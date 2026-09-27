"""
SLMS Client Agent System Information Module.

Collects basic operating-system and computer metadata.
Delegates network identity resolution to the canonical resolver in modules.network
to prevent duplicated logic (D-04) and ensure IP/MAC consistency (D-03, D-05).
"""

from __future__ import annotations

import platform
import socket
from typing import Any

from modules.network import get_canonical_network_identity


def get_lan_ip() -> str | None:
    """
    Return the primary LAN IPv4 address using canonical network identity.
    Does not contact the Internet; works in LAN-only environments.
    Returns None if no suitable active interface exists (no fake 127.0.0.1).
    """
    identity = get_canonical_network_identity()
    return identity.get("ip_address")


def get_mac_address() -> str | None:
    """
    Return the MAC address corresponding to the primary LAN interface.
    Guaranteed to match the adapter providing get_lan_ip().
    Returns None if no suitable active interface exists (no fake 00:00:00:00:00:00).
    """
    identity = get_canonical_network_identity()
    return identity.get("mac_address")


def get_system_info() -> dict[str, Any]:
    """
    Collect basic computer and operating-system information.
    Privacy constraint: Windows username is NOT collected.
    """
    identity = get_canonical_network_identity()

    return {
        "computer_name": socket.gethostname(),
        "operating_system": platform.system(),
        "os_version": platform.version(),
        "machine": platform.machine(),
        "processor": platform.processor(),
        "ip_address": identity.get("ip_address"),
        "mac_address": identity.get("mac_address"),
    }
