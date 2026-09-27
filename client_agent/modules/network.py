"""
SLMS Client Agent Network Module.

Provides canonical network identity resolution and network traffic monitoring.

Design principles (Phase 4):
- D-03 / D-04 / D-05: Single canonical implementation for machine network identity.
  Consolidates IP and MAC address resolution from the same active adapter.
  Never pairs an IP from adapter A with a MAC from adapter B.
  Never fabricates 127.0.0.1 or 00:00:00:00:00:00.
- D-06: Network byte counters (bytes_sent, bytes_received) are CUMULATIVE counters
  from psutil.net_io_counters() since system boot/counter reset.
  They must retain cumulative semantics and must NOT be converted to rates.
"""

from __future__ import annotations

import ipaddress
import re
import socket
from typing import Any

import psutil

# Regex for validating and extracting standard 6-byte MAC addresses
_MAC_PATTERN = re.compile(r"^([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})$")

# Keywords indicating virtual, container, or tunnel adapters
_VIRTUAL_ADAPTER_KEYWORDS = (
    "vethernet",
    "hyper-v",
    "virtual",
    "vmware",
    "vmnet",
    "vbox",
    "virtualbox",
    "docker",
    "wsl",
    "tailscale",
    "tap",
    "tun",
    "wireguard",
    "vpn",
    "pseudo",
    "teredo",
    "isatap",
)

# Keywords indicating preferred physical LAN adapters
_PHYSICAL_LAN_KEYWORDS = (
    "ethernet",
    "local area connection",
    "eth",
    "lan",
)

_PHYSICAL_WIFI_KEYWORDS = (
    "wi-fi",
    "wifi",
    "wireless",
    "wlan",
    "802.11",
)


def normalize_mac_address(raw_mac: str | None) -> str | None:
    """
    Normalize a MAC address string to standard uppercase colon-separated format
    (e.g., 'CE:30:A6:2B:D9:DB').

    Returns None if the MAC is invalid, all-zeros, all-ones, or malformed.
    """
    if not raw_mac or not isinstance(raw_mac, str):
        return None

    cleaned = raw_mac.strip().replace("-", ":").upper()
    if not _MAC_PATTERN.match(cleaned):
        return None

    # Reject null MACs (all 00s) and broadcast MACs (all FFs)
    parts = cleaned.split(":")
    if all(p == "00" for p in parts) or all(p == "FF" for p in parts):
        return None

    return cleaned


def is_valid_routable_ipv4(ip_str: str | None) -> bool:
    """
    Check whether an IP string is a valid non-loopback, non-link-local, non-unspecified IPv4.
    """
    if not ip_str or not isinstance(ip_str, str):
        return False

    try:
        ip_obj = ipaddress.IPv4Address(ip_str.strip())
        if ip_obj.is_loopback:
            return False
        if ip_obj.is_link_local:  # 169.254.0.0/16 APIPA
            return False
        if ip_obj.is_unspecified:  # 0.0.0.0
            return False
        if ip_obj.is_reserved:
            return False
        return True
    except (ValueError, ipaddress.AddressValueError):
        return False


def evaluate_interface(
    iface_name: str,
    addresses: list[Any],
    stat: Any | None,
) -> tuple[int, str | None, str | None]:
    """
    Evaluate a network interface for suitability as the primary LAN identity.

    Returns:
        (score, valid_ipv4, normalized_mac)
        score <= 0 indicates unsuitable interface.
    """
    name_lower = iface_name.casefold()

    # Exclude loopback interfaces
    if "loopback" in name_lower or "pseudo" in name_lower:
        return 0, None, None

    # Extract IPv4 addresses and MAC address from this interface
    found_ipv4: str | None = None
    found_mac: str | None = None

    for addr in addresses:
        try:
            family = getattr(addr, "family", None)
            address_str = getattr(addr, "address", None)
            if not address_str:
                continue

            # Check for IPv4
            if family == socket.AF_INET:
                if is_valid_routable_ipv4(address_str):
                    if found_ipv4 is None:
                        found_ipv4 = address_str.strip()

            # Check for MAC address (AF_LINK on Windows is -1, AF_PACKET on Linux is 17)
            # Or any non-IP address matching standard MAC format
            is_mac_family = family in (getattr(psutil, "AF_LINK", -1), getattr(socket, "AF_PACKET", 17))
            if is_mac_family or family not in (socket.AF_INET, socket.AF_INET6):
                normalized = normalize_mac_address(address_str)
                if normalized and found_mac is None:
                    found_mac = normalized
        except Exception:
            continue

    # Interface without a valid routable IPv4 cannot be the primary LAN identity
    if not found_ipv4:
        return 0, None, None

    # Scoring criteria:
    score = 100

    # 1. Operational status (UP)
    if stat is not None:
        if not getattr(stat, "isup", True):
            # Interface is down
            return 0, None, None
        # Bonus for link speed
        speed = getattr(stat, "speed", 0) or 0
        if speed > 0:
            score += min(20, speed // 100)

    # 2. Prefer physical adapters over virtual
    is_virtual = any(kw in name_lower for kw in _VIRTUAL_ADAPTER_KEYWORDS)
    if is_virtual:
        score -= 60
    else:
        # Physical Ethernet preferred
        if any(kw in name_lower for kw in _PHYSICAL_LAN_KEYWORDS):
            score += 50
        # Physical Wi-Fi
        elif any(kw in name_lower for kw in _PHYSICAL_WIFI_KEYWORDS):
            score += 40

    # 3. Has corresponding valid hardware MAC address
    if found_mac:
        score += 30

    return score, found_ipv4, found_mac


def get_canonical_network_identity(
    addrs: dict[str, list[Any]] | None = None,
    stats: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Determine the canonical network identity for this computer.

    Selects the best active network adapter based on operational status,
    routable LAN IPv4, and physical vs. virtual priority.
    The returned IP address and MAC address are GUARANTEED to come from the
    exact same selected interface.

    Returns:
        dict with keys:
            status: 'success' | 'failed'
            interface: str | None
            ip_address: str | None
            mac_address: str | None
            error: str | None
    """
    try:
        if addrs is None:
            addrs = psutil.net_if_addrs()
        if stats is None:
            stats = psutil.net_if_stats()
    except Exception as e:
        return {
            "status": "failed",
            "interface": None,
            "ip_address": None,
            "mac_address": None,
            "error": f"Failed to query network interfaces: {e}",
        }

    best_score = 0
    best_interface: str | None = None
    best_ip: str | None = None
    best_mac: str | None = None

    for iface_name, iface_addrs in addrs.items():
        iface_stat = stats.get(iface_name) if stats else None
        score, ip, mac = evaluate_interface(iface_name, iface_addrs, iface_stat)

        if score > best_score:
            best_score = score
            best_interface = iface_name
            best_ip = ip
            best_mac = mac

    if best_interface is not None and best_ip is not None:
        return {
            "status": "success",
            "interface": best_interface,
            "ip_address": best_ip,
            "mac_address": best_mac,
            "error": None,
        }

    return {
        "status": "failed",
        "interface": None,
        "ip_address": None,
        "mac_address": None,
        "error": "No suitable active non-loopback network interface identified",
    }


def get_network_info() -> dict[str, Any]:
    """
    Collect network information including canonical identity and cumulative byte counters.

    Cumulative Counters Contract (D-06):
    'bytes_sent' and 'bytes_received' are cumulative byte counters from
    psutil.net_io_counters() since system/network interface counter reset.
    They must retain cumulative semantics and are NOT rate/per-second values.
    """
    identity = get_canonical_network_identity()

    hostname = socket.gethostname()

    try:
        io_stats = psutil.net_io_counters()
        bytes_sent = io_stats.bytes_sent
        bytes_received = io_stats.bytes_recv
    except Exception:
        bytes_sent = None
        bytes_received = None

    return {
        "hostname": hostname,
        "interface": identity.get("interface"),
        "ip_address": identity.get("ip_address"),
        "mac_address": identity.get("mac_address"),
        "network_status": identity.get("status"),
        "bytes_sent": bytes_sent,
        "bytes_received": bytes_received,
    }
